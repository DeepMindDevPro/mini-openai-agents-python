"""Trace base + NoOp / Impl variants."""
from __future__ import annotations

import abc
from dataclasses import dataclass, field
from types import TracebackType
from typing import Any

from .util import gen_trace_id


@dataclass
class TraceState:
    """Serializable trace metadata for resumed runs."""

    trace_id: str | None = None
    workflow_name: str | None = None
    group_id: str | None = None
    metadata: dict[str, Any] | None = None
    tracing_api_key_hash: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "workflow_name": self.workflow_name,
            "group_id": self.group_id,
            "metadata": self.metadata,
            "tracing_api_key_hash": self.tracing_api_key_hash,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TraceState:
        return cls(
            trace_id=data.get("trace_id"),
            workflow_name=data.get("workflow_name"),
            group_id=data.get("group_id"),
            metadata=data.get("metadata"),
            tracing_api_key_hash=data.get("tracing_api_key_hash"),
        )


class Trace(abc.ABC):
    """A workflow-level tracing scope."""

    @property
    @abc.abstractmethod
    def trace_id(self) -> str: ...

    @property
    @abc.abstractmethod
    def name(self) -> str: ...

    @abc.abstractmethod
    def start(self, mark_as_current: bool = False) -> None: ...

    @abc.abstractmethod
    def finish(self, reset_current: bool = False) -> None: ...

    def __enter__(self) -> Trace:
        self.start(mark_as_current=True)
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self.finish(reset_current=True)


class NoOpTrace(Trace):
    """Default trace — no-op, preserves CM contract."""

    def __init__(self, name: str = "noop") -> None:
        self._name = name
        self._trace_id = gen_trace_id()

    @property
    def trace_id(self) -> str:
        return self._trace_id

    @property
    def name(self) -> str:
        return self._name

    def start(self, mark_as_current: bool = False) -> None:
        return None

    def finish(self, reset_current: bool = False) -> None:
        return None


__all__ = ["NoOpTrace", "Trace", "TraceState"]