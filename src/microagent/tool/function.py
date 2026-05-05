"""FunctionTool + `function_tool` decorator.

A `FunctionTool` wraps a Python callable with:
- Auto-generated JSON schema (via `function_schema`).
- Per-tool guardrails (input / output).
- Approval policy (`needs_approval: bool | Callable`).
- Timeout (`timeout_seconds / timeout_behavior`).
- Deferred loading for "tool search" providers.
- `is_enabled` dynamic gating.

Positional field order is part of the public contract: add new optional fields at the end.
"""
from __future__ import annotations

import dataclasses
import inspect
import json
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Literal, Protocol, TypeAlias, Union

from pydantic import ValidationError

from ..exceptions import ModelBehaviorError, ToolTimeoutError, UserError
from ..function_schema import FuncSchema, function_schema
from ..logger import logger
from ..run_context import RunContextWrapper
from ..strict_schema import ensure_strict_json_schema
from ..tool_context import ToolContext
from ..util._types import MaybeAwaitable
from .origin import ToolOrigin, ToolOriginType

if TYPE_CHECKING:
    from ..agent import AgentBase
    from ..items import RunItem, ToolApprovalItem
    from ..tool_guardrails import ToolInputGuardrail, ToolOutputGuardrail

DEFAULT_APPROVAL_REJECTION_MESSAGE = "Tool call was rejected by the approval policy."

ToolTimeoutBehavior: TypeAlias = Literal["error_as_result", "raise_exception"]
ToolErrorFunction: TypeAlias = Callable[
    [RunContextWrapper[Any], Exception], MaybeAwaitable[str]
]


def default_tool_error_function(context: RunContextWrapper[Any], error: Exception) -> str:
    """Formatter that returns a plain "tool raised X" message to the model."""
    return f"The tool errored: {error}"


class Tool(Protocol):
    """Structural Protocol every concrete Tool satisfies (name + description)."""

    name: str
    description: str


@dataclass
class FunctionToolResult:
    """Result envelope produced after executing a FunctionTool invocation."""

    tool: FunctionTool
    output: Any
    run_item: RunItem | None = None
    interruptions: list[ToolApprovalItem] = field(default_factory=list)
    agent_run_result: Any = None  # avoid circular import


@dataclass
class FunctionTool:
    """A tool that wraps a Python callable and exposes it to the LLM as a function."""

    name: str
    description: str
    params_json_schema: dict[str, Any]
    on_invoke_tool: Callable[[ToolContext[Any], str], Awaitable[Any]]

    strict_json_schema: bool = True
    is_enabled: bool | Callable[[RunContextWrapper[Any], AgentBase], MaybeAwaitable[bool]] = True
    tool_input_guardrails: list[ToolInputGuardrail[Any]] | None = None
    tool_output_guardrails: list[ToolOutputGuardrail[Any]] | None = None
    needs_approval: (
        bool | Callable[[RunContextWrapper[Any], dict[str, Any], str], Awaitable[bool]]
    ) = False
    timeout_seconds: float | None = None
    timeout_behavior: ToolTimeoutBehavior = "error_as_result"
    timeout_error_function: ToolErrorFunction | None = None
    defer_loading: bool = False

    # internal / kw-only metadata
    _failure_error_function: ToolErrorFunction | None = field(
        default=None, kw_only=True, repr=False
    )
    _is_agent_tool: bool = field(default=False, kw_only=True, repr=False)
    _agent_instance: Any = field(default=None, kw_only=True, repr=False)
    _tool_namespace: str | None = field(default=None, kw_only=True, repr=False)
    _tool_namespace_description: str | None = field(default=None, kw_only=True, repr=False)
    _mcp_title: str | None = field(default=None, kw_only=True, repr=False)
    _tool_origin: ToolOrigin | None = field(default=None, kw_only=True, repr=False)
    _emit_tool_origin: bool = field(default=True, kw_only=True, repr=False)

    def __post_init__(self) -> None:
        if self.strict_json_schema:
            self.params_json_schema = ensure_strict_json_schema(self.params_json_schema)

    @property
    def qualified_name(self) -> str:
        if self._tool_namespace:
            return f"{self._tool_namespace}.{self.name}"
        return self.name


# --------------------------------------------------------------------------- decorator


