"""Token usage accounting.

Mirrors the industrial shape of `openai-agents`' Usage: per-run totals plus per-request entries
so that RunState snapshots can faithfully reconstruct accounting after a resume. No OpenAI types
are leaked into the public API — we only carry plain integers and cache/reasoning sub-counts.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any


@dataclass
class TokenDetails:
    """Sub-breakdown of input or output tokens (cached / reasoning / audio…)."""

    cached_tokens: int = 0
    reasoning_tokens: int = 0

    def to_dict(self) -> dict[str, int]:
        return {
            "cached_tokens": self.cached_tokens,
            "reasoning_tokens": self.reasoning_tokens,
        }


@dataclass
class RequestUsage:
    """Usage accounting for a single model request."""

    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    input_tokens_details: TokenDetails = field(default_factory=TokenDetails)
    output_tokens_details: TokenDetails = field(default_factory=TokenDetails)

    def to_dict(self) -> dict[str, Any]:
        return {
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
            "input_tokens_details": self.input_tokens_details.to_dict(),
            "output_tokens_details": self.output_tokens_details.to_dict(),
        }


@dataclass
class Usage:
    """Cumulative token usage for an entire agent run."""

    requests: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    input_tokens_details: TokenDetails = field(default_factory=TokenDetails)
    output_tokens_details: TokenDetails = field(default_factory=TokenDetails)
    request_usage_entries: list[RequestUsage] = field(default_factory=list)

    def add(self, other: RequestUsage) -> None:
        """Accumulate another request's usage into this run total."""
        self.requests += 1
        self.input_tokens += other.input_tokens
        self.output_tokens += other.output_tokens
        self.total_tokens += other.total_tokens
        self.input_tokens_details.cached_tokens += other.input_tokens_details.cached_tokens
        self.output_tokens_details.reasoning_tokens += other.output_tokens_details.reasoning_tokens
        self.request_usage_entries.append(other)

    def to_dict(self) -> dict[str, Any]:
        return {
            "requests": self.requests,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
            "input_tokens_details": self.input_tokens_details.to_dict(),
            "output_tokens_details": self.output_tokens_details.to_dict(),
            "request_usage_entries": [e.to_dict() for e in self.request_usage_entries],
        }


def deserialize_usage(data: Mapping[str, Any]) -> Usage:
    """Rebuild a Usage from a previously serialized dict (best-effort)."""
    usage = Usage(
        requests=int(data.get("requests", 0)),
        input_tokens=int(data.get("input_tokens", 0)),
        output_tokens=int(data.get("output_tokens", 0)),
        total_tokens=int(data.get("total_tokens", 0)),
    )
    itd = data.get("input_tokens_details") or {}
    otd = data.get("output_tokens_details") or {}
    usage.input_tokens_details = TokenDetails(
        cached_tokens=int(itd.get("cached_tokens", 0)),
        reasoning_tokens=int(itd.get("reasoning_tokens", 0)),
    )
    usage.output_tokens_details = TokenDetails(
        cached_tokens=int(otd.get("cached_tokens", 0)),
        reasoning_tokens=int(otd.get("reasoning_tokens", 0)),
    )
    for entry in data.get("request_usage_entries") or []:
        if not isinstance(entry, Mapping):
            continue
        usage.request_usage_entries.append(
            RequestUsage(
                input_tokens=int(entry.get("input_tokens", 0)),
                output_tokens=int(entry.get("output_tokens", 0)),
                total_tokens=int(entry.get("total_tokens", 0)),
            )
        )
    return usage


# Aliases matching the `to_dict / from_dict` pair requested by upstream parity.
Usage.from_dict = classmethod(lambda cls, data: deserialize_usage(data))  # type: ignore[attr-defined]


def merge_request_usage(a: RequestUsage, b: RequestUsage) -> RequestUsage:
    """Combine two `RequestUsage` values — handy for streamed delta aggregation."""
    return RequestUsage(
        input_tokens=a.input_tokens + b.input_tokens,
        output_tokens=a.output_tokens + b.output_tokens,
        total_tokens=a.total_tokens + b.total_tokens,
        input_tokens_details=TokenDetails(
            cached_tokens=a.input_tokens_details.cached_tokens
            + b.input_tokens_details.cached_tokens,
            reasoning_tokens=a.input_tokens_details.reasoning_tokens
            + b.input_tokens_details.reasoning_tokens,
        ),
        output_tokens_details=TokenDetails(
            cached_tokens=a.output_tokens_details.cached_tokens
            + b.output_tokens_details.cached_tokens,
            reasoning_tokens=a.output_tokens_details.reasoning_tokens
            + b.output_tokens_details.reasoning_tokens,
        ),
    )


__all__ = [
    "RequestUsage",
    "TokenDetails",
    "Usage",
    "deserialize_usage",
    "merge_request_usage",
]