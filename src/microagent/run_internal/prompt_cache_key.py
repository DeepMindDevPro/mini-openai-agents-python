"""PromptCacheKeyResolver — one generated prompt cache key per runner invocation.

The runner asks for a key on every model turn. This helper returns the same generated key
each time, persists it to the active `RunState` for resume flows, and opts out when the
request already forwards a user-supplied key through `ModelSettings.extra_args`.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
from typing import Any

from ..memory.session import Session
from ..model_settings import ModelSettings
from ..run_state import RunState
from .run_grouping import resolve_run_grouping

PROMPT_CACHE_KEY_FIELD = "prompt_cache_key"


@dataclass
class PromptCacheKeyResolver:
    """Provides the generated prompt cache key for a runner invocation."""

    run_state: RunState | None = None
    _generated_key: str | None = None

    @classmethod
    def from_run_state(cls, *, run_state: RunState | None) -> "PromptCacheKeyResolver":
        existing = run_state._generated_prompt_cache_key if run_state is not None else None
        return cls(run_state=run_state, _generated_key=existing)

    def resolve(
        self,
        model_settings: ModelSettings,
        *,
        model: Any,
        conversation_id: str | None,
        session: Session | None,
        group_id: str | None,
    ) -> str | None:
        """Return the generated key for this model call, or None to opt out."""
        if _model_settings_has_prompt_cache_key(model_settings):
            return None
        if not _model_supports_default_prompt_cache_key(model):
            return None
        return self._get_or_create(
            conversation_id=conversation_id, session=session, group_id=group_id
        )

    def _get_or_create(
        self,
        *,
        conversation_id: str | None,
        session: Session | None,
        group_id: str | None,
    ) -> str:
        if self._generated_key is not None:
            return self._generated_key

        kind, value = resolve_run_grouping(
            conversation_id=conversation_id, session=session, group_id=group_id
        )
        key = sha256(f"{kind}:{value}".encode("utf-8")).hexdigest()
        self._generated_key = key
        if self.run_state is not None:
            self.run_state._generated_prompt_cache_key = key
        return key


def _model_settings_has_prompt_cache_key(model_settings: ModelSettings | None) -> bool:
    if model_settings is None:
        return False
    extra = getattr(model_settings, "extra_args", None)
    if isinstance(extra, dict) and PROMPT_CACHE_KEY_FIELD in extra:
        return True
    extra_body = getattr(model_settings, "extra_body", None)
    if isinstance(extra_body, dict) and PROMPT_CACHE_KEY_FIELD in extra_body:
        return True
    return False


def _model_supports_default_prompt_cache_key(model: Any) -> bool:
    """True unless the model explicitly opts out via `supports_prompt_cache_key = False`."""
    if model is None:
        return False
    opt = getattr(model, "supports_prompt_cache_key", None)
    if isinstance(opt, bool):
        return opt
    return True


__all__ = ["PROMPT_CACHE_KEY_FIELD", "PromptCacheKeyResolver"]