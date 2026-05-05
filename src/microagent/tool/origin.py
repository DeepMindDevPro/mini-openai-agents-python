"""ToolOrigin — serializable metadata describing where a function-tool call came from.

Carried on RunItems so that RunState snapshots can faithfully reconstruct tool identity after a
resume (this is the schema-1.9 invariant from the upstream SDK).
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
from typing import Any


class ToolOriginType(str, Enum):
    FUNCTION = "function"
    MCP = "mcp"
    AGENT_AS_TOOL = "agent_as_tool"


@dataclass(frozen=True)
class ToolOrigin:
    type: ToolOriginType
    mcp_server_name: str | None = None
    agent_name: str | None = None
    agent_tool_name: str | None = None

    def to_json_dict(self) -> dict[str, str]:
        out: dict[str, str] = {"type": self.type.value}
        if self.mcp_server_name:
            out["mcp_server_name"] = self.mcp_server_name
        if self.agent_name:
            out["agent_name"] = self.agent_name
        if self.agent_tool_name:
            out["agent_tool_name"] = self.agent_tool_name
        return out

    @classmethod
    def from_json_dict(cls, data: Any) -> ToolOrigin | None:
        if not isinstance(data, Mapping):
            return None
        raw = data.get("type")
        if not isinstance(raw, str):
            return None
        try:
            kind = ToolOriginType(raw)
        except ValueError:
            return None

        def _opt(key: str) -> str | None:
            value = data.get(key)
            return value if isinstance(value, str) else None

        return cls(
            type=kind,
            mcp_server_name=_opt("mcp_server_name"),
            agent_name=_opt("agent_name"),
            agent_tool_name=_opt("agent_tool_name"),
        )