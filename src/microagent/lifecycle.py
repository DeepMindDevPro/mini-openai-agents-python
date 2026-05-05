"""Lifecycle hooks: `RunHooks` (run-wide) and `AgentHooks` (per-agent).

Full callback list:

- `on_llm_start(ctx, agent, system_prompt, input_items)`
- `on_llm_end(ctx, agent, response)`
- `on_agent_start(hook_ctx, agent)`
- `on_agent_end(hook_ctx, agent, output)`
- `on_handoff(ctx, from_agent, to_agent)`
- `on_tool_start(ctx, agent, tool)`
- `on_tool_end(ctx, agent, tool, result)`
- `on_tool_approval_requested(ctx, agent, approval_item)`

All callbacks are async; subclasses override only the ones they care about.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any, Generic

from typing_extensions import TypeVar

from .run_context import AgentHookContext, RunContextWrapper, TContext

if TYPE_CHECKING:
    from .agent import Agent, AgentBase
    from .items import ModelResponse, ToolApprovalItem, TResponseInputItem
    from .tool import FunctionToolResult, Tool

TAgent = TypeVar("TAgent", bound="AgentBase[Any]", default="AgentBase[Any]")


class RunHooksBase(Generic[TContext, TAgent]):
    """Base class for run-scoped hooks. Override what you need."""

    async def on_llm_start(
        self,
        context: RunContextWrapper[TContext],
        agent: Agent[TContext],
        system_prompt: str | None,
        input_items: list[TResponseInputItem],
    ) -> None:
        """Called just before the LLM is invoked."""

    async def on_llm_end(
        self,
        context: RunContextWrapper[TContext],
        agent: Agent[TContext],
        response: ModelResponse,
    ) -> None:
        """Called after the LLM responds."""

    async def on_agent_start(
        self, context: AgentHookContext[TContext], agent: TAgent
    ) -> None:
        """Called when a (new) agent takes control of the run."""

    async def on_agent_end(
        self,
        context: AgentHookContext[TContext],
        agent: TAgent,
        output: Any,
    ) -> None:
        """Called when the agent produces its final output."""

    async def on_handoff(
        self,
        context: RunContextWrapper[TContext],
        from_agent: TAgent,
        to_agent: TAgent,
    ) -> None:
        """Called when control transfers from one agent to another."""

    async def on_tool_start(
        self,
        context: RunContextWrapper[TContext],
        agent: TAgent,
        tool: Tool,
    ) -> None:
        """Called just before a tool is invoked."""

    async def on_tool_end(
        self,
        context: RunContextWrapper[TContext],
        agent: TAgent,
        tool: Tool,
        result: FunctionToolResult,
    ) -> None:
        """Called after a tool invocation returns (regardless of success)."""

    async def on_tool_approval_requested(
        self,
        context: RunContextWrapper[TContext],
        agent: TAgent,
        approval_item: ToolApprovalItem,
    ) -> None:
        """Called when a tool call requires human approval."""


class RunHooks(RunHooksBase[TContext, "Agent[Any]"]):
    """Concrete run-scoped hooks (generic on user context type)."""


class AgentHooksBase(Generic[TContext, TAgent]):
    """Per-agent subset of hooks. Narrower callbacks than `RunHooks`."""

    async def on_start(self, context: AgentHookContext[TContext], agent: TAgent) -> None:
        """Called when the Runner switches to this agent."""

    async def on_end(
        self,
        context: AgentHookContext[TContext],
        agent: TAgent,
        output: Any,
    ) -> None:
        """Called when this agent produces a final output."""

    async def on_tool_start(
        self,
        context: RunContextWrapper[TContext],
        agent: TAgent,
        tool: Tool,
    ) -> None: ...

    async def on_tool_end(
        self,
        context: RunContextWrapper[TContext],
        agent: TAgent,
        tool: Tool,
        result: FunctionToolResult,
    ) -> None: ...


class AgentHooks(AgentHooksBase[TContext, "Agent[Any]"]):
    pass


__all__ = [
    "AgentHooks",
    "AgentHooksBase",
    "RunHooks",
    "RunHooksBase",
]