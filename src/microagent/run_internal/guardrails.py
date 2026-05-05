"""Guardrail execution helpers."""
from __future__ import annotations

from typing import Any

from ..agent import Agent
from ..guardrail import (
    InputGuardrail,
    InputGuardrailResult,
    OutputGuardrail,
    OutputGuardrailResult,
)
from ..items import TResponseInputItem
from ..run_context import RunContextWrapper, TContext


async def run_single_input_guardrail(
    agent: Agent[Any],
    guardrail: InputGuardrail[TContext],
    input: str | list[TResponseInputItem],
    context: RunContextWrapper[TContext],
) -> InputGuardrailResult:
    return await guardrail.run(agent, input, context)


async def run_single_output_guardrail(
    guardrail: OutputGuardrail[TContext],
    agent: Agent[Any],
    agent_output: Any,
    context: RunContextWrapper[TContext],
) -> OutputGuardrailResult:
    return await guardrail.run(context, agent, agent_output)


async def run_input_guardrails(
    agent: Agent[Any],
    guardrails: list[InputGuardrail[TContext]],
    input: str | list[TResponseInputItem],
    context: RunContextWrapper[TContext],
) -> list[InputGuardrailResult]:
    results: list[InputGuardrailResult] = []
    for g in guardrails:
        result = await run_single_input_guardrail(agent, g, input, context)
        results.append(result)
        if result.output.tripwire_triggered:
            from ..exceptions import InputGuardrailTripwireTriggered

            raise InputGuardrailTripwireTriggered(result)
    return results


async def run_output_guardrails(
    guardrails: list[OutputGuardrail[TContext]],
    agent: Agent[Any],
    agent_output: Any,
    context: RunContextWrapper[TContext],
) -> list[OutputGuardrailResult]:
    results: list[OutputGuardrailResult] = []
    for g in guardrails:
        result = await run_single_output_guardrail(g, agent, agent_output, context)
        results.append(result)
        if result.output.tripwire_triggered:
            from ..exceptions import OutputGuardrailTripwireTriggered

            raise OutputGuardrailTripwireTriggered(result)
    return results


__all__ = [
    "run_input_guardrails",
    "run_output_guardrails",
    "run_single_input_guardrail",
    "run_single_output_guardrail",
]