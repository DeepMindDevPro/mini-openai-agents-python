"""ToolContext — the context passed to `function_tool` callables.

A `ToolContext` is a `RunContextWrapper` subclass that adds tool-call-specific metadata
(`tool_name`, `tool_call_id`, `tool_arguments`, ...). Tool implementations may accept either
`RunContextWrapper` or `ToolContext` as their first positional parameter; `function_schema`
auto-detects which shape the user declared.

`ToolContext.run_config` / `ToolContext.agent` are populated by the runner so tools that need
to know the active agent or the resolved `RunConfig` (for instance, to locate the
`tool_error_formatter`) can read them without extra plumbing.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Generic

from .run_context import RunContextWrapper, TContext

if TYPE_CHECKING:
    from .agent import AgentBase
    from .run_config import RunConfig


def _must_pass(field_name: str) -> Any:
    def _raise() -> str:
        raise ValueError(f"ToolContext requires {field_name!r} to be provided explicitly")

    return _raise


@dataclass
class ToolContext(RunContextWrapper[TContext], Generic[TContext]):
    """Context available to a tool invocation.

    Positional field order is part of the public contract (see AGENTS.md).
    """

    tool_name: str = field(default_factory=_must_pass("tool_name"))
    tool_call_id: str = field(default_factory=_must_pass("tool_call_id"))
    tool_arguments: str = field(default_factory=_must_pass("tool_arguments"))
    tool_call: Any | None = None
    tool_namespace: str | None = None
    agent: AgentBase[Any] | None = None  # type: ignore[assignment]
    run_config: RunConfig | None = None  # type: ignore[assignment]

    @classmethod
    def from_run_context(
        cls,
        parent: RunContextWrapper[TContext],
        *,
        tool_name: str,
        tool_call_id: str,
        tool_arguments: str,
        tool_call: Any | None = None,
        tool_namespace: str | None = None,
        agent: Any | None = None,
        run_config: Any | None = None,
    ) -> ToolContext[TContext]:
        """Create a `ToolContext` that shares state (`usage`, approvals) with the parent."""
        ctx = cls(
            context=parent.context,
            usage=parent.usage,
            turn_input=parent.turn_input,
            tool_name=tool_name,
            tool_call_id=tool_call_id,
            tool_arguments=tool_arguments,
            tool_call=tool_call,
            tool_namespace=tool_namespace,
            agent=agent,
            run_config=run_config,
        )
        # share approvals map reference so nested tools can see parent approvals
        ctx._approvals = parent._approvals
        return ctx


__all__ = ["ToolContext"]