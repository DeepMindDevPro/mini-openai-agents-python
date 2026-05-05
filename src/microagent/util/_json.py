"""JSON helpers that tolerate non-JSON objects."""
from __future__ import annotations

import dataclasses
import json
from typing import Any

from pydantic import BaseModel


def to_dump_compatible(value: Any) -> Any:
    """Convert a value into a JSON-serializable shape (best effort)."""
    if isinstance(value, BaseModel):
        return value.model_dump(exclude_none=True, mode="json")
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return dataclasses.asdict(value)
    if isinstance(value, dict):
        return {k: to_dump_compatible(v) for k, v in value.items()}
    if isinstance(value, list | tuple):
        return [to_dump_compatible(v) for v in value]
    return value


def safe_json_dumps(value: Any) -> str:
    """`json.dumps` that falls back to `str()` for non-serializable leaves."""
    try:
        return json.dumps(to_dump_compatible(value), ensure_ascii=False)
    except TypeError:
        return json.dumps(str(value), ensure_ascii=False)