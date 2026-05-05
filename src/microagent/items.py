"""RunItem family — the common vocabulary between the Runner and the user.

Full family (13 concrete types in industrial SDKs; we carry the 8 most-used in core MVP and
keep Protocol hooks for the rest so addons can register them at load-time):

    core (v0.1):
      - MessageOutputItem
      - ToolCallItem
      - ToolCallOutputItem
      - ToolApprovalItem
      - HandoffCallItem
      - HandoffOutputItem
      - ReasoningItem
      - ModelResponse (not strictly an item, but tracked alongside)

    addon-registered (v0.2+):
      - MCPApprovalRequestItem / MCPApprovalResponseItem / MCPListToolsItem
      - ToolSearchCallItem / ToolSearchOutputItem
      - CompactionItem

The base `RunItemBase` uses `weakref` for its `agent` field so that long traces + large agent
objects do not leak memory (see AGENTS.md §1.5 and the matching release_agent() test).

Type aliases at the top mirror the upstream SDK's `TResponse*` names so addons that speak the
OpenAI Responses item shapes can interop cleanly. `ItemHelpers` collects the small conversion
helpers used by both the runner and user code.
"""
from __future__ import annotations

import abc
import weakref
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Generic, Literal, TypeAlias, TypeVar

if TYPE_CHECKING:
    from .agent import Agent
    from ._tool_identity import NamedToolLookupKey
    from .tool.origin import ToolOrigin
    from .usage import Usage

# Provider-agnostic shape: keep these as `Any` so core has no hard OpenAI-type dependency.
TResponseInputItem: TypeAlias = dict[str, Any]
TResponseOutputItem: TypeAlias = dict[str, Any]
TResponseStreamEvent: TypeAlias = dict[str, Any]

T = TypeVar("T")

_MISSING = object()


@dataclass
class ModelResponse:
    """A single model response (one LLM turn)."""

    output: list[TResponseOutputItem]
    usage: Usage | None = None
    response_id: str | None = None
    request_id: str | None = None

    def to_input_items(self) -> list[TResponseInputItem]:
        return list(self.output)


@dataclass
class RunItemBase(Generic[T], abc.ABC):
    """Base class for all RunItems. `agent` is held as a weak reference to prevent leaks."""

    agent: Agent[Any]
    raw_item: T
    _agent_ref: weakref.ReferenceType[Agent[Any]] | None = field(
        init=False, repr=False, default=None
    )

    def __post_init__(self) -> None:
        try:
            self._agent_ref = weakref.ref(self.agent)
        except TypeError:
            self._agent_ref = None

    def release_agent(self) -> None:
        """Drop the strong reference, keep the weak reference alive."""
        if "agent" not in self.__dict__:
            return
        agent = self.__dict__["agent"]
        if agent is None:
            return
        try:
            self._agent_ref = weakref.ref(agent)
        except TypeError:
            self._agent_ref = None
        self.__dict__["agent"] = None

    def _resolve_agent(self) -> Agent[Any] | None:
        agent = self.__dict__.get("agent", _MISSING)
        if agent is not _MISSING and agent is not None:
            return agent  # type: ignore[return-value]
        ref = self._agent_ref
        if ref is None:
            return None
        return ref()

    def to_input_item(self) -> TResponseInputItem:
        """Convert this RunItem back into a model-facing input item."""
        if isinstance(self.raw_item, dict):
            return self.raw_item  # type: ignore[return-value]
        if hasattr(self.raw_item, "model_dump"):
            return self.raw_item.model_dump(exclude_none=True)  # type: ignore[no-any-return]
        return {"raw": str(self.raw_item)}


@dataclass
class MessageOutputItem(RunItemBase[dict[str, Any]]):
    """An assistant message emitted by the LLM."""

    type: Literal["message_output_item"] = "message_output_item"


@dataclass
class ToolCallItem(RunItemBase[dict[str, Any]]):
    """The LLM decided to invoke a tool."""

    type: Literal["tool_call_item"] = "tool_call_item"
    tool_origin: ToolOrigin | None = None


@dataclass
class ToolCallOutputItem(RunItemBase[dict[str, Any]]):
    """The tool execution result, fed back into the LLM on the next turn."""

    output: Any = None
    type: Literal["tool_call_output_item"] = "tool_call_output_item"


@dataclass
class ToolApprovalItem(RunItemBase[dict[str, Any]]):
    """A pending tool call that needs human approval before execution."""

    call_id: str = ""
    tool_name: str = ""
    tool_namespace: str | None = None
    tool_lookup_key: NamedToolLookupKey | None = None
    type: Literal["tool_approval_item"] = "tool_approval_item"


@dataclass
class HandoffCallItem(RunItemBase[dict[str, Any]]):
    """The LLM requested a handoff to another agent."""

    type: Literal["handoff_call_item"] = "handoff_call_item"


@dataclass
class HandoffOutputItem(RunItemBase[dict[str, Any]]):
    """Synthetic output item emitted after a handoff is fulfilled."""

    source_agent: Agent[Any] | None = None
    target_agent: Agent[Any] | None = None
    type: Literal["handoff_output_item"] = "handoff_output_item"


