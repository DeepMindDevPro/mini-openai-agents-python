"""Runner — the only public entry point.

Hosts `Runner` (sync / async / streamed). All business logic lives in
`run_internal/` (see AGENTS.md §1.1).
"""
from __future__ import annotations

import asyncio
from typing import Any

from .agent import Agent
from .exceptions import MaxTurnsExceeded, ModelRefusalError, UserError
from .items import RunItem, TResponseInputItem
from .lifecycle import RunHooks
from .result import QUEUE_COMPLETE, RunResult, RunResultStreaming
from .run_config import DEFAULT_MAX_TURNS, RunConfig
from .run_context import RunContextWrapper
from .run_error_handlers import RunErrorHandlers
from .run_internal.error_handlers import build_run_error_data, maybe_handle_run_error
from .run_internal.items import normalize_resumed_input
from .run_internal.oai_conversation import OpenAIServerConversationTracker
from .run_internal.prompt_cache_key import PromptCacheKeyResolver
from .run_internal.run_loop import run_single_turn
from .run_internal.run_steps import (
    NextStepFinalOutput,
    NextStepHandoff,
    NextStepInterruption,
    NextStepRunAgain,
)
from .run_internal.tool_use_tracker import AgentToolUseTracker, maybe_reset_tool_choice
from .run_internal.turn_preparation import validate_run_hooks
from .stream_events import (
    AgentUpdatedStreamEvent,
    RawResponsesStreamEvent,
    RunItemStreamEvent,
)


