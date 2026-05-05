"""Approval coordination — approval-aware tool execution + rejection synthesis.

Helpers used by the run loop when a tool requires HITL approval. The actual approval state
lives on `RunContextWrapper._approvals`; here we just translate between approval items and
synthetic tool outputs that surface the result back to the model.
"""
from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from ..items import (
    ItemHelpers,
    RunItem,
    ToolApprovalItem,
    ToolCallOutputItem,
    TResponseInputItem,
)
from ..run_context import RunContextWrapper
from ..tool import DEFAULT_APPROVAL_REJECTION_MESSAGE
from .items import REJECTION_MESSAGE, function_rejection_item, run_item_to_input_item


def filter_tool_approvals(items: Sequence[Any]) -> list[ToolApprovalItem]:
    """Keep only `ToolApprovalItem` entries from a mixed interruption payload."""
    return [it for it in items if isinstance(it, ToolApprovalItem)]


def approvals_from_step(step: Any) -> list[ToolApprovalItem]:
    interruptions = getattr(step, "interruptions", None) or []
    return filter_tool_approvals(interruptions)


def get_approval_decision(
    *, context: RunContextWrapper[Any], approval: ToolApprovalItem
) -> tuple[str, str | None]:
    """Resolve an approval into (decision, message).

    `decision` is one of:
      - "pending"  → still waiting on the user
      - "approved" → run the tool
      - "rejected" → emit the rejection message instead
    """
    status = context.get_approval_status(
        tool_name=approval.tool_name,
        call_id=approval.call_id,
        tool_namespace=approval.tool_namespace,
    )
    if status is True:
        return "approved", None
    if status is False:
        # Pull a sticky / per-call rejection message if one was set.
        key = context._resolve_approval_key(approval)
        record = context._approvals.get(key)
        message: str | None = None
        if record is not None:
            message = record.rejection_messages.get(approval.call_id)
            if message is None and record.sticky_rejection_message is not None:
                message = record.sticky_rejection_message
        return "rejected", message or REJECTION_MESSAGE
    return "pending", None


def append_approval_rejection_output(
    *,
    generated_items: list[RunItem],
    agent: Any,
    approval: ToolApprovalItem,
    message: str = DEFAULT_APPROVAL_REJECTION_MESSAGE,
) -> None:
    """Emit a synthetic tool output so the model sees why the approval failed."""
    raw = function_rejection_item(call_id=approval.call_id, message=message)
    generated_items.append(
        ToolCallOutputItem(
            agent=agent,
            raw_item=raw,
            output=message,
        )
    )


def append_input_items_excluding_approvals(
    base_input: list[TResponseInputItem], items: Sequence[RunItem]
) -> None:
    """Append tool outputs to model input while skipping approval placeholders."""
    for item in items:
        converted = run_item_to_input_item(item)
        if converted is None:
            continue
        base_input.append(converted)


__all__ = [
    "append_approval_rejection_output",
    "append_input_items_excluding_approvals",
    "approvals_from_step",
    "filter_tool_approvals",
    "get_approval_decision",
]