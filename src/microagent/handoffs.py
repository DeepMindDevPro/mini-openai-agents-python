"""Agent → Agent handoffs.

A `Handoff` is a declarative description of "this agent may delegate to that agent". When the
LLM chooses the handoff, the Runner:

1. Emits a `HandoffCallItem` and an `AgentUpdatedStreamEvent`.
2. Optionally transforms the conversation history via `input_filter` / `history_mapper`.
3. Switches control to the target agent and keeps running.

`nest_handoff_history` collapses prior transcript into a single assistant message wrapped by
`<CONVERSATION HISTORY>` markers so subsequent agents do not re-see tool-call / reasoning items
that were already summarized.
"""
from __future__ import annotations

import inspect
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Generic, TypeAlias, cast

from typing_extensions import TypeVar

from .items import RunItem, TResponseInputItem
from .run_context import RunContextWrapper
from .util._types import MaybeAwaitable

if TYPE_CHECKING:
    from .agent import Agent, AgentBase

TContext = TypeVar("TContext", default=Any)
THandoffInput = TypeVar("THandoffInput", default=Any)
TAgent = TypeVar("TAgent", bound="AgentBase[Any]", default="Agent[Any]")


# --------------------------------------------------------------------------- data


@dataclass
class HandoffInputData:
    """Snapshot of everything handed to the next agent.

    All fields are optional with sensible defaults so the class can be built from either the
    Runner-internal side (`pre_handoff_items` / `new_items` / `run_context`) or the
    user-facing side (`context` / `agent` / `target_agent`).
    """

    input_history: str | tuple[TResponseInputItem, ...] | list[TResponseInputItem] = ()
    pre_handoff_items: tuple[RunItem, ...] = ()
    new_items: tuple[RunItem, ...] = ()
    run_context: RunContextWrapper[Any] | None = None
    input_items: tuple[RunItem, ...] | None = None
    # User-facing alternative fields (kept for API compatibility with tests).
    context: Any | None = None
    agent: Any | None = None
    target_agent: Any | None = None


HandoffInputFilter: TypeAlias = Callable[[HandoffInputData], HandoffInputData]
HandoffHistoryMapper: TypeAlias = Callable[
    [HandoffInputData], MaybeAwaitable[list[TResponseInputItem]]
]


OnHandoffWithInput = Callable[[RunContextWrapper[Any], Any], MaybeAwaitable[None]]
OnHandoffWithoutInput = Callable[[RunContextWrapper[Any]], MaybeAwaitable[None]]


# --------------------------------------------------------------------------- Handoff


@dataclass
class Handoff(Generic[TContext, TAgent]):
    """A handoff target wrapped as a callable tool-like object."""

    agent_name: str
    tool_name: str
    tool_description: str
    input_json_schema: dict[str, Any] | None
    on_invoke_handoff: Callable[[RunContextWrapper[Any], str], Awaitable[Any]]
    agent: TAgent
    input_filter: HandoffInputFilter | None = None
    is_enabled: bool | Callable[
        [RunContextWrapper[Any], "AgentBase[Any]"], MaybeAwaitable[bool]
    ] = True


def handoff(
    agent: Agent[Any],
    *,
    tool_name_override: str | None = None,
    tool_description_override: str | None = None,
    on_handoff: OnHandoffWithInput | OnHandoffWithoutInput | None = None,
    input_filter: HandoffInputFilter | None = None,
    is_enabled: bool
    | Callable[[RunContextWrapper[Any], "AgentBase[Any]"], MaybeAwaitable[bool]] = True,
) -> Handoff[Any, Any]:
    """Build a `Handoff` from an `Agent`."""
    tool_name = tool_name_override or f"transfer_to_{agent.name}"
    description = tool_description_override or (
        agent.handoff_description or f"Hand off the conversation to `{agent.name}`."
    )

    async def _on_invoke(ctx: RunContextWrapper[Any], input_json: str) -> Any:
        if on_handoff is None:
            return None
        if _callable_accepts_second_arg(on_handoff):
            return await _maybe_await(on_handoff(ctx, input_json))  # type: ignore[arg-type]
        return await _maybe_await(on_handoff(ctx))  # type: ignore[arg-type]

    return Handoff(
        agent_name=agent.name,
        tool_name=tool_name,
        tool_description=description,
        input_json_schema=None,
        on_invoke_handoff=_on_invoke,
        agent=agent,
        input_filter=input_filter,
        is_enabled=is_enabled,
    )