class Runner:
    """High-level driver around the per-turn loop."""

    @staticmethod
    async def run(
        agent: Agent[Any],
        input: str | list[TResponseInputItem],
        *,
        context: Any = None,
        run_config: RunConfig | None = None,
        hooks: Any = None,
        max_turns: int = DEFAULT_MAX_TURNS,
        previous_response_id: str | None = None,
        conversation_id: str | None = None,
        error_handlers: RunErrorHandlers[Any] | None = None,
    ) -> RunResult:
        """Run an agent to completion and return a `RunResult`."""
        cfg = run_config or RunConfig()
        run_hooks = validate_run_hooks(hooks)
        ctx = _coerce_context(context)

        input_items: list[TResponseInputItem] = normalize_resumed_input(input)

        tool_use_tracker = AgentToolUseTracker()
        # Server-managed conversation tracker: only active if ids are supplied.
        server_conv = OpenAIServerConversationTracker(
            conversation_id=conversation_id,
            previous_response_id=previous_response_id,
        )

        all_new_items: list[RunItem] = []
        raw_responses = []
        current_agent: Agent[Any] = agent
        starting_agent: Agent[Any] = agent
        final_output: Any = None
        turn = 0
        interruptions: list[Any] = []

        while True:
            turn += 1
            if turn > max_turns:
                error = MaxTurnsExceeded(
                    f"Run exceeded max_turns={max_turns} (current_turn={turn})"
                )
                run_data = build_run_error_data(
                    input=input,
                    new_items=all_new_items,
                    raw_responses=raw_responses,
                    last_agent=current_agent,
                )
                handled = await maybe_handle_run_error(
                    error=error,
                    handlers=error_handlers,
                    context=ctx,
                    run_data=run_data,
                )
                if handled is not None:
                    final_output = handled.final_output
                    break
                raise error

            step = await run_single_turn(
                agent=current_agent,
                input_items=input_items + _items_to_inputs(all_new_items),
                context_wrapper=ctx,
                run_config=cfg,
                hooks=run_hooks,
                previous_response_id=server_conv.previous_response_id,
                conversation_id=server_conv.conversation_id,
            )
            all_new_items.extend(step.new_items)
            if step.model_response is not None:
                raw_responses.append(step.model_response)
                server_conv.record_response(step.model_response)

            # Record any tool usage on the active agent for tool-choice reset.
            tool_use_tracker.record_run_items(current_agent, step.new_items)
            maybe_reset_tool_choice(
                current_agent, tool_use_tracker, current_agent.model_settings
            )

            last_step = step.next_step
            if isinstance(last_step, NextStepFinalOutput):
                final_output = last_step.final_output
                break
            if isinstance(last_step, NextStepHandoff):
                current_agent = last_step.target
                continue
            if isinstance(last_step, NextStepInterruption):
                interruptions = list(last_step.interruptions)
                break
            # NextStepRunAgain → loop again with same agent

        return RunResult(
            input=input,
            new_items=all_new_items,
            raw_responses=raw_responses,
            final_output=final_output,
            last_agent=current_agent,
            interruptions=interruptions,
            context_wrapper=ctx,
            _starting_agent_for_state=starting_agent,
        )

    @staticmethod
    def run_sync(
        agent: Agent[Any],
        input: str | list[TResponseInputItem],
        *,
        context: Any = None,
        run_config: RunConfig | None = None,
        hooks: Any = None,
        max_turns: int = DEFAULT_MAX_TURNS,
        previous_response_id: str | None = None,
        conversation_id: str | None = None,
        error_handlers: RunErrorHandlers[Any] | None = None,
    ) -> RunResult:
        """Synchronous wrapper. Spins up an event loop if none is running."""
        coro = Runner.run(
            agent,
            input,
            context=context,
            run_config=run_config,
            hooks=hooks,
            max_turns=max_turns,
            previous_response_id=previous_response_id,
            conversation_id=conversation_id,
            error_handlers=error_handlers,
        )
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Cannot block on a running loop; create a fresh one.
                return asyncio.run(coro)
        except RuntimeError:
            pass
        return asyncio.run(coro)

    @staticmethod
    def run_streamed(
        agent: Agent[Any],
        input: str | list[TResponseInputItem],
        *,
        context: Any = None,
        run_config: RunConfig | None = None,
        hooks: Any = None,
        max_turns: int = DEFAULT_MAX_TURNS,
        previous_response_id: str | None = None,
        conversation_id: str | None = None,
        error_handlers: RunErrorHandlers[Any] | None = None,
    ) -> RunResultStreaming:
        """Run an agent and return a `RunResultStreaming` whose `events()` yields stream events."""
        result = RunResultStreaming(
            input=input,
            current_agent=agent,
            _starting_agent_for_state=agent,
        )

        async def _drive() -> None:
            try:
                run_result = await Runner.run(
                    agent,
                    input,
                    context=context,
                    run_config=run_config,
                    hooks=hooks,
                    max_turns=max_turns,
                    previous_response_id=previous_response_id,
                    conversation_id=conversation_id,
                    error_handlers=error_handlers,
                )
                result.new_items = run_result.new_items
                result.raw_responses = run_result.raw_responses
                result.final_output = run_result.final_output
                result.last_agent = run_result.last_agent
                result.context_wrapper = run_result.context_wrapper
                result.interruptions = run_result.interruptions
                result._starting_agent_for_state = run_result._starting_agent_for_state

                # Replay items as RunItemStreamEvents.
                for response in run_result.raw_responses:
                    await result._event_queue.put(
                        RawResponsesStreamEvent(data={"response": getattr(response, "response_id", None)})
                    )
                for item in run_result.new_items:
                    name = getattr(item, "type", "message_output_created")
                    await result._event_queue.put(
                        RunItemStreamEvent(
                            name=_event_name_for_item(name),
                            item=item,
                            agent_name=getattr(item.agent, "name", None) if getattr(item, "agent", None) else None,
                        )
                    )
                if run_result.last_agent is not None and run_result.last_agent is not agent:
                    await result._event_queue.put(
                        AgentUpdatedStreamEvent(new_agent=run_result.last_agent)
                    )
                result.is_complete = True
            except BaseException as exc:  # noqa: BLE001
                result._stored_exception = exc
            finally:
                await result._event_queue.put(QUEUE_COMPLETE)

        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        result._background_task = loop.create_task(_drive())
        return result


def _coerce_context(context: Any) -> RunContextWrapper[Any]:
    if isinstance(context, RunContextWrapper):
        return context
    return RunContextWrapper(context=context)


def _items_to_inputs(items: list[RunItem]) -> list[TResponseInputItem]:
    """Convert generated RunItems back into model-input items (skipping unconvertible)."""
    out: list[TResponseInputItem] = []
    for item in items:
        if getattr(item, "type", None) == "tool_approval_item":
            continue
        try:
            converted = item.to_input_item()
        except Exception:
            continue
        if isinstance(converted, dict):
            out.append(converted)
    return out


_ITEM_TYPE_TO_STREAM_NAME = {
    "message_output_item": "message_output_created",
    "tool_call_item": "tool_called",
    "tool_call_output_item": "tool_output",
    "handoff_call_item": "handoff_requested",
    "handoff_output_item": "handoff_occurred",
    "reasoning_item": "reasoning_item_created",
    "mcp_approval_request_item": "mcp_approval_requested",
    "mcp_approval_response_item": "mcp_approval_response",
    "mcp_list_tools_item": "mcp_list_tools",
    "tool_search_call_item": "tool_search_called",
    "tool_search_output_item": "tool_search_output_created",
}


def _event_name_for_item(item_type: str) -> str:
    return _ITEM_TYPE_TO_STREAM_NAME.get(item_type, item_type)


__all__ = ["Runner"]