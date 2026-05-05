"""Tracing identifier helpers."""
from __future__ import annotations

import uuid


def gen_trace_id() -> str:
    return f"trace_{uuid.uuid4().hex}"


def gen_span_id() -> str:
    return f"span_{uuid.uuid4().hex[:16]}"