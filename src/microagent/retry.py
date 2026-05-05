"""3-layer retry model.

    ModelRetryNormalizedError → RetryPolicy + RetryPolicyContext → RetryDecision

- `ModelRetryNormalizedError` — provider-neutral error facts (status / code / retry_after / …).
- `RetryPolicy`               — pure function from (normalized_error, context) → `RetryDecision`.
- `RetryDecision`             — `{retry: bool, delay_seconds: float | None, reason: str | None}`.

Providers may also supply a `ModelRetryAdvice` via `Model.get_retry_advice(...)` to surface
replay-safety and explicit server retry hints without coupling core to any SDK's error types.
"""
from __future__ import annotations

import dataclasses
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, TypeAlias

from .util._types import MaybeAwaitable


@dataclass
class ModelRetryBackoffSettings:
    """Runner-managed retry backoff configuration."""

    initial_delay: float | None = None
    max_delay: float | None = None
    multiplier: float | None = None
    jitter: bool | None = None

    def to_json_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


ModelRetryBackoffInput: TypeAlias = ModelRetryBackoffSettings | dict[str, Any] | None


@dataclass
class ModelRetrySettings:
    """Top-level retry settings attached to `ModelSettings` or `RunConfig`."""

    max_attempts: int | None = None
    policy: RetryPolicy | None = None
    backoff: ModelRetryBackoffSettings | None = None


@dataclass
class ModelRetryNormalizedError:
    """Provider-neutral error facts."""

    status_code: int | None = None
    error_code: str | None = None
    message: str | None = None
    request_id: str | None = None
    retry_after: float | None = None
    is_abort: bool = False
    is_network_error: bool = False
    is_timeout: bool = False


@dataclass
class ModelRetryAdviceRequest:
    """Input to `Model.get_retry_advice(...)`."""

    error: Exception
    normalized: ModelRetryNormalizedError
    attempt: int


@dataclass
class ModelRetryAdvice:
    """Provider-returned hint. Takes precedence over the default RetryPolicy if present."""

    replay_safe: bool = False
    retry_after: float | None = None
    reason: str | None = None


@dataclass
class RetryDecision:
    retry: bool
    delay_seconds: float | None = None
    reason: str | None = None


@dataclass
class RetryPolicyContext:
    attempt: int
    settings: ModelRetrySettings
    advice: ModelRetryAdvice | None = None


RetryPolicy: TypeAlias = Callable[
    [ModelRetryNormalizedError, RetryPolicyContext],
    MaybeAwaitable[RetryDecision],
]


def default_retry_policy(
    error: ModelRetryNormalizedError, context: RetryPolicyContext
) -> RetryDecision:
    """Retry on network errors, timeouts, and 5xx / 429 responses.

    Delay uses `retry_after` when present, otherwise an exponential backoff capped by
    settings.
    """
    max_attempts = context.settings.max_attempts or 3
    if context.attempt >= max_attempts:
        return RetryDecision(retry=False, reason="max_attempts reached")
    if error.is_abort:
        return RetryDecision(retry=False, reason="request aborted")
    if error.is_network_error or error.is_timeout:
        return RetryDecision(
            retry=True, delay_seconds=_backoff(context), reason="network/timeout"
        )
    if error.status_code is not None:
        if 500 <= error.status_code < 600 or error.status_code == 429:
            delay = error.retry_after if error.retry_after is not None else _backoff(context)
            return RetryDecision(retry=True, delay_seconds=delay, reason=f"status {error.status_code}")
    return RetryDecision(retry=False, reason="non-retryable")


def _backoff(ctx: RetryPolicyContext) -> float:
    s = ctx.settings.backoff or ModelRetryBackoffSettings()
    initial = s.initial_delay if s.initial_delay is not None else 1.0
    multiplier = s.multiplier if s.multiplier is not None else 2.0
    max_delay = s.max_delay if s.max_delay is not None else 30.0
    delay = min(initial * (multiplier ** (ctx.attempt - 1)), max_delay)
    return delay


retry_policies: dict[str, RetryPolicy] = {
    "default": default_retry_policy,
}


def _coerce_backoff_settings(value: ModelRetryBackoffInput) -> ModelRetryBackoffSettings | None:
    if value is None or isinstance(value, ModelRetryBackoffSettings):
        return value
    if isinstance(value, dict):
        return ModelRetryBackoffSettings(**value)
    raise TypeError(f"Unsupported backoff settings type: {type(value).__name__}")


__all__ = [
    "ModelRetryAdvice",
    "ModelRetryAdviceRequest",
    "ModelRetryBackoffInput",
    "ModelRetryBackoffSettings",
    "ModelRetryNormalizedError",
    "ModelRetrySettings",
    "RetryDecision",
    "RetryPolicy",
    "RetryPolicyContext",
    "default_retry_policy",
    "retry_policies",
]