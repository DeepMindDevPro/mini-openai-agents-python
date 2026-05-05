"""Top-level streaming facade.

Provides `run_streamed` as a convenience wrapper around `Runner.run_streamed`. The streaming
result is also available from `RunResultStreaming` and emits `StreamEvent` instances via
`stream_events()` / `events()`.
"""
from __future__ import annotations

from typing import Any

from .agent import Agent
from .items import TResponseInputItem
from .result import RunResultStreaming
from .run import Runner


def run_streamed(
    agent: Agent[Any],
    input: str | list[TResponseInputItem],
    *,
    context: Any = None,
    run_config: Any = None,
    hooks: Any = None,
    max_turns: int | None = None,
    previous_response_id: str | None = None,
    conversation_id: str | None = None,
) -> RunResultStreaming:
    """Streaming variant of `Runner.run`. Returns a `RunResultStreaming`."""
    kwargs: dict[str, Any] = {
        "context": context,
        "run_config": run_config,
        "hooks": hooks,
        "previous_response_id": previous_response_id,
        "conversation_id": conversation_id,
    }
    if max_turns is not None:
        kwargs["max_turns"] = max_turns
    return Runner.run_streamed(agent, input, **kwargs)


__all__ = ["run_streamed"]