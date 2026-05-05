"""RunState resume helpers — bridge between a `RunResult` snapshot and a fresh `Runner.run`."""

from __future__ import annotations

from typing import Any, TypeVar

from .items import TResponseInputItem
from .run import Runner
from .run_state import RunState

InputT = TypeVar("InputT")
OutputT = TypeVar("OutputT")


def _build_combined_input(
    run_state: RunState[Any, Any],
    new_input: str | list[TResponseInputItem],
) -> list[TResponseInputItem]:
    history = run_state.get_conversation_history()
    combined: list[TResponseInputItem] = list(history)
    if isinstance(new_input, str):
        combined.append({"role": "user", "content": new_input})
    else:
        combined.extend(dict(i) if isinstance(i, dict) else i for i in new_input)
    return combined


def resume_run_state(
    *,
    run_state: RunState[Any, Any],
    new_input: str | list[TResponseInputItem],
    context: Any | None = None,
    run_config: Any | None = None,
    hooks: Any | None = None,
) -> Any:
    """Synchronously resume a run from saved state with new user input."""
    combined = _build_combined_input(run_state, new_input)
    return Runner.run_sync(
        run_state._starting_agent,
        combined,
        context=context if context is not None else run_state._context,
        run_config=run_config,
        hooks=hooks,
        previous_response_id=run_state._previous_response_id,
        conversation_id=run_state._conversation_id,
    )


async def async_resume_run_state(
    *,
    run_state: RunState[Any, Any],
    new_input: str | list[TResponseInputItem],
    context: Any | None = None,
    run_config: Any | None = None,
    hooks: Any | None = None,
) -> Any:
    """Async version of `resume_run_state`."""
    combined = _build_combined_input(run_state, new_input)
    return await Runner.run(
        run_state._starting_agent,
        combined,
        context=context if context is not None else run_state._context,
        run_config=run_config,
        hooks=hooks,
        previous_response_id=run_state._previous_response_id,
        conversation_id=run_state._conversation_id,
    )


def create_run_state_from_result(
    result: Any,
    original_input: str | list[TResponseInputItem],
) -> RunState[Any, Any]:
    """Materialize a `RunState` from a completed `RunResult` so the run can be resumed."""
    starting_agent = (
        getattr(result, "_starting_agent_for_state", None)
        or getattr(result, "last_agent", None)
    )
    state = RunState(
        context=getattr(result, "context_wrapper", None),
        original_input=original_input,
        starting_agent=starting_agent,
    )
    state._current_agent = getattr(result, "last_agent", None) or starting_agent
    state._generated_items = list(getattr(result, "new_items", []) or [])
    state._model_responses = list(getattr(result, "raw_responses", []) or [])
    state._input_guardrail_results = list(
        getattr(result, "input_guardrail_results", []) or []
    )
    state._output_guardrail_results = list(
        getattr(result, "output_guardrail_results", []) or []
    )
    state._generated_prompt_cache_key = getattr(result, "_generated_prompt_cache_key", None)
    return state


__all__ = [
    "async_resume_run_state",
    "create_run_state_from_result",
    "resume_run_state",
]