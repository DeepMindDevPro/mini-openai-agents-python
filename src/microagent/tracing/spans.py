"""Span base + NoOp / Impl variants."""
from __future__ import annotations

import abc
from types import TracebackType
from typing import Any, Generic, TypeVar

from typing_extensions import TypedDict

from .span_data import SpanData
from .util import gen_span_id

TSpanData = TypeVar("TSpanData", bound=SpanData)


class SpanError(TypedDict):
    """Payload attached to a span when an error occurs."""

    message: str
    data: dict[str, Any] | None


class Span(abc.ABC, Generic[TSpanData]):
    """A single timed unit within a trace."""

    @property
    @abc.abstractmethod
    def span_id(self) -> str: ...

    @property
    @abc.abstractmethod
    def trace_id(self) -> str: ...

    @property
    @abc.abstractmethod
    def span_data(self) -> TSpanData: ...

    @abc.abstractmethod
    def start(self, mark_as_current: bool = False) -> None: ...

    @abc.abstractmethod
    def finish(self, reset_current: bool = False) -> None: ...

    @abc.abstractmethod
    def set_error(self, error: SpanError) -> None: ...

    @abc.abstractmethod
    def set_output(self, output: Any) -> None: ...

    def __enter__(self) -> Span[TSpanData]:
        self.start(mark_as_current=True)
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self.finish(reset_current=True)


class NoOpSpan(Span[TSpanData]):
    """Default span — does nothing, but preserves the context-manager contract."""

    def __init__(self, data: TSpanData, *, trace_id: str = "no_trace") -> None:
        self._data = data
        self._span_id = gen_span_id()
        self._trace_id = trace_id

    @property
    def span_id(self) -> str:
        return self._span_id

    @property
    def trace_id(self) -> str:
        return self._trace_id

    @property
    def span_data(self) -> TSpanData:
        return self._data

    def start(self, mark_as_current: bool = False) -> None:
        return None

    def finish(self, reset_current: bool = False) -> None:
        return None

    def set_error(self, error: SpanError) -> None:
        return None

    def set_output(self, output: Any) -> None:
        return None


class SpanImpl(NoOpSpan[TSpanData]):
    """Real span implementation (carries error / output on the data payload).

    Processors registered via `add_trace_processor(...)` receive `start` / `finish`
    notifications from subclasses shipped by exporter addons; the core ships the data
    capture so the NoOp fallback still records the last error/output.
    """

    def set_error(self, error: SpanError) -> None:
        setattr(self._data, "error", dict(error))

    def set_output(self, output: Any) -> None:
        setattr(self._data, "output", output)


__all__ = ["NoOpSpan", "Span", "SpanError", "SpanImpl", "TSpanData"]