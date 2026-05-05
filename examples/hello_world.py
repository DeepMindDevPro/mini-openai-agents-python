"""Hello-world example using FakeModel (no API key required).

Run with:

    python examples/hello_world.py
"""
from __future__ import annotations

import asyncio

from src.microagent import Agent, FakeModel, FakeModelTurn, Runner, function_tool


@function_tool
def get_weather(city: str) -> str:
    """Get the weather for a given city."""
    return f"The weather in {city} is sunny."


async def main() -> None:
    model = FakeModel(
        [
            FakeModelTurn(tool_calls=[("get_weather", {"city": "Tokyo"})]),
            FakeModelTurn(final_output="It is sunny in Tokyo."),
        ]
    )
    agent = Agent(
        name="Weather Assistant",
        instructions="Answer weather questions using the provided tool.",
        tools=[get_weather],
        model=model,
    )
    result = await Runner.run(agent, "What is the weather in Tokyo?")
    print("Final output:", result.final_output)
    print("Total tool calls:", sum(1 for i in result.new_items if i.type == "tool_call_item"))


if __name__ == "__main__":
    asyncio.run(main())