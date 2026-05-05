"""RunState — schema-versioned snapshot used for resume / HITL.

Schema policy (see AGENTS.md §1.3):
- `CURRENT_SCHEMA_VERSION` MUST come with a one-line entry in `SCHEMA_VERSION_SUMMARIES`.
- Older SDKs refuse newer snapshots (fail-fast forward compat).
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Generic, TypeVar

from .items import TResponseInputItem

InputT = TypeVar("InputT")
OutputT = TypeVar("OutputT")

CURRENT_SCHEMA_VERSION = "1.0"
SCHEMA_VERSION_SUMMARIES: dict[str, str] = {
    "1.0": "Initial RunState schema: starting agent, generated items, prompt cache key, "
    "approvals, conversation history.",
}

# Import-time invariant: the current schema version must have a non-empty summary.
assert CURRENT_SCHEMA_VERSION in SCHEMA_VERSION_SUMMARIES, (
    f"CURRENT_SCHEMA_VERSION {CURRENT_SCHEMA_VERSION!r} missing from "
    "SCHEMA_VERSION_SUMMARIES (see AGENTS.md §1.3)"
)
assert SCHEMA_VERSION_SUMMARIES[CURRENT_SCHEMA_VERSION].strip(), (
    f"SCHEMA_VERSION_SUMMARIES[{CURRENT_SCHEMA_VERSION!r}] must be non-empty"
)


class RunState(Generic[InputT, OutputT]):
    """State object for resuming agent runs.

    v0.2: full resume support — generated items, model responses, guardrail results,
    approvals, prompt cache key, schema-versioned (de)serialization.
    """

    def __init__(
        self,
        *,
        context: Any = None,
        original_input: InputT | None = None,
        starting_agent: Any = None,
        max_turns: int = 10,
        conversation_id: str | None = None,
        previous_response_id: str | None = None,
    ) -> None:
        self._context = context
        self._original_input = original_input
        self._starting_agent = starting_agent
        self._current_agent = starting_agent
        self._max_turns = max_turns
        self._current_turn = 0
        self._conversation_id = conversation_id
        self._previous_response_id = previous_response_id

        self._generated_items: list[Any] = []
        self._model_responses: list[Any] = []
        self._input_guardrail_results: list[Any] = []
        self._output_guardrail_results: list[Any] = []
        self._conversation_history: list[TResponseInputItem] = []
        self._generated_prompt_cache_key: str | None = None

        # HITL / approval bookkeeping
        self._approved_call_ids: set[str] = set()
        self._rejected_call_ids: dict[str, str] = {}

    # ---- conversation helpers ----

    def get_conversation_history(self) -> list[TResponseInputItem]:
        """Reconstruct the conversation history from original input + generated items."""
        history: list[TResponseInputItem] = []

        # Original input first.
        original = self._original_input
        if isinstance(original, str):
            history.append({"role": "user", "content": original})
        elif isinstance(original, list):
            for item in original:
                if isinstance(item, dict):
                    history.append(dict(item))

        # Then any generated items that can convert back to input items.
        for item in self._generated_items:
            try:
                converted = item.to_input_item() if hasattr(item, "to_input_item") else None
            except Exception:
                converted = None
            if isinstance(converted, dict):
                history.append(converted)

        # Plus any explicitly tracked history (for backwards compatibility).
        history.extend(self._conversation_history)
        return history

    def add_to_history(self, item: TResponseInputItem) -> None:
        self._conversation_history.append(item)

    # ---- HITL helpers ----

    def approve(self, call_id: str) -> None:
        """Mark a tool-call as approved (per call-id)."""
        if not isinstance(call_id, str):
            return
        self._approved_call_ids.add(call_id)

    def reject(self, call_id: str, reason: str | None = None) -> None:
        """Mark a tool-call as rejected (per call-id), optionally with a reason."""
        if not isinstance(call_id, str):
            return
        self._rejected_call_ids[call_id] = reason or ""

    def set_prompt_cache_key(self, key: str) -> None:
        self._generated_prompt_cache_key = key

    # ---- (de)serialization ----

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": CURRENT_SCHEMA_VERSION,
            "max_turns": self._max_turns,
            "current_turn": self._current_turn,
            "conversation_id": self._conversation_id,
            "previous_response_id": self._previous_response_id,
            "starting_agent_name": getattr(self._starting_agent, "name", None),
            "current_agent_name": getattr(self._current_agent, "name", None),
            "original_input": _safe_jsonable(self._original_input),
            "generated_items": [_safe_jsonable(i) for i in self._generated_items],
            "model_responses": [_safe_jsonable(r) for r in self._model_responses],
            "conversation_history": list(self._conversation_history),
            "generated_prompt_cache_key": self._generated_prompt_cache_key,
            "approved_call_ids": sorted(self._approved_call_ids),
            "rejected_call_ids": dict(self._rejected_call_ids),
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), default=str)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RunState[Any, Any]":
        version = data.get("schema_version")
        if version is not None and version != CURRENT_SCHEMA_VERSION:
            # Forward-compat is fail-fast; older SDKs refuse newer snapshots.
            if _is_newer_version(version, CURRENT_SCHEMA_VERSION):
                raise ValueError(
                    f"RunState snapshot is schema version {version!r}; "
                    f"this SDK only understands {CURRENT_SCHEMA_VERSION!r}."
                )
        state = cls(
            context=None,
            original_input=data.get("original_input"),
            starting_agent=None,
            max_turns=int(data.get("max_turns", 10)),
            conversation_id=data.get("conversation_id"),
            previous_response_id=data.get("previous_response_id"),
        )
        state._current_turn = int(data.get("current_turn", 0))
        state._conversation_history = list(data.get("conversation_history") or [])
        state._generated_prompt_cache_key = data.get("generated_prompt_cache_key")
        state._approved_call_ids = set(data.get("approved_call_ids") or [])
        state._rejected_call_ids = dict(data.get("rejected_call_ids") or {})
        return state

    @classmethod
    def from_json(cls, text: str) -> "RunState[Any, Any]":
        return cls.from_dict(json.loads(text))


def _is_newer_version(a: str, b: str) -> bool:
    """Best-effort `a > b` comparison for dotted version strings."""
    try:
        ta = tuple(int(p) for p in str(a).split("."))
        tb = tuple(int(p) for p in str(b).split("."))
        return ta > tb
    except Exception:
        return False


def _safe_jsonable(value: Any) -> Any:
    """Best-effort conversion of a value to a JSON-serializable shape."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(k): _safe_jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_safe_jsonable(v) for v in value]
    if hasattr(value, "to_dict"):
        try:
            return _safe_jsonable(value.to_dict())
        except Exception:
            pass
    if hasattr(value, "model_dump"):
        try:
            return _safe_jsonable(value.model_dump(exclude_none=True))
        except Exception:
            pass
    raw = getattr(value, "raw_item", None)
    if raw is not None and raw is not value:
        return _safe_jsonable(raw)
    return repr(value)


__all__ = [
    "CURRENT_SCHEMA_VERSION",
    "RunState",
    "SCHEMA_VERSION_SUMMARIES",
]