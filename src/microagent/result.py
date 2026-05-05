"""RunResult / RunResultStreaming — what `Runner.run*` returns.

- `RunResult` (non-streaming): complete, final-output-ready snapshot.
- `RunResultStreaming` (streaming): lazy async iterator over `StreamEvent`s.

Both derive from `RunResultBase` so code that only needs `final_output / new_items` works
transparently. `to_state()` materializes a resumable `RunState` snapshot including model
responses, guardrail results, and the prompt-cache key.
"""
from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from .util._pretty_print import (
    pretty_print_result,
    pretty_print_run_result_streaming,
)

if TYPE_CHECKING:
    from .agent import Agent
    from .guardrail import InputGuardrailResult, OutputGuardrailResult
    from .items import ModelResponse, RunItem, ToolApprovalItem, TResponseInputItem
    from .run_context import RunContextWrapper
    from .run_state import RunState
    from .stream_events import StreamEvent
    from .tool_guardrails import ToolInputGuardrailResult, ToolOutputGuardrailResult


@dataclass(frozen=True)
class AgentToolInvocation:
    """Metadata carried when an agent is invoked via `agent.as_tool(...)`."""

    tool_name: str
    tool_call_id: str
    tool_arguments: str


@dataclass
class RunResultBase:
    """Shared fields between streaming and non-streaming results."""

    input: str | list[TResponseInputItem] = ""
    new_items: list[RunItem] = field(default_factory=list)
    raw_responses: list[ModelResponse] = field(default_factory=list)
    final_output: Any = None
    last_agent: Agent[Any] | None = None
    input_guardrail_results: list[InputGuardrailResult] = field(default_factory=list)
    output_guardrail_results: list[OutputGuardrailResult] = field(default_factory=list)
    tool_input_guardrail_results: list[ToolInputGuardrailResult[Any]] = field(
        default_factory=list
    )
    tool_output_guardrail_results: list[ToolOutputGuardrailResult[Any]] = field(
        default_factory=list
    )
    interruptions: list[ToolApprovalItem] = field(default_factory=list)
    context_wrapper: RunContextWrapper[Any] | None = None

    # Private metadata stashes (carried by Runner; not for user mutation)
    _starting_agent_for_state: Agent[Any] | None = None
    _reasoning_item_id_policy: Any = None
    _generated_prompt_cache_key: str | None = None

    # ---- resume helpers ----

    def to_input_list(self) -> list[TResponseInputItem]:
        """Return the full input that a follow-up call should receive (history + new items)."""
        from .items import ItemHelpers

        history = ItemHelpers.input_to_new_input_list(self.input)
        extras: list[TResponseInputItem] = []
        for item in self.new_items:
            try:
                extras.append(item.to_input_item())
            except Exception:
                continue
        return history + extras


@dataclass
class RunResult(RunResultBase):
    """Non-streaming result."""

    def __str__(self) -> str:  # pragma: no cover
        return pretty_print_result(self)

    def to_state(self) -> RunState[Any, Any]:
        """Construct a resumable RunState from this result."""
        from .run_state import RunState

        state = RunState(
            context=self.context_wrapper,
            original_input=self.input,
            starting_agent=self._starting_agent_for_state or self.last_agent,
        )
        state._current_agent = self.last_agent
        state._generated_items = list(self.new_items)
        state._model_responses = list(self.raw_responses)
        state._input_guardrail_results = list(self.input_guardrail_results)
        state._output_guardrail_results = list(self.output_guardrail_results)
        state._generated_prompt_cache_key = self._generated_prompt_cache_key
        return state


class _QueueSentinel:
    pass


QUEUE_COMPLETE = _QueueSentinel()


@dataclass
class RunResultStreaming(RunResultBase):
    """Streaming result. Consumers drive progress via `async for ev in result.stream_events()`."""

    is_complete: bool = False
    current_agent: Agent[Any] | None = None
    current_turn: int = 0
    _event_queue: asyncio.Queue[Any] = field(default_factory=asyncio.Queue)
    _input_guardrail_queue: asyncio.Queue[Any] = field(default_factory=asyncio.Queue)
    _stored_exception: BaseException | None = None
    _triggered_input_guardrail_result: InputGuardrailResult | None = None
    _background_task: asyncio.Task[Any] | None = None

    def __str__(self) -> str:  # pragma: no cover
        return pretty_print_run_result_streaming(self)

    async def stream_events(self) -> AsyncIterator[StreamEvent]:
        """Yield events as they arrive. Terminates on `QUEUE_COMPLETE` or stored exception."""
        while True:
            event = await self._event_queue.get()
            if isinstance(event, _QueueSentinel):
                break
            yield event
        if self._stored_exception is not None:
            raise self._stored_exception

    # `events()` is a friendly alias used by examples and addons.
    events = stream_events

    async def cancel(self) -> None:
        """Cancel the background runner task (if any)."""
        if self._background_task is not None and not self._background_task.done():
            self._background_task.cancel()
            try:
                await self._background_task
            except Exception:
                pass

    def to_state(self) -> RunState[Any, Any]:
        """Same semantics as `RunResult.to_state`."""
        from .run_state import RunState

        state = RunState(
            context=self.context_wrapper,
            original_input=self.input,
            starting_agent=self._starting_agent_for_state or self.last_agent,
        )
        state._current_agent = self.current_agent or self.last_agent
        state._generated_items = list(self.new_items)
        state._model_responses = list(self.raw_responses)
        state._input_guardrail_results = list(self.input_guardrail_results)
        state._output_guardrail_results = list(self.output_guardrail_results)
        state._current_turn = self.current_turn
        state._generated_prompt_cache_key = self._generated_prompt_cache_key
        return state


__all__ = [
    "AgentToolInvocation",
    "QUEUE_COMPLETE",
    "RunResult",
    "RunResultBase",
    "RunResultStreaming",
]