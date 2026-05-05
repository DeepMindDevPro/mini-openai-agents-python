"""RunContextWrapper and approval tracking.

The `RunContextWrapper` carries:
- A user-provided generic context object (arbitrary deps).
- Cumulative `Usage` for the run.
- Per-tool approval records, keyed by the tool's approval key (name / namespace / call_id).

`_ApprovalRecord` tracks four kinds of state:
- `approved` — bool (always-approve) or list[call_id] (per-call approvals).
- `rejected` — bool (always-reject) or list[call_id] (per-call rejections).
- `rejection_messages` — map of call_id → override message for rejected calls.
- `sticky_rejection_message` — set once, applies to all future rejections for this tool.

`AgentHookContext` extends `RunContextWrapper` with an `agent_name` so agent-scoped hooks
(`on_agent_start` / `on_agent_end`) can be typed narrowly.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Generic

from typing_extensions import TypeVar

from ._tool_identity import (
    NamedToolLookupKey,
    get_function_tool_approval_keys,
    tool_qualified_name,
)
from .usage import Usage

if TYPE_CHECKING:
    from .items import ToolApprovalItem

TContext = TypeVar("TContext", default=Any)


@dataclass(eq=False)
class _ApprovalRecord:
    approved: bool | list[str] = field(default_factory=list)
    rejected: bool | list[str] = field(default_factory=list)
    rejection_messages: dict[str, str] = field(default_factory=dict)
    sticky_rejection_message: str | None = None


@dataclass(eq=False)
class RunContextWrapper(Generic[TContext]):
    """Wraps the user-provided context object together with run-scoped state.

    Contexts are **never** sent to the LLM — they are dependency / state passthroughs
    for tools, hooks, and guardrails.
    """

    context: TContext = None  # type: ignore[assignment]
    usage: Usage = field(default_factory=Usage)
    turn_input: list[Any] = field(default_factory=list)
    _approvals: dict[str, _ApprovalRecord] = field(default_factory=dict)
    tool_input: Any | None = None

    # ---- approval helpers ----

    @staticmethod
    def _resolve_tool_name(approval_item: ToolApprovalItem) -> str:
        name = getattr(approval_item, "tool_name", None)
        if isinstance(name, str) and name:
            return name
        raw = getattr(approval_item, "raw_item", None)
        if isinstance(raw, dict):
            candidate = raw.get("name") or raw.get("type")
        else:
            candidate = getattr(raw, "name", None) or getattr(raw, "type", None)
        return candidate if isinstance(candidate, str) and candidate else "unknown_tool"

    @staticmethod
    def _resolve_tool_namespace(approval_item: ToolApprovalItem) -> str | None:
        namespace = getattr(approval_item, "tool_namespace", None)
        if isinstance(namespace, str) and namespace:
            return namespace
        raw = getattr(approval_item, "raw_item", None)
        if isinstance(raw, dict):
            candidate = raw.get("namespace")
        else:
            candidate = getattr(raw, "namespace", None)
        return candidate if isinstance(candidate, str) and candidate else None

    @staticmethod
    def _resolve_tool_lookup_key(approval_item: ToolApprovalItem) -> NamedToolLookupKey | None:
        return getattr(approval_item, "tool_lookup_key", None)

    @staticmethod
    def _resolve_approval_key(approval_item: ToolApprovalItem) -> str:
        name = RunContextWrapper._resolve_tool_name(approval_item)
        namespace = RunContextWrapper._resolve_tool_namespace(approval_item)
        return tool_qualified_name(name, namespace) or name

    @staticmethod
    def _resolve_approval_keys(approval_item: ToolApprovalItem) -> list[NamedToolLookupKey]:
        return get_function_tool_approval_keys(
            tool_name=RunContextWrapper._resolve_tool_name(approval_item),
            tool_namespace=RunContextWrapper._resolve_tool_namespace(approval_item),
            tool_lookup_key=RunContextWrapper._resolve_tool_lookup_key(approval_item),
        )

    def _record_for(self, key: str) -> _ApprovalRecord:
        return self._approvals.setdefault(key, _ApprovalRecord())

    def approve_tool(
        self,
        approval_item: ToolApprovalItem,
        *,
        always_approve: bool = False,
    ) -> None:
        key = self._resolve_approval_key(approval_item)
        rec = self._record_for(key)
        if always_approve:
            rec.approved = True
        else:
            call_id = approval_item.call_id or ""
            if isinstance(rec.approved, list):
                if call_id and call_id not in rec.approved:
                    rec.approved.append(call_id)
            # if already True, nothing to do

    def reject_tool(
        self,
        approval_item: ToolApprovalItem,
        *,
        always_reject: bool = False,
        message: str | None = None,
    ) -> None:
        key = self._resolve_approval_key(approval_item)
        rec = self._record_for(key)
        if always_reject:
            rec.rejected = True
            if message:
                rec.sticky_rejection_message = message
        else:
            call_id = approval_item.call_id or ""
            if isinstance(rec.rejected, list):
                if call_id and call_id not in rec.rejected:
                    rec.rejected.append(call_id)
            if message and call_id:
                rec.rejection_messages[call_id] = message

    def get_approval_status(
        self,
        tool_name: str,
        call_id: str,
        *,
        tool_namespace: str | None = None,
        existing_pending: ToolApprovalItem | None = None,
    ) -> bool | None:
        """Return True/False if the tool is approved/rejected, None if still pending."""
        key = tool_qualified_name(tool_name, tool_namespace) or tool_name
        rec = self._approvals.get(key)
        if rec is None:
            return None
        if rec.rejected is True:
            return False
        if isinstance(rec.rejected, list) and call_id in rec.rejected:
            return False
        if rec.approved is True:
            return True
        if isinstance(rec.approved, list) and call_id in rec.approved:
            return True
        return None


@dataclass(eq=False)
class AgentHookContext(RunContextWrapper[TContext], Generic[TContext]):
    """Context specialization passed to agent-level hooks (on_agent_start/end)."""

    agent_name: str | None = None


__all__ = ["AgentHookContext", "RunContextWrapper", "TContext", "_ApprovalRecord"]