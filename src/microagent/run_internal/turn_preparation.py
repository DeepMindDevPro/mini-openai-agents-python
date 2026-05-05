"""Helpers that prepare "what the model sees" before each turn.

- `validate_run_hooks(hooks)` — enforce the `RunHooks` type.
- `get_all_tools(agent, ctx)` — resolve enabled tools.
- `get_handoffs(agent, ctx)`  — resolve enabled handoffs.
- `get_output_schema(agent)`  — build the output schema for structured output.
- `get_model(agent, run_config)` — pick the concrete `Model`.
- `maybe_filter_model_input(...)` — optional `call_model_input_filter` pass.
"""
from __future__ import annotations

import inspect
from typing import Any

from ..agent import Agent
from ..agent_output import AgentOutputSchema, AgentOutputSchemaBase
from ..exceptions import UserError
from ..handoffs import Handoff, handoff
from ..items import TResponseInputItem
from ..lifecycle import AgentHooksBase, RunHooks, RunHooksBase
from ..models.interface import Model
from ..run_config import CallModelData, ModelInputData, RunConfig
from ..run_context import RunContextWrapper, TContext
from ..tool import Tool


def validate_run_hooks(hooks: Any) -> RunHooks[Any]:
    if hooks is None:
        return RunHooks[Any]()
    if isinstance(hooks, AgentHooksBase):
        raise TypeError(
            "Run hooks must be an instance of RunHooks. Received agent-scoped hooks. "
            "Attach AgentHooks to an Agent via Agent(..., hooks=...)."
        )
    if not isinstance(hooks, RunHooksBase):
        raise TypeError(f"Run hooks must be instances of RunHooks. Got {type(hooks).__name__}.")
    return hooks


async def get_all_tools(
    agent: Agent[Any], context_wrapper: RunContextWrapper[Any]
) -> list[Tool]:
    return await agent.get_all_tools(context_wrapper)


async def get_handoffs(
    agent: Agent[Any], context_wrapper: RunContextWrapper[Any]
) -> list[Handoff]:
    handoffs: list[Handoff] = []
    for item in agent.handoffs:
        if isinstance(item, Handoff):
            handoffs.append(item)
        elif isinstance(item, Agent):
            handoffs.append(handoff(item))

    async def _is_enabled(h: Handoff) -> bool:
        attr = h.is_enabled
        if isinstance(attr, bool):
            return attr
        val = attr(context_wrapper, agent)
        if inspect.isawaitable(val):
            val = await val
        return bool(val)

    enabled: list[Handoff] = []
    for h in handoffs:
        if await _is_enabled(h):
            enabled.append(h)
    return enabled


def get_output_schema(agent: Agent[Any]) -> AgentOutputSchemaBase | None:
    if agent.output_type is None or agent.output_type is str:
        return None
    if isinstance(agent.output_type, AgentOutputSchemaBase):
        return agent.output_type
    return AgentOutputSchema(agent.output_type)


def get_model(agent: Agent[Any], run_config: RunConfig | None) -> Model | None:
    """Resolve the Model for a turn.

    Priority: run_config.model (Model instance) > agent.model (Model instance) >
    run_config.model_provider(name) > raise UserError asking the user to supply one.

    Prefix-routed provider picking (`"openai/gpt-4o"`, `"claude/opus"`) is delegated to the
    optional `MultiProvider` addon; core only understands the plain `ModelProvider.get_model`
    contract.
    """
    if run_config is not None and isinstance(run_config.model, Model):
        return run_config.model
    if isinstance(agent.model, Model):
        return agent.model
    if run_config is not None and run_config.model_provider is not None:
        name = run_config.model if isinstance(run_config.model, str) else None
        if name is None and isinstance(agent.model, str):
            name = agent.model
        return run_config.model_provider.get_model(name)
    return None


async def maybe_filter_model_input(
    *,
    agent: Agent[TContext],
    run_config: RunConfig,
    context_wrapper: RunContextWrapper[TContext],
    input_items: list[TResponseInputItem],
    system_instructions: str | None,
) -> ModelInputData:
    if run_config.call_model_input_filter is None:
        return ModelInputData(input=list(input_items), instructions=system_instructions)
    payload = CallModelData(
        model_data=ModelInputData(
            input=list(input_items), instructions=system_instructions
        ),
        agent=agent,
        context=context_wrapper.context,
    )
    updated = run_config.call_model_input_filter(payload)
    if inspect.isawaitable(updated):
        updated = await updated
    if not isinstance(updated, ModelInputData):
        raise UserError("call_model_input_filter must return a ModelInputData instance")
    return updated


__all__ = [
    "get_all_tools",
    "get_handoffs",
    "get_model",
    "get_output_schema",
    "maybe_filter_model_input",
    "validate_run_hooks",
]