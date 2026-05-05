"""OpenAIServerConversationTracker — three-view dedupe for server-managed conversations.

When the model provider keeps the conversation server-side (`conversation_id` /
`previous_response_id` / `auto_previous_response_id`), the runner must only send **deltas**.
This tracker keeps three views of what's already been acknowledged:

1. **Object identity** — `id(item)` for items still alive in this Python process.
2. **Stable provider IDs** — `item.id` and `call_id` returned by the model.
3. **Content fingerprints** — SHA-256 of the canonical JSON, for resumed/retried runs where
   object identity has been lost.

When server-managed conversation is active, **local Session persistence is disabled** to
avoid double-writing.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any

from ..items import ModelResponse, RunItem, TResponseInputItem


def _stable_fingerprint(item: Any) -> str | None:
    """Best-effort canonical-JSON fingerprint of an input item."""
    try:
        if isinstance(item, dict):
            payload = item
        elif hasattr(item, "model_dump"):
            payload = item.model_dump(exclude_none=True)
        else:
            payload = {"raw": str(item)}
        text = json.dumps(payload, sort_keys=True, default=str)
    except Exception:
        return None
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _extract(value: Any, key: str) -> Any:
    if isinstance(value, dict):
        return value.get(key)
    return getattr(value, key, None)


@dataclass
class OpenAIServerConversationTracker:
    """Track delta-send eligibility across resumes / retries / process restarts."""

    conversation_id: str | None = None
    previous_response_id: str | None = None
    auto_previous_response_id: bool = False

    # In-process object identity for items already sent / acknowledged.
    sent_items: set[int] = field(default_factory=set)
    server_items: set[int] = field(default_factory=set)

    # Stable provider IDs.
    server_item_ids: set[str] = field(default_factory=set)
    server_tool_call_ids: set[str] = field(default_factory=set)

    # Content fingerprints for resume / retry.
    sent_item_fingerprints: set[str] = field(default_factory=set)

    sent_initial_input: bool = False
    primed_from_state: bool = False

    @property
    def is_active(self) -> bool:
        return bool(self.conversation_id or self.previous_response_id or self.auto_previous_response_id)

    def hydrate_from_state(
        self,
        *,
        original_input: str | list[TResponseInputItem],
        generated_items: list[RunItem],
        model_responses: list[ModelResponse],
    ) -> None:
        """Seed the tracker from a serialized RunState so resumed runs don't replay."""
        if self.sent_initial_input:
            return

        # Initial input: track fingerprints + provider IDs.
        if isinstance(original_input, list):
            for item in original_input:
                self._record_known(item)
        elif isinstance(original_input, str):
            fp = _stable_fingerprint({"role": "user", "content": original_input})
            if fp:
                self.sent_item_fingerprints.add(fp)

        self.sent_initial_input = True

        # Model responses: their output items are already on the server.
        for response in model_responses:
            for output_item in response.output:
                self._record_known(output_item, source="server")
            if self.conversation_id is None and response.response_id:
                self.previous_response_id = response.response_id

        # Generated run items.
        for item in generated_items:
            raw = getattr(item, "raw_item", None)
            if raw is not None:
                self._record_known(raw)
        self.primed_from_state = True

    def filter_outgoing(
        self, items: list[TResponseInputItem]
    ) -> list[TResponseInputItem]:
        """Drop items already acknowledged by the server. Returns only fresh deltas."""
        out: list[TResponseInputItem] = []
        for item in items:
            if id(item) in self.sent_items or id(item) in self.server_items:
                continue
            iid = _extract(item, "id")
            if isinstance(iid, str) and iid in self.server_item_ids:
                continue
            cid = _extract(item, "call_id")
            if isinstance(cid, str) and cid in self.server_tool_call_ids:
                # Only skip if the item carries a tool output (call already on server).
                if isinstance(item, dict) and "output" in item:
                    continue
            fp = _stable_fingerprint(item)
            if fp and fp in self.sent_item_fingerprints:
                continue
            out.append(item)
        return out

    def mark_input_as_sent(self, items: list[TResponseInputItem]) -> None:
        """Acknowledge items just sent so subsequent calls don't re-send them."""
        for item in items:
            self.sent_items.add(id(item))
            iid = _extract(item, "id")
            if isinstance(iid, str):
                self.server_item_ids.add(iid)
            cid = _extract(item, "call_id")
            if isinstance(cid, str) and isinstance(item, dict) and "output" in item:
                self.server_tool_call_ids.add(cid)
            fp = _stable_fingerprint(item)
            if fp:
                self.sent_item_fingerprints.add(fp)

    def record_response(self, response: ModelResponse) -> None:
        for output_item in response.output:
            self._record_known(output_item, source="server")
        if self.conversation_id is None and response.response_id:
            self.previous_response_id = response.response_id

    # ---- internals ----

    def _record_known(self, item: Any, *, source: str = "input") -> None:
        bucket = self.server_items if source == "server" else self.sent_items
        bucket.add(id(item))
        iid = _extract(item, "id")
        if isinstance(iid, str):
            self.server_item_ids.add(iid)
        cid = _extract(item, "call_id")
        if isinstance(cid, str):
            has_output = isinstance(item, dict) and "output" in item or hasattr(item, "output")
            if has_output:
                self.server_tool_call_ids.add(cid)
        fp = _stable_fingerprint(item)
        if fp:
            self.sent_item_fingerprints.add(fp)


__all__ = ["OpenAIServerConversationTracker"]