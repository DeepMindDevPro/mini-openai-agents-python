"""Run-level error handlers — turn `MaxTurnsExceeded` / `ModelRefusalError` into final outputs.

Behaviour mirrors `openai-agents-python`: handlers receive a `RunErrorHandlerInput` carrying
the snapshot of progress so far and may return a `RunErrorHandlerResult`, a dict with
`final_output`, a raw value, or `None` to re-raise.
"""
from __future__ import annotations

import inspect
from typing import Any

from ..exceptions import MaxTurnsExceeded, ModelRefusalError
from ..items import ItemHelpers, ModelResponse, RunItem, TResponseInputItem
from ..run_context import RunContextWrapper
from ..run_error_handlers import (
    RunErrorData,
    RunErrorHandlerInput,
    RunErrorHandlerResult,
    RunErrorHandlers,
)
from .items import run_item_to_input_item


def build_run_error_data(
    *,
    input: str | list[TResponseInputItem],
    new_items: list[RunItem],
    raw_responses: list[ModelResponse],
    last_agent: Any,
) -> RunErrorData:
    history: list[TResponseInputItem] = ItemHelpers.input_to_new_input_list(input)
    output: list[TResponseInputItem] = []
    for item in new_items:
        converted = run_item_to_input_item(item)
        if converted is None:
            continue
        output.append(converted)
    return RunErrorData(
        input=input,
        new_items=list(new_items),
        history=history + list(output),
        output=output,
        raw_responses=list(raw_responses),
        last_agent=last_agent,
    )


async def maybe_handle_run_error(
    *,
    error: MaxTurnsExceeded | ModelRefusalError,
    handlers: RunErrorHandlers[Any] | None,
    context: RunContextWrapper[Any],
    run_data: RunErrorData,
) -> RunErrorHandlerResult | None:
    """Run the matching handler; return the result if any, else None (caller re-raises)."""
    if not handlers:
        return None

    key = "max_turns" if isinstance(error, MaxTurnsExceeded) else "model_refusal"
    handler = handlers.get(key)  # type: ignore[arg-type]
    if handler is None:
        return None

    payload: RunErrorHandlerInput[Any] = RunErrorHandlerInput(
        error=error, context=context, run_data=run_data
    )
    raw = handler(payload)
    if inspect.isawaitable(raw):
        raw = await raw

    if raw is None:
        return None
    if isinstance(raw, RunErrorHandlerResult):
        return raw
    if isinstance(raw, dict) and "final_output" in raw:
        include = bool(raw.get("include_in_history", True))
        return RunErrorHandlerResult(final_output=raw["final_output"], include_in_history=include)
    # Treat as a raw final_output value.
    return RunErrorHandlerResult(final_output=raw)


__all__ = [
    "build_run_error_data",
    "maybe_handle_run_error",
]