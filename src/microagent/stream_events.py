"""Stream event types emitted by `Runner.run_streamed`.

**Stability contract**: the string Literals below are part of the public API. Renaming them
is a breaking change (see AGENTS.md §1.6). Unlike the upstream SDK which froze a typo
(`"handoff_occured"`), this fresh implementation starts from the correct spelling
(`"handoff_occurred"`) — there is no legacy baggage to preserve.

Three top-level event kinds:

- `RawResponsesStreamEvent` — pass-through of provider-side token deltas.
- `RunItemStreamEvent`      — semantic "a RunItem just appeared".
- `AgentUpdatedStreamEvent` — "a handoff transferred control to a new agent".
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, TypeAlias

from .agent import Agent
from .items import RunItem, TResponseStreamEvent

# The canonical set of event names. `str` is included so runtime-registered addon events
# (MCP, tool-search, etc.) don't need to edit this module. The Literal is retained for
# static-analysis stability.
RunItemStreamEventName: TypeAlias = Literal[
    "message_output_created",
    "message_output_item",
    "handoff_requested",
    "handoff_occurred",
    "handoff_call_item",
    "handoff_output_item",
    "tool_called",
    "tool_call_item",
    "tool_output",
    "tool_call_output_item",
    "tool_approval_item",
    "reasoning_item_created",
    "reasoning_item",
    "mcp_approval_requested",
    "mcp_approval_request_item",
    "mcp_approval_response",
    "mcp_approval_response_item",
    "mcp_list_tools",
    "mcp_list_tools_item",
    "tool_search_called",
    "tool_search_call_item",
    "tool_search_output_created",
    "tool_search_output_item",
    "compaction_item",
]


@dataclass
class RawResponsesStreamEvent:
    """Raw streaming event forwarded from the model."""

    data: TResponseStreamEvent
    type: Literal["raw_response_event"] = "raw_response_event"


@dataclass
class RunItemStreamEvent:
    """Emitted whenever a new `RunItem` is materialized."""

    name: RunItemStreamEventName
    item: Any = None
    run_id: str | None = None
    agent_name: str | None = None
    type: Literal["run_item_stream_event"] = "run_item_stream_event"


@dataclass
class AgentUpdatedStreamEvent:
    """Emitted when control is handed to a new agent."""

    new_agent: Agent[Any] | None = None
    new_agent_name: str | None = None
    name: str = "handoff_occurred"
    run_id: str | None = None
    agent_name: str | None = None
    type: Literal["agent_updated_stream_event"] = "agent_updated_stream_event"


StreamEvent: TypeAlias = (
    RawResponsesStreamEvent | RunItemStreamEvent | AgentUpdatedStreamEvent
)


__all__ = [
    "AgentUpdatedStreamEvent",
    "RawResponsesStreamEvent",
    "RunItemStreamEvent",
    "RunItemStreamEventName",
    "StreamEvent",
]