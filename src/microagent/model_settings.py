"""Provider-neutral ModelSettings.

Fields are the subset usable across Chat Completions / Responses / Claude / DeepSeek / etc.
Provider-specific extras should live in `extra_*` passthroughs; addons own their own shape.

Reasoning-effort / verbosity knobs (OpenAI o-series, DeepSeek R1) are first-class. MCP-flavoured
tool-choice shapes and other provider-specific hooks use `extra_args`.
"""
from __future__ import annotations

import dataclasses
from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from typing import Any, Literal, TypeAlias

from .retry import (
    ModelRetryBackoffInput,
    ModelRetryBackoffSettings,
    ModelRetrySettings,
    _coerce_backoff_settings,
)

ToolChoice: TypeAlias = Literal["auto", "required", "none"] | str | None


@dataclass
class ModelSettings:
    """Per-run tuning knobs for the model.

    Positional field order is a public contract. New fields append at the end only.
    """

    temperature: float | None = None
    top_p: float | None = None
    frequency_penalty: float | None = None
    presence_penalty: float | None = None
    max_tokens: int | None = None
    stop: list[str] | None = None
    tool_choice: ToolChoice = None
    parallel_tool_calls: bool | None = None
    seed: int | None = None
    response_format: dict[str, Any] | None = None

    # Reasoning / verbosity (optional; provider-specific but widely adopted)
    reasoning_effort: Literal["none", "low", "medium", "high"] | None = None
    verbosity: Literal["low", "medium", "high"] | None = None

    # Server-side behavior knobs
    store: bool | None = None
    include_usage: bool | None = None

    # Retry settings
    retry: ModelRetrySettings | None = None

    # Arbitrary provider-specific passthrough
    extra_headers: dict[str, str] | None = None
    extra_query: dict[str, Any] | None = None
    extra_body: dict[str, Any] | None = None
    extra_args: dict[str, Any] | None = None

    def resolve(self, override: ModelSettings | None) -> ModelSettings:
        """Overlay non-None fields from `override` on top of `self`."""
        if override is None:
            return self
        changes: dict[str, Any] = {}
        for f in dataclasses.fields(self):
            val = getattr(override, f.name)
            if val is not None:
                changes[f.name] = val
        return replace(self, **changes)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain dict (drops None).

        Retry settings get special handling to stay JSON-compatible.
        """
        out: dict[str, Any] = {}
        for f in dataclasses.fields(self):
            val = getattr(self, f.name)
            if val is None:
                continue
            if isinstance(val, ModelRetrySettings):
                retry_dict: dict[str, Any] = {}
                if val.max_attempts is not None:
                    retry_dict["max_attempts"] = val.max_attempts
                if val.backoff is not None:
                    retry_dict["backoff"] = val.backoff.to_json_dict()
                # policy is a callable; not serializable
                out["retry"] = retry_dict
            else:
                out[f.name] = val
        return out


__all__ = ["ModelSettings", "ToolChoice"]