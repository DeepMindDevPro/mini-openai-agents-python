"""Input normalization + rejection-item builders used by the run loop."""
from __future__ import annotations

import copy
from typing import Any, Literal

from ..items import RunItem, ToolApprovalItem, TResponseInputItem
from ..tool import DEFAULT_APPROVAL_REJECTION_MESSAGE

ReasoningItemIdPolicy = Literal["preserve", "omit"]
REJECTION_MESSAGE = DEFAULT_APPROVAL_REJECTION_MESSAGE


def copy_input_items(
    value: str | list[TResponseInputItem],
) -> str | list[TResponseInputItem]:
    """Return a shallow copy of input items to avoid cross-turn mutation."""
    if isinstance(value, str):
        return value
    return [dict(i) for i in value]


def normalize_resumed_input(
    value: str | list[TResponseInputItem],
) -> list[TResponseInputItem]:
    """Normalize an input into list form (`[{"role": "user", "content": ...}, ...]`)."""
    if isinstance(value, str):
        return [{"role": "user", "content": value}]
    return [dict(i) for i in value]


def run_item_to_input_item(
    run_item: RunItem,
    reasoning_item_id_policy: ReasoningItemIdPolicy | None = None,
) -> TResponseInputItem | None:
    """Convert a RunItem back to a model-facing input item.

    Returns `None` for items that should not be forwarded (e.g. ToolApprovalItem).
    """
    if run_item.type == "tool_approval_item":
        return None
    try:
        return run_item.to_input_item()
    except Exception:
        raw = getattr(run_item, "raw_item", None)
        if isinstance(raw, dict):
            return dict(raw)
        return None


def run_items_to_input_items(
    items: list[RunItem],
    reasoning_item_id_policy: ReasoningItemIdPolicy | None = None,
) -> list[TResponseInputItem]:
    out: list[TResponseInputItem] = []
    for item in items:
        converted = run_item_to_input_item(item, reasoning_item_id_policy)
        if converted is not None:
            out.append(converted)
    return out


def function_rejection_item(
    *,
    call_id: str,
    message: str = REJECTION_MESSAGE,
) -> TResponseInputItem:
    """Synthetic tool-output that says "this call was rejected by approval policy"."""
    return {
        "type": "function_call_output",
        "call_id": call_id,
        "output": message,
    }


__all__ = [
    "REJECTION_MESSAGE",
    "ReasoningItemIdPolicy",
    "copy_input_items",
    "function_rejection_item",
    "normalize_resumed_input",
    "run_item_to_input_item",
    "run_items_to_input_items",
]