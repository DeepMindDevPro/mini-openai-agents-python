"""Model retry orchestration.

Wraps `Model.get_response` / `Model.stream_response` with the policy resolved from
`ModelSettings.retry`. Honours provider-supplied `ModelRetryAdvice` (which takes
precedence over the default policy) and applies an exponential-backoff-with-jitter
when no `retry_after` hint is available.
"""
from __future__ import annotations

import asyncio
import inspect
import random
from typing import Any, Awaitable, Callable

from ..retry import (
    ModelRetryAdvice,
    ModelRetryAdviceRequest,
    ModelRetryNormalizedError,
    ModelRetrySettings,
    RetryDecision,
    RetryPolicyContext,
    default_retry_policy,
)


def _normalize(error: Exception) -> ModelRetryNormalizedError:
    """Best-effort coercion of an arbitrary exception to `ModelRetryNormalizedError`."""
    status = getattr(error, "status_code", None)
    if status is None:
        status = getattr(error, "status", None)
    return ModelRetryNormalizedError(
        status_code=int(status) if isinstance(status, int) else None,
        error_code=getattr(error, "code", None),
        message=str(error),
        request_id=getattr(error, "request_id", None),
        retry_after=getattr(error, "retry_after", None),
        is_abort=isinstance(error, asyncio.CancelledError),
        is_network_error=isinstance(error, ConnectionError),
        is_timeout=isinstance(error, (TimeoutError, asyncio.TimeoutError)),
    )


async def _decide(
    error: Exception,
    settings: ModelRetrySettings,
    attempt: int,
    advice: ModelRetryAdvice | None,
) -> RetryDecision:
    normalized = _normalize(error)
    policy = settings.policy or default_retry_policy
    ctx = RetryPolicyContext(attempt=attempt, settings=settings, advice=advice)
    decision = policy(normalized, ctx)
    if inspect.isawaitable(decision):
        decision = await decision  # type: ignore[assignment]
    return decision  # type: ignore[return-value]


def _jittered(delay: float) -> float:
    """Apply ±25% uniform jitter to avoid thundering herds."""
    if delay <= 0:
        return 0.0
    spread = delay * 0.25
    return max(0.0, delay + random.uniform(-spread, spread))


async def call_with_retry(
    fn: Callable[[], Awaitable[Any]],
    *,
    settings: ModelRetrySettings | None,
    get_advice: Callable[[ModelRetryAdviceRequest], ModelRetryAdvice | None] | None = None,
) -> Any:
    """Invoke an async `fn` with retry logic governed by `settings`.

    `get_advice` is the provider-supplied hook (typically `model.get_retry_advice`).
    """
    if settings is None or settings.max_attempts is None:
        return await fn()

    attempt = 0
    while True:
        attempt += 1
        try:
            return await fn()
        except Exception as exc:  # noqa: BLE001
            advice: ModelRetryAdvice | None = None
            if get_advice is not None:
                try:
                    advice = get_advice(
                        ModelRetryAdviceRequest(
                            error=exc, normalized=_normalize(exc), attempt=attempt
                        )
                    )
                except Exception:
                    advice = None
            decision = await _decide(exc, settings, attempt, advice)
            if not decision.retry:
                raise
            delay = decision.delay_seconds or 0.0
            if (advice is not None) and advice.retry_after is not None:
                delay = advice.retry_after
            await asyncio.sleep(_jittered(delay))


__all__ = ["call_with_retry"]