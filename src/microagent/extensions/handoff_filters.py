"""Common handoff input filters.

Use these to shape what the receiving agent sees after a handoff. Each filter takes a
`HandoffInputData` and returns a new `HandoffInputData` (or list of input items, depending
on the helper).
"""
from __future__ import annotations

from typing import Any

from ..handoffs import (
    HandoffInputData,
    default_handoff_history_mapper,
    nest_handoff_history,
)
from ..items import (
    HandoffCallItem,
    HandoffOutputItem,
    MCPApprovalRequestItem,
    MCPApprovalResponseItem,
    MCPListToolsItem,
    ReasoningItem,
    RunItem,
    ToolApprovalItem,
    ToolCallItem,
    ToolCallOutputItem,
    ToolSearchCallItem,
    ToolSearchOutputItem,
    TResponseInputItem,
)

_TOOL_INPUT_TYPES = frozenset(
    {
        "function_call",
        "function_call_output",
        "computer_call",
        "computer_call_output",
        "file_search_call",
        "tool_search_call",
        "tool_search_output",
        "web_search_call",
        "mcp_call",
        "mcp_list_tools",
        "mcp_approval_request",
        "mcp_approval_response",
        "reasoning",
        "code_interpreter_call",
        "image_generation_call",
        "local_shell_call",
        "local_shell_call_output",
        "shell_call",
        "shell_call_output",
        "apply_patch_call",
        "apply_patch_call_output",
    }
)

_TOOL_RUN_ITEM_TYPES = (
    HandoffCallItem,
    HandoffOutputItem,
    ToolSearchCallItem,
    ToolSearchOutputItem,
    ToolCallItem,
    ToolCallOutputItem,
    ReasoningItem,
    MCPListToolsItem,
    MCPApprovalRequestItem,
    MCPApprovalResponseItem,
    ToolApprovalItem,
)


def remove_all_tools(data: HandoffInputData) -> HandoffInputData:
    """Strip every tool / approval / reasoning item from the carried history."""
    history = data.input_history
    filtered_history: Any
    if isinstance(history, (list, tuple)):
        filtered_history = type(history)(
            it for it in history
            if not (isinstance(it, dict) and it.get("type") in _TOOL_INPUT_TYPES)
        )
    else:
        filtered_history = history

    return HandoffInputData(
        input_history=filtered_history,
        pre_handoff_items=tuple(
            it for it in data.pre_handoff_items if not isinstance(it, _TOOL_RUN_ITEM_TYPES)
        ),
        new_items=tuple(
            it for it in data.new_items if not isinstance(it, _TOOL_RUN_ITEM_TYPES)
        ),
        run_context=data.run_context,
        context=data.context,
        agent=data.agent,
        target_agent=data.target_agent,
    )


def keep_last_n_messages(data: HandoffInputData, n: int) -> HandoffInputData:
    """Truncate the carried history to the last `n` items (useful for compaction)."""
    history = data.input_history
    if isinstance(history, (list, tuple)) and n >= 0:
        sliced = list(history)[-n:]
        return HandoffInputData(
            input_history=type(history)(sliced) if isinstance(history, tuple) else sliced,
            pre_handoff_items=data.pre_handoff_items,
            new_items=data.new_items,
            run_context=data.run_context,
            context=data.context,
            agent=data.agent,
            target_agent=data.target_agent,
        )
    return data


__all__ = [
    "default_handoff_history_mapper",
    "keep_last_n_messages",
    "nest_handoff_history",
    "remove_all_tools",
]