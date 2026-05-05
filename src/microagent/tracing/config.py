"""TracingConfig — per-run tracing overrides."""
from __future__ import annotations

from typing import TypedDict

from typing_extensions import NotRequired


class TracingConfig(TypedDict, total=False):
    """Per-run tracing overrides."""

    api_key: NotRequired[str]
    """Optional API key used by the exporter (e.g. OpenAI tracing backend)."""


__all__ = ["TracingConfig"]