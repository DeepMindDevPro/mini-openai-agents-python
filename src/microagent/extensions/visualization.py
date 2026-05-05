"""Optional graph visualization for `Agent` topologies.

Requires the optional `graphviz` package. Build a DOT-language string showing the
agent ↔ tool ↔ handoff topology starting at `agent`.

    from microagent.extensions.visualization import draw_graph

    print(draw_graph(my_agent))  # → Graphviz DOT source

If `graphviz` is installed, you can also render to PNG / SVG via the package's `Source`.
"""
from __future__ import annotations

from typing import Any

_DOT_HEADER = "digraph G {\n  rankdir=LR;\n  node [shape=box, style=\"rounded,filled\", fillcolor=\"#ffffff\"];\n"
_DOT_FOOTER = "}\n"


def draw_graph(agent: Any, *, max_depth: int = 5) -> str:
    """Return a DOT-language string describing the agent's topology."""
    visited: set[int] = set()
    lines: list[str] = []
    _walk(agent, visited, lines, depth=0, max_depth=max_depth)
    return _DOT_HEADER + "\n".join(f"  {line}" for line in lines) + "\n" + _DOT_FOOTER


def _node_id(value: Any, prefix: str) -> str:
    name = getattr(value, "name", repr(value))
    safe = "".join(ch if ch.isalnum() or ch in "_-" else "_" for ch in str(name))
    return f"{prefix}_{safe}_{id(value):x}"


def _walk(
    agent: Any,
    visited: set[int],
    lines: list[str],
    *,
    depth: int,
    max_depth: int,
) -> str:
    aid = _node_id(agent, "agent")
    if id(agent) in visited or depth > max_depth:
        return aid
    visited.add(id(agent))

    label = getattr(agent, "name", "Agent")
    lines.append(f'{aid} [label="🤖 {label}", fillcolor="#dce9ff"];')

    # Tools.
    for tool in getattr(agent, "tools", []) or []:
        tid = _node_id(tool, "tool")
        tool_name = getattr(tool, "name", repr(tool))
        lines.append(f'{tid} [label="🛠️ {tool_name}", fillcolor="#fff2c2"];')
        lines.append(f"{aid} -> {tid};")

    # Handoffs.
    for h in getattr(agent, "handoffs", []) or []:
        target = getattr(h, "agent", h)
        target_id = _walk(target, visited, lines, depth=depth + 1, max_depth=max_depth)
        lines.append(f'{aid} -> {target_id} [label="handoff", style=dashed];')

    return aid


def render_graph(agent: Any, *, fmt: str = "png", filename: str | None = None) -> Any:
    """Render the topology using the optional `graphviz` package."""
    try:
        import graphviz  # type: ignore
    except ImportError as exc:  # pragma: no cover
        raise ImportError(
            "render_graph requires the 'graphviz' package. Install with `pip install graphviz`."
        ) from exc
    src = graphviz.Source(draw_graph(agent), format=fmt)
    if filename:
        src.render(filename, cleanup=True)
    return src


__all__ = ["draw_graph", "render_graph"]