def _parse_json_input(tool_name: str, input_json: str) -> dict[str, Any]:
    if not input_json or input_json.strip() == "":
        return {}
    try:
        data = json.loads(input_json)
    except json.JSONDecodeError as exc:
        raise ModelBehaviorError(
            f"Tool {tool_name!r} received invalid JSON: {exc}"
        ) from exc
    if not isinstance(data, dict):
        raise ModelBehaviorError(
            f"Tool {tool_name!r} expected a JSON object, got {type(data).__name__}"
        )
    return data


def _build_invoker(
    func: Callable[..., Any],
    schema: FuncSchema,
    failure_error_function: ToolErrorFunction | None,
) -> Callable[[ToolContext[Any], str], Awaitable[Any]]:
    async def _invoke(ctx: ToolContext[Any], input_json: str) -> Any:
        try:
            raw = _parse_json_input(schema.name, input_json)
            try:
                validated = schema.params_pydantic_model.model_validate(raw)
            except ValidationError as exc:
                raise ModelBehaviorError(
                    f"Tool {schema.name!r} received invalid arguments: {exc}"
                ) from exc
            args, kwargs = schema.to_call_args(validated)
            if schema.takes_context:
                result = func(ctx, *args, **kwargs)
            else:
                result = func(*args, **kwargs)
            if inspect.isawaitable(result):
                result = await result
            return result
        except Exception as exc:
            handler = failure_error_function
            if handler is None:
                raise
            msg = handler(ctx, exc)
            if inspect.isawaitable(msg):
                msg = await msg
            logger.debug("Tool %s raised %r; converted to model-visible error", schema.name, exc)
            return msg

    return _invoke


def function_tool(
    func: Callable[..., Any] | None = None,
    *,
    name_override: str | None = None,
    description_override: str | None = None,
    strict_json_schema: bool = True,
    is_enabled: bool
    | Callable[[RunContextWrapper[Any], AgentBase], MaybeAwaitable[bool]] = True,
    failure_error_function: ToolErrorFunction | None = default_tool_error_function,
    tool_input_guardrails: list[ToolInputGuardrail[Any]] | None = None,
    tool_output_guardrails: list[ToolOutputGuardrail[Any]] | None = None,
    needs_approval: bool
    | Callable[[RunContextWrapper[Any], dict[str, Any], str], Awaitable[bool]] = False,
    timeout_seconds: float | None = None,
    timeout_behavior: ToolTimeoutBehavior = "error_as_result",
    timeout_error_function: ToolErrorFunction | None = None,
) -> Any:
    """Decorator turning a Python callable into a FunctionTool.

    Usage:
        @function_tool
        def my_tool(x: int) -> str: ...

        @function_tool(name_override="my_tool_v2")
        async def another(ctx: RunContextWrapper, y: str) -> dict: ...
    """

    def _decorate(f: Callable[..., Any]) -> FunctionTool:
        if not callable(f):
            raise UserError(f"@function_tool expected a callable, got {type(f).__name__}")
        schema = function_schema(
            f,
            name_override=name_override,
            description_override=description_override,
            strict_json_schema=strict_json_schema,
        )
        invoker = _build_invoker(f, schema, failure_error_function)
        return FunctionTool(
            name=schema.name,
            description=schema.description or "",
            params_json_schema=schema.params_json_schema,
            on_invoke_tool=invoker,
            strict_json_schema=strict_json_schema,
            is_enabled=is_enabled,
            tool_input_guardrails=tool_input_guardrails,
            tool_output_guardrails=tool_output_guardrails,
            needs_approval=needs_approval,
            timeout_seconds=timeout_seconds,
            timeout_behavior=timeout_behavior,
            timeout_error_function=timeout_error_function,
            _failure_error_function=failure_error_function,
            _tool_origin=ToolOrigin(type=ToolOriginType.FUNCTION),
        )

    if func is not None and callable(func):
        # @function_tool (no parens)
        return _decorate(func)
    return _decorate


__all__ = [
    "DEFAULT_APPROVAL_REJECTION_MESSAGE",
    "FunctionTool",
    "FunctionToolResult",
    "Tool",
    "ToolErrorFunction",
    "ToolTimeoutBehavior",
    "default_tool_error_function",
    "function_tool",
]