"""Run loop — main turn iteration + unified re-export panel.

Responsibilities (MVP):
1. Provide `run_single_turn` + `run_single_turn_streamed` + `get_new_response` — the only three
   functions the public `Runner` cares about.
2. Re-export the symbols from the horizontal slices (`turn_preparation`, `turn_resolution`,
   `guardrails`, `session_persistence`, …) so `run.py` has a single import surface.

Stream vs non-stream alignment:
- Both call `get_new_response` (wrapping `Model.get_response`).
- Both call `process_model_response` and `execute_tools_and_side_effects`.
- Only difference: the streaming variant enqueues `StreamEvent`s into `result._event_queue` as
  items arrive.

v0.2 status:
- `run_single_turn` is implemented here.
- Streaming is implemented in `Runner.run_streamed` (see `run.py`) on top of the non-streaming
  loop; `run_internal/streaming.py` provides the queue fan-out helpers.
"""
from __future__ import annotations

from typing import Any

from ..agent import Agent
from ..agent_output import AgentOutputSchemaBase
from ..handoffs import Handoff
from ..items import ItemHelpers, ModelResponse, RunItem, TResponseInputItem
from ..lifecycle import RunHooks
from ..logger import logger
from ..models.interface import Model, ModelTracing
from ..run_config import RunConfig
from ..run_context import RunContextWrapper
from ..stream_events import AgentUpdatedStreamEvent, RunItemStreamEvent
from ..tool import Tool
from .guardrails import (
    run_input_guardrails,
    run_output_guardrails,
    run_single_input_guardrail,
    run_single_output_guardrail,
)
from .items import (
    REJECTION_MESSAGE,
    copy_input_items,
    function_rejection_item,
    normalize_resumed_input,
    run_item_to_input_item,
    run_items_to_input_items,
)
from .run_steps import (
    NextStep,
    NextStepFinalOutput,
    NextStepHandoff,
    NextStepInterruption,
    NextStepRunAgain,
    ProcessedResponse,
    QueueCompleteSentinel,
    SingleStepResult,
)
from .session_persistence import prepare_input_with_session, save_result_to_session
from .turn_preparation import (
    get_all_tools,
    get_handoffs,
    get_model,
    get_output_schema,
    maybe_filter_model_input,
    validate_run_hooks,
)
from .turn_resolution import (
    build_next_step,
    execute_tools_and_side_effects,
    process_model_response,
)
from .run_grouping import (
    resolve_run_grouping, 
    resolve_run_grouping_id,
    generate_prompt_cache_key,
    get_prompt_cache_key_with_context,
)


# --------------------------------------------------------------------------- model call


async def get_new_response(
    *,
    model: Model,
    system_instructions: str | None,
    model_input: list[TResponseInputItem],
    tools: list[Tool],
    handoffs: list[Handoff],
    output_schema: AgentOutputSchemaBase | None,
    model_settings: Any,
    tracing: ModelTracing = ModelTracing.ENABLED,
    previous_response_id: str | None = None,
    conversation_id: str | None = None,
    prompt: Any | None = None,
) -> ModelResponse:
    """Single gateway into `Model.get_response`. Used by both stream and non-stream paths."""
    from .model_retry import call_with_retry

    async def _call() -> ModelResponse:
        return await model.get_response(
            system_instructions,
            model_input,
            model_settings,
            tools,
            output_schema,
            handoffs,
            tracing,
            previous_response_id=previous_response_id,
            conversation_id=conversation_id,
            prompt=prompt,
        )

    retry_settings = getattr(model_settings, "retry", None) if model_settings is not None else None
    return await call_with_retry(
        _call,
        settings=retry_settings,
        get_advice=getattr(model, "get_retry_advice", None),
    )


# --------------------------------------------------------------------------- single turn


async def run_single_turn(
    *,
    agent: Agent[Any],
    input_items: list[TResponseInputItem],
    context_wrapper: RunContextWrapper[Any],
    run_config: RunConfig,
    hooks: RunHooks[Any],
    previous_response_id: str | None = None,
    conversation_id: str | None = None,
) -> SingleStepResult:
    """Execute one agent turn: prepare → model → parse → run tools → decide next step."""
    tools = await get_all_tools(agent, context_wrapper)
    handoffs = await get_handoffs(agent, context_wrapper)
    output_schema = get_output_schema(agent)
    system_instructions = await agent.get_system_prompt(context_wrapper)

    model = get_model(agent, run_config)
    if model is None:
        from ..exceptions import UserError

        raise UserError(
            "No Model resolved for the agent. Pass `model=<Model instance>` to Agent(...) "
            "or set `run_config.model_provider`."
        )

    # Model input filter (last chance to rewrite before the call).
    filtered = await maybe_filter_model_input(
        agent=agent,
        run_config=run_config,
        context_wrapper=context_wrapper,
        input_items=input_items,
        system_instructions=system_instructions,
    )
    effective_input = filtered.input
    effective_instructions = filtered.instructions

    # LLM hooks (before).
    await hooks.on_llm_start(context_wrapper, agent, effective_instructions, effective_input)

    response = await get_new_response(
        model=model,
        system_instructions=effective_instructions,
        model_input=effective_input,
        tools=tools,
        handoffs=handoffs,
        output_schema=output_schema,
        model_settings=agent.model_settings.resolve(run_config.model_settings),
        previous_response_id=previous_response_id,
        conversation_id=conversation_id,
    )

    # Accumulate usage into the context.
    if response.usage is not None:
        for entry in response.usage.request_usage_entries:
            context_wrapper.usage.add(entry)

    await hooks.on_llm_end(context_wrapper, agent, response)

    processed = process_model_response(
        agent=agent,
        response=response,
        tools=tools,
        handoffs=handoffs,
        output_schema=output_schema,
    )

    tool_outputs: list[RunItem] = []
    if processed.has_tool_calls:
        tool_outputs = await execute_tools_and_side_effects(
            agent=agent,
            processed=processed,
            context_wrapper=context_wrapper,
            tools=tools,
        )

    all_new_items = list(processed.new_items) + list(tool_outputs)
    return SingleStepResult(
        new_items=all_new_items,
        model_response=response,
        next_step=build_next_step(processed),
    )


# --------------------------------------------------------------------------- streaming

# Streaming mirrors the non-streaming path by reusing `run_single_turn`. The
# per-item fan-out lives in `Runner.run_streamed` to keep the turn helpers provider-neutral.


__all__ = [
    # main-loop entry points
    "get_new_response",
    "run_single_turn",
    # re-export turn_preparation
    "get_all_tools",
    "get_handoffs",
    "get_output_schema",
    "get_model",
    "validate_run_hooks",
    "maybe_filter_model_input",
    # re-export turn_resolution
    "process_model_response",
    "execute_tools_and_side_effects",
    "build_next_step",
    # re-export guardrails
    "run_input_guardrails",
    "run_output_guardrails",
    "run_single_input_guardrail",
    "run_single_output_guardrail",
    # re-export items
    "REJECTION_MESSAGE",
    "copy_input_items",
    "function_rejection_item",
    "normalize_resumed_input",
    "run_item_to_input_item",
    "run_items_to_input_items",
    # re-export session_persistence
    "prepare_input_with_session",
    "save_result_to_session",
    # re-export run_steps
    "NextStep",
    "NextStepFinalOutput",
    "NextStepHandoff",
    "NextStepInterruption",
    "NextStepRunAgain",
    "ProcessedResponse",
    "QueueCompleteSentinel",
    "SingleStepResult",
]