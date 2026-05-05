"""AgentToolUseTracker — remembers which tools each agent has already called in a run.

Used by the Runner to decide whether `reset_tool_choice` should fire after a tool executes,
and to give addon models a hint about which tools were already invoked (so they can avoid
redundant suggestions).
"""
from __future__ import annotations

from typing import Any

from ..items import RunItem, ToolCallItem


class AgentToolUseTracker:
    """Track tool invocations per agent.

    - `agent_map`: name-keyed, serializable snapshot (resume-friendly).
    - `agent_to_tools`: identity-keyed, runtime state (survives duplicate-name agents).
    """

    def __init__(self) -> None:
        self.agent_map: dict[str, set[str]] = {}
        self.agent_to_tools: list[tuple[Any, list[str]]] = []

    def add_tool_use(self, agent: Any, tool_names: list[str]) -> None:
        if not tool_names:
            return
        agent_name = getattr(agent, "name", agent.__class__.__name__)
        self.agent_map.setdefault(agent_name, set()).update(tool_names)

        for existing_agent, names in self.agent_to_tools:
            if existing_agent is agent:
                names.extend(tool_names)
                return
        self.agent_to_tools.append((agent, list(tool_names)))

    def record_run_items(self, agent: Any, items: list[RunItem]) -> None:
        """Pull tool names out of ToolCallItems and record them."""
        names: list[str] = []
        for item in items:
            if isinstance(item, ToolCallItem):
                raw = item.raw_item
                if isinstance(raw, dict):
                    n = raw.get("name")
                    if isinstance(n, str) and n:
                        names.append(n)
        self.add_tool_use(agent, names)

    def has_used_tools(self, agent: Any) -> bool:
        for existing_agent, names in self.agent_to_tools:
            if existing_agent is agent and names:
                return True
        return False

    def tools_used(self, agent: Any) -> list[str]:
        for existing_agent, names in self.agent_to_tools:
            if existing_agent is agent:
                return list(names)
        agent_name = getattr(agent, "name", agent.__class__.__name__)
        return sorted(self.agent_map.get(agent_name, set()))

    def as_serializable(self) -> dict[str, list[str]]:
        if self.agent_map:
            return {name: sorted(names) for name, names in self.agent_map.items()}
        snapshot: dict[str, set[str]] = {}
        for agent, names in self.agent_to_tools:
            agent_name = getattr(agent, "name", agent.__class__.__name__)
            snapshot.setdefault(agent_name, set()).update(names)
        return {name: sorted(n) for name, n in snapshot.items()}

    @classmethod
    def from_serializable(cls, data: dict[str, list[str]]) -> "AgentToolUseTracker":
        tracker = cls()
        tracker.agent_map = {name: set(tools) for name, tools in (data or {}).items()}
        return tracker


def maybe_reset_tool_choice(
    agent: Any,
    tracker: AgentToolUseTracker,
    model_settings: Any,
) -> Any:
    """If the agent has `reset_tool_choice=True` and has already used tools, unset tool_choice."""
    if getattr(agent, "reset_tool_choice", False) and tracker.has_used_tools(agent):
        if model_settings is not None and getattr(model_settings, "tool_choice", None) is not None:
            from dataclasses import replace

            try:
                return replace(model_settings, tool_choice=None)
            except Exception:
                return model_settings
    return model_settings


__all__ = ["AgentToolUseTracker", "maybe_reset_tool_choice"]