"""Pretty printers for the user-facing result objects.

Concise one-line repr; exporter addons can override via `set_trace_provider` to emit
richer diagnostics.
"""
from __future__ import annotations

from typing import Any


def pretty_print_result(result: Any) -> str:
    final = getattr(result, "final_output", None)
    last_agent = getattr(result, "last_agent", None)
    last_agent_name = getattr(last_agent, "name", "<unknown>") if last_agent is not None else "-"
    return f"RunResult(last_agent={last_agent_name}, final_output={final!r})"


def pretty_print_run_result_streaming(result: Any) -> str:
    return f"RunResultStreaming(is_complete={getattr(result, 'is_complete', False)})"


def pretty_print_run_error_details(details: Any) -> str:
    last_agent = getattr(details, "last_agent", None)
    last_agent_name = getattr(last_agent, "name", "<unknown>") if last_agent is not None else "-"
    new_items = getattr(details, "new_items", []) or []
    return (
        f"RunErrorDetails(last_agent={last_agent_name}, "
        f"new_items={len(new_items)}, raw_responses={len(getattr(details, 'raw_responses', []) or [])})"
    )