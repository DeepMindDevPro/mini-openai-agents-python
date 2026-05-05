"""Error attachment helper used by tracing Spans."""
from __future__ import annotations

from typing import Any


def attach_error_to_current_span(error: Any) -> None:
    """Best-effort: attach an error payload to the current active span.

    The default NoOp tracing provider silently drops these;
    real exporters will record them in v0.2+.
    """
    return None