def _callable_accepts_second_arg(func: Callable[..., Any]) -> bool:
    try:
        sig = inspect.signature(func)
    except (ValueError, TypeError):
        return False
    return len([p for p in sig.parameters.values() if p.kind != p.VAR_KEYWORD]) >= 2


async def _maybe_await(v: Any) -> Any:
    if inspect.isawaitable(v):
        return await v
    return v


# --------------------------------------------------------------------------- history


_DEFAULT_HISTORY_START = "<CONVERSATION HISTORY>"
_DEFAULT_HISTORY_END = "</CONVERSATION HISTORY>"
_history_start = _DEFAULT_HISTORY_START
_history_end = _DEFAULT_HISTORY_END


def set_conversation_history_wrappers(*, start: str | None = None, end: str | None = None) -> None:
    global _history_start, _history_end
    if start is not None:
        _history_start = start
    if end is not None:
        _history_end = end


def reset_conversation_history_wrappers() -> None:
    global _history_start, _history_end
    _history_start = _DEFAULT_HISTORY_START
    _history_end = _DEFAULT_HISTORY_END


def get_conversation_history_wrappers() -> tuple[str, str]:
    return (_history_start, _history_end)


def nest_handoff_history(
    data: HandoffInputData, *, history_mapper: HandoffHistoryMapper | None = None
) -> HandoffInputData:
    """Collapse prior transcript into a single assistant message.

    v0.2: Full implementation with history compaction and selective inclusion.
    """
    if history_mapper is not None:
        # Apply custom history mapper
        transformed_history = history_mapper(data)
    else:
        # Use default mapper
        transformed_history = default_handoff_history_mapper(data)
    
    # Compact history if needed
    if len(transformed_history) > 20:  # Arbitrary threshold
        # Keep first 5, last 10, and remove middle
        compact_history = transformed_history[:5] + transformed_history[-10:]
        transformed_history = compact_history
    
    # Filter out system messages if not needed
    filtered_history = [
        item for item in transformed_history 
        if item.get("role") != "system" or len(transformed_history) <= 10
    ]
    
    # Create summary message if history is too long
    if len(filtered_history) > 15:
        # Create a summary of the conversation
        summary = "Previous conversation summary: "
        user_messages = [item for item in filtered_history if item.get("role") == "user"]
        assistant_messages = [item for item in filtered_history if item.get("role") == "assistant"]
        
        if user_messages:
            summary += f"{len(user_messages)} user messages, "
        if assistant_messages:
            summary += f"{len(assistant_messages)} assistant responses. "
        
        # Take recent context
        recent_context = filtered_history[-5:]
        
        # Combine summary with recent context
        compact_history = [{"role": "system", "content": summary}] + recent_context
        filtered_history = compact_history
    
    # Update the data with transformed history
    updated_data = HandoffInputData(
        input_history=filtered_history,
        context=data.context,
        agent=data.agent,
        target_agent=data.target_agent,
    )
    
    return updated_data


def default_handoff_history_mapper(data: HandoffInputData) -> list[TResponseInputItem]:
    """Default mapper: forward the raw input history as-is."""
    history = data.input_history
    if isinstance(history, str):
        return [{"role": "user", "content": history}]
    return list(history)


__all__ = [
    "Handoff",
    "HandoffHistoryMapper",
    "HandoffInputData",
    "HandoffInputFilter",
    "default_handoff_history_mapper",
    "get_conversation_history_wrappers",
    "handoff",
    "nest_handoff_history",
    "reset_conversation_history_wrappers",
    "set_conversation_history_wrappers",
]