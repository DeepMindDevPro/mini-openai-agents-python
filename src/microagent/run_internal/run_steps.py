"""Control-flow datatypes for the run loop.

- `NextStepFinalOutput` — the run is done; carry the final output.
- `NextStepHandoff`     — switch to the target agent.
- `NextStepRunAgain`    — feed tool outputs back into the same agent.
- `NextStepInterruption` — pause the run for HITL approvals.
- `ProcessedResponse`   — the intermediate "we parsed the model's turn" struct.
- `SingleStepResult`    — outcome of one run_single_turn call.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..agent import Agent
    from ..items import ModelResponse, RunItem, ToolApprovalItem


@dataclass
class ProcessedResponse:
    new_items: list[RunItem] = field(default_factory=list)
    handoff_target: Agent[Any] | None = None
    final_output: Any = None
    has_tool_calls: bool = False
    has_pending_approvals: bool = False
    pending_approvals: list[ToolApprovalItem] = field(default_factory=list)


@dataclass
class NextStepRunAgain:
    pass


@dataclass
class NextStepFinalOutput:
    final_output: Any


@dataclass
class NextStepHandoff:
    target: Agent[Any]


@dataclass
class NextStepInterruption:
    interruptions: list[ToolApprovalItem]


NextStep = NextStepRunAgain | NextStepFinalOutput | NextStepHandoff | NextStepInterruption


@dataclass
class SingleStepResult:
    new_items: list[RunItem] = field(default_factory=list)
    model_response: ModelResponse | None = None
    next_step: NextStep = field(default_factory=NextStepRunAgain)


class QueueCompleteSentinel:
    pass


__all__ = [
    "NextStep",
    "NextStepFinalOutput",
    "NextStepHandoff",
    "NextStepInterruption",
    "NextStepRunAgain",
    "ProcessedResponse",
    "QueueCompleteSentinel",
    "SingleStepResult",
]