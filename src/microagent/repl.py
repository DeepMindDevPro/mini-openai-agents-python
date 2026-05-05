"""Simple REPL loop for quick CLI experimentation.

    from microagent import Agent, run_demo_loop
    from microagent.models import FakeModel, FakeModelTurn

    agent = Agent(name="Assistant", instructions="Be brief.",
                   model=FakeModel([FakeModelTurn(final_output="hi")]))
    asyncio.run(run_demo_loop(agent))

Type `exit` or `quit` to leave.
"""
from __future__ import annotations

from typing import Any

from .agent import Agent
from .items import TResponseInputItem
from .run import Runner


async def run_demo_loop(
    agent: Agent[Any],
    *,
    max_turns: int = 10,
) -> None:
    input_items: list[TResponseInputItem] = []
    while True:
        try:
            user_input = input(" > ")
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if user_input.strip().lower() in {"exit", "quit"}:
            break
        if not user_input:
            continue
        input_items.append({"role": "user", "content": user_input})
        result = await Runner.run(agent, input=input_items, max_turns=max_turns)
        print(result.final_output)


__all__ = ["run_demo_loop"]