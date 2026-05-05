"""Agent dataclass — the declarative config that drives one LLM-plus-tools turn.

Positional field order is a public contract (see AGENTS.md §1.4). New optional fields **must**
be appended at the end.

`as_tool()` exposes an agent as a FunctionTool so other agents can call it; the MVP here forwards
a simple `{"input": str}` payload. `tool_use_behavior` covers the three common policies
(`run_llm_again` / `stop_on_first_tool` / `StopAtTools` dict / callable). `mcp_servers` is kept
as an opaque Protocol-typed list so concrete transports can ship in `microagent-mcp`.
"""
from __future__ import annotations

import dataclasses
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Generic, Literal, TypeAlias

from typing_extensions import NotRequired, TypedDict, TypeVar

from .agent_output import AgentOutputSchemaBase
from .guardrail import InputGuardrail, OutputGuardrail
from .handoffs import Handoff
from .logger import logger
from .model_settings import ModelSettings
from .prompts import DynamicPromptFunction, Prompt
from .run_context import RunContextWrapper, TContext
from .tool import FunctionTool, FunctionToolResult, Tool
from .util._types import MaybeAwaitable

if TYPE_CHECKING:
    from .items import ToolApprovalItem, TResponseInputItem
    from .lifecycle import AgentHooks
    from .memory import Session
    from .result import RunResult, RunResultStreaming
    from .run_config import RunConfig


# --------------------------------------------------------------------------- tool_use_behavior


class StopAtTools(TypedDict):
    stop_at_tool_names: list[str]


@dataclass
class ToolsToFinalOutputResult:
    is_final_output: bool
    final_output: Any | None = None


ToolsToFinalOutputFunction: TypeAlias = Callable[
    [RunContextWrapper[Any], list[FunctionToolResult]],
    MaybeAwaitable[ToolsToFinalOutputResult],
]


# --------------------------------------------------------------------------- AgentBase


@dataclass
class AgentBase(Generic[TContext]):
    """Common fields between `Agent` and realtime-style agents.

    Subclasses can grow; keep field order stable for pickle compatibility.
    """

    name: str
    handoff_description: str | None = None
    tools: list[Tool] = field(default_factory=list)


# --------------------------------------------------------------------------- Agent


Instructions = (
    str
    | Callable[[RunContextWrapper[TContext], "Agent[TContext]"], MaybeAwaitable[str]]
    | None
)


@dataclass
class AgentToolStreamEvent:
    """Lightweight event shape emitted by `Agent.as_tool(..., on_stream=...)`."""

    nested_agent: Agent[Any]
    tool_call: Any | None
    event: Any


@dataclass
class Agent(AgentBase[TContext], Generic[TContext]):
    """Declarative agent configuration.

    Field order matters. Do not reorder; append only.
    """

    instructions: Instructions[TContext] = None
    prompt: Prompt | DynamicPromptFunction | None = None
    handoffs: list[Agent[Any] | Handoff[TContext, Any]] = field(default_factory=list)
    model: str | Any | None = None  # str name or a Model instance (resolve via provider)
    model_settings: ModelSettings = field(default_factory=ModelSettings)
    input_guardrails: list[InputGuardrail[TContext]] = field(default_factory=list)
    output_guardrails: list[OutputGuardrail[TContext]] = field(default_factory=list)
    output_type: type[Any] | AgentOutputSchemaBase | None = None
    hooks: AgentHooks[TContext] | None = None
    tool_use_behavior: (
        Literal["run_llm_again", "stop_on_first_tool"]
        | StopAtTools
        | ToolsToFinalOutputFunction
    ) = "run_llm_again"
    reset_tool_choice: bool = True

    # MCP support is kept here as a Protocol-typed list so core does not depend on any MCP
    # transport implementation. The `microagent-mcp` addon provides concrete servers.
    mcp_servers: list[Any] = field(default_factory=list)
    mcp_config: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.name, str):
            raise TypeError(f"Agent.name must be a str, got {type(self.name).__name__}")
        if not isinstance(self.tools, list):
            raise TypeError(
                f"Agent.tools must be a list, got {type(self.tools).__name__}"
            )
        if not isinstance(self.handoffs, list):
            raise TypeError(
                f"Agent.handoffs must be a list, got {type(self.handoffs).__name__}"
            )
        if not isinstance(self.model_settings, ModelSettings):
            raise TypeError(
                "Agent.model_settings must be a ModelSettings instance"
            )
        valid_behaviors = {"run_llm_again", "stop_on_first_tool"}
        if not (
            (isinstance(self.tool_use_behavior, str) and self.tool_use_behavior in valid_behaviors)
            or isinstance(self.tool_use_behavior, dict)
            or callable(self.tool_use_behavior)
        ):
            raise TypeError(
                "Agent.tool_use_behavior must be 'run_llm_again', 'stop_on_first_tool', "
                "a StopAtTools dict, or a callable."
            )

    def clone(self, **kwargs: Any) -> Agent[TContext]:
        """Make a shallow copy with overrides."""
        return dataclasses.replace(self, **kwargs)

    # ---- helpers used by the Runner ----

    async def get_system_prompt(
        self, context: RunContextWrapper[TContext]
    ) -> str | None:
        """Resolve the system instructions (handles str / callable forms)."""
        if self.instructions is None:
            return None
        if isinstance(self.instructions, str):
            return self.instructions
        if callable(self.instructions):
            value = self.instructions(context, self)
            from .util._coro import resolve

            return await resolve(value)  # type: ignore[return-value]
        raise TypeError(f"Unsupported instructions type: {type(self.instructions).__name__}")

    async def get_all_tools(
        self, context: RunContextWrapper[TContext]
    ) -> list[Tool]:
        """Return tools enabled for this turn.

        Honours `Tool.is_enabled` which may be either a plain bool or a sync/async callable
        of `(context, agent)`. Addons that surface MCP-discovered tools can subclass
        `Agent` and override this hook.
        """
        resolved: list[Tool] = []
        for tool in self.tools:
            enabled = getattr(tool, "is_enabled", True)
            if isinstance(enabled, bool):
                if enabled:
                    resolved.append(tool)
                continue
            if callable(enabled):
                import inspect

                from .util._coro import resolve

                val = enabled(context, self)
                if inspect.isawaitable(val):
                    val = await val
                if val:
                    resolved.append(tool)
                continue
            resolved.append(tool)
        return resolved

    # ---- as_tool (MVP skeleton) ----

    def as_tool(
        self,
        tool_name: str | None = None,
        tool_description: str | None = None,
        *,
        is_enabled: bool
        | Callable[
            [RunContextWrapper[Any], "AgentBase[Any]"], MaybeAwaitable[bool]
        ] = True,
        needs_approval: bool = False,
    ) -> FunctionTool:
        """Expose this agent as a FunctionTool for another agent to call.

        MVP: forwards a simple `{"input": str}` payload and runs this agent with it. Structured
        input payloads and streaming fan-out are handled by the addon-layered
        `StructuredToolInputBuilder`.
        """
        from .util._transforms import transform_string_function_style

        resolved_name = tool_name or transform_string_function_style(self.name)
        resolved_description = tool_description or (
            self.handoff_description or f"Delegate to agent `{self.name}`."
        )
        schema = {
            "type": "object",
            "properties": {"input": {"type": "string"}},
            "required": ["input"],
            "additionalProperties": False,
        }

        async def _invoke(ctx: Any, input_json: str) -> Any:
            import json as _json

            from .run import Runner

            try:
                parsed = _json.loads(input_json or "{}")
            except _json.JSONDecodeError:
                parsed = {}
            nested_input = parsed.get("input") if isinstance(parsed, dict) else ""
            if not isinstance(nested_input, str):
                nested_input = str(nested_input)
            nested = await Runner.run(self, nested_input, context=ctx.context)
            return nested.final_output

        from .tool.origin import ToolOrigin, ToolOriginType

        return FunctionTool(
            name=resolved_name,
            description=resolved_description,
            params_json_schema=schema,
            on_invoke_tool=_invoke,
            is_enabled=is_enabled,
            needs_approval=needs_approval,
            _is_agent_tool=True,
            _agent_instance=self,
            _tool_origin=ToolOrigin(
                type=ToolOriginType.AGENT_AS_TOOL,
                agent_name=self.name,
                agent_tool_name=resolved_name,
            ),
        )


__all__ = [
    "Agent",
    "AgentBase",
    "AgentToolStreamEvent",
    "Instructions",
    "StopAtTools",
    "ToolsToFinalOutputFunction",
    "ToolsToFinalOutputResult",
]