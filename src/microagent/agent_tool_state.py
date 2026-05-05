"""Ephemeral state for `Agent-as-Tool` nested runs.

When an agent is wrapped with `agent.as_tool(...)` and the model calls it, the Runner needs to:
1. Track the nested `RunResult` while it is still "in flight" (pending approvals).
2. Resume the nested run after the parent's approval decision comes back.
3. Avoid leaking references across unrelated runs (scope isolation).

We implement this with module-level WeakRef maps keyed by the tool-call object id and a scope id
attached to the `RunContextWrapper` via an attribute. The `ContextVar`-based isolation is a
natural follow-up for addons that need true cross-run concurrency safety.
"""
from __future__ import annotations

import weakref
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .result import RunResult, RunResultStreaming

_AGENT_TOOL_STATE_SCOPE_ATTR = "_agent_tool_state_scope_id"

ToolCallSignature = tuple[str, str, str, str, str | None, str | None]
ScopedToolCallSignature = tuple[str | None, ToolCallSignature]

_results_by_obj: dict[int, Any] = {}
_results_by_sig: dict[ScopedToolCallSignature, set[int]] = {}
_sig_by_obj: dict[int, ScopedToolCallSignature] = {}
_callrefs: dict[int, weakref.ReferenceType[Any]] = {}


def get_agent_tool_state_scope(context: Any) -> str | None:
    scope_id = getattr(context, _AGENT_TOOL_STATE_SCOPE_ATTR, None)
    return scope_id if isinstance(scope_id, str) else None


def set_agent_tool_state_scope(context: Any, scope_id: str | None) -> None:
    if context is None:
        return
    try:
        if scope_id is None:
            try:
                delattr(context, _AGENT_TOOL_STATE_SCOPE_ATTR)
            except AttributeError:
                pass
            return
        setattr(context, _AGENT_TOOL_STATE_SCOPE_ATTR, scope_id)
    except Exception:
        return


def _signature(tool_call: Any) -> ToolCallSignature:
    return (
        getattr(tool_call, "call_id", "") or "",
        getattr(tool_call, "name", "") or "",
        getattr(tool_call, "arguments", "") or "",
        getattr(tool_call, "type", "") or "",
        getattr(tool_call, "id", None),
        getattr(tool_call, "status", None),
    )


def _scoped(tool_call: Any, *, scope_id: str | None) -> ScopedToolCallSignature:
    return (scope_id, _signature(tool_call))


def record_agent_tool_run_result(
    tool_call: Any,
    result: RunResult | RunResultStreaming,
    *,
    scope_id: str | None = None,
) -> None:
    obj_id = id(tool_call)
    sig = _scoped(tool_call, scope_id=scope_id)
    _results_by_obj[obj_id] = result
    _sig_by_obj[obj_id] = sig
    _results_by_sig.setdefault(sig, set()).add(obj_id)
    try:
        _callrefs[obj_id] = weakref.ref(tool_call, lambda _ref, oid=obj_id: _drop(oid))
    except TypeError:
        # non-weakreffable tool_call objects (e.g. dicts); silent fallback
        pass


def peek_agent_tool_run_result(
    tool_call: Any,
    *,
    scope_id: str | None = None,
) -> Any | None:
    obj_id = id(tool_call)
    if obj_id in _results_by_obj:
        return _results_by_obj[obj_id]
    sig = _scoped(tool_call, scope_id=scope_id)
    candidates = _results_by_sig.get(sig)
    if not candidates:
        return None
    for cand in candidates:
        result = _results_by_obj.get(cand)
        if result is not None:
            return result
    return None


def consume_agent_tool_run_result(
    tool_call: Any,
    *,
    scope_id: str | None = None,
) -> Any | None:
    result = peek_agent_tool_run_result(tool_call, scope_id=scope_id)
    if result is not None:
        _drop(id(tool_call))
    return result


def drop_agent_tool_run_result(tool_call_obj_id: int) -> None:
    _drop(tool_call_obj_id)


def _drop(obj_id: int) -> None:
    _callrefs.pop(obj_id, None)
    _results_by_obj.pop(obj_id, None)
    sig = _sig_by_obj.pop(obj_id, None)
    if sig is None:
        return
    candidates = _results_by_sig.get(sig)
    if candidates:
        candidates.discard(obj_id)
        if not candidates:
            _results_by_sig.pop(sig, None)


__all__ = [
    "consume_agent_tool_run_result",
    "drop_agent_tool_run_result",
    "get_agent_tool_state_scope",
    "peek_agent_tool_run_result",
    "record_agent_tool_run_result",
    "set_agent_tool_state_scope",
]