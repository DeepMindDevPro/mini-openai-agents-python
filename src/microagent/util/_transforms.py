"""Tiny string transforms used across the SDK."""
from __future__ import annotations

import re

_NON_ID = re.compile(r"[^A-Za-z0-9_]+")


def transform_string_function_style(name: str) -> str:
    """Normalize a human name to a snake_case-ish identifier for tool naming."""
    slug = _NON_ID.sub("_", name.strip()).strip("_")
    return slug.lower() or "tool"