@dataclass
class ReasoningItem(RunItemBase[dict[str, Any]]):
    """Thinking / reasoning content emitted by reasoning-capable models (o-series, R1, ...)."""

    type: Literal["reasoning_item"] = "reasoning_item"


# Addon-registered stub items (minimal placeholders; concrete behavior lives in addons):


@dataclass
class MCPApprovalRequestItem(RunItemBase[dict[str, Any]]):
    type: Literal["mcp_approval_request_item"] = "mcp_approval_request_item"


@dataclass
class MCPApprovalResponseItem(RunItemBase[dict[str, Any]]):
    type: Literal["mcp_approval_response_item"] = "mcp_approval_response_item"


@dataclass
class MCPListToolsItem(RunItemBase[dict[str, Any]]):
    type: Literal["mcp_list_tools_item"] = "mcp_list_tools_item"


@dataclass
class ToolSearchCallItem(RunItemBase[dict[str, Any]]):
    type: Literal["tool_search_call_item"] = "tool_search_call_item"


@dataclass
class ToolSearchOutputItem(RunItemBase[dict[str, Any]]):
    type: Literal["tool_search_output_item"] = "tool_search_output_item"


@dataclass
class CompactionItem(RunItemBase[dict[str, Any]]):
    """Synthetic item representing a memory compaction step."""

    type: Literal["compaction_item"] = "compaction_item"


RunItem = (
    MessageOutputItem
    | ToolCallItem
    | ToolCallOutputItem
    | ToolApprovalItem
    | HandoffCallItem
    | HandoffOutputItem
    | ReasoningItem
    | MCPApprovalRequestItem
    | MCPApprovalResponseItem
    | MCPListToolsItem
    | ToolSearchCallItem
    | ToolSearchOutputItem
    | CompactionItem
)


class ItemHelpers:
    """Helpers for converting between inputs and RunItems."""

    @staticmethod
    def input_to_new_input_list(
        input: str | list[TResponseInputItem],
    ) -> list[TResponseInputItem]:
        if isinstance(input, str):
            return [{"role": "user", "content": input}]
        return list(input)

    @staticmethod
    def text_message_outputs(items: list[RunItem]) -> str:
        """Concatenate text content from all MessageOutputItems."""
        parts: list[str] = []
        for item in items:
            if isinstance(item, MessageOutputItem):
                raw = item.raw_item
                if isinstance(raw, dict):
                    content = raw.get("content")
                    if isinstance(content, str):
                        parts.append(content)
                    elif isinstance(content, list):
                        for c in content:
                            if isinstance(c, dict) and isinstance(c.get("text"), str):
                                parts.append(c["text"])
        return "".join(parts)

    @staticmethod
    def extract_last_text(items: list[RunItem]) -> str | None:
        """Return the text of the last MessageOutputItem, if any."""
        for item in reversed(items):
            if isinstance(item, MessageOutputItem):
                raw = item.raw_item
                if isinstance(raw, dict):
                    content = raw.get("content")
                    if isinstance(content, str):
                        return content
                    if isinstance(content, list):
                        for c in reversed(content):
                            if isinstance(c, dict) and isinstance(c.get("text"), str):
                                return c["text"]
        return None

    # ---- factory helpers ----

    @staticmethod
    def text_message_output(text: str, *, role: str = "assistant") -> TResponseInputItem:
        """Build a provider-neutral message output item payload."""
        return {
            "type": "message",
            "role": role,
            "content": [{"type": "output_text", "text": text}],
        }

    @staticmethod
    def tool_call_output_item(
        tool_call: Any, output: Any
    ) -> TResponseInputItem:
        """Build a `function_call_output` input item matching a `tool_call`."""
        call_id: str | None = None
        if isinstance(tool_call, dict):
            call_id = tool_call.get("call_id")
        else:
            call_id = getattr(tool_call, "call_id", None)
        return {
            "type": "function_call_output",
            "call_id": call_id or "unknown",
            "output": output if isinstance(output, str) else str(output),
        }

    @staticmethod
    def function_call_item(
        *, name: str, arguments: str, call_id: str
    ) -> TResponseInputItem:
        return {
            "type": "function_call",
            "name": name,
            "arguments": arguments,
            "call_id": call_id,
        }


__all__ = [
    "CompactionItem",
    "HandoffCallItem",
    "HandoffOutputItem",
    "ItemHelpers",
    "MCPApprovalRequestItem",
    "MCPApprovalResponseItem",
    "MCPListToolsItem",
    "MessageOutputItem",
    "ModelResponse",
    "ReasoningItem",
    "RunItem",
    "RunItemBase",
    "ToolApprovalItem",
    "ToolCallItem",
    "ToolCallOutputItem",
    "ToolSearchCallItem",
    "ToolSearchOutputItem",
    "TResponseInputItem",
    "TResponseOutputItem",
    "TResponseStreamEvent",
]