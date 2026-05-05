"""Composable `Capability` framework.

Each capability is a plug-in that can:
- Contribute tools (`tools()`).
- Mutate the manifest before the session starts (`process_manifest`).
- Append deterministic instructions to the system prompt (`instructions`).
- Inject sampling parameters (`sampling_params`).
- Rewrite the model input context (`process_context`).

Built-in capability **types** in core (registered names only — the heavy
implementations live in `microagent-sandbox-*` addons):

- `filesystem` — read/write files inside the sandbox workspace
- `shell`      — run shell commands
- `memory`     — long-task memory consolidation (phase one + phase two)
- `skills`     — durable skill scripts
- `compaction` — conversation compaction worker
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, ClassVar

from ..items import TResponseInputItem
from ..tool import Tool
from .manifest import Manifest


@dataclass
class Capability:
    """Base class for all capabilities. Subclasses set `type`."""

    type: str = "base"
    metadata: dict[str, Any] = field(default_factory=dict)

    # Filled in at session bind-time by the runner.
    session: Any | None = None
    run_as: Any | None = None

    # Class-level registry: subclass `type` → subclass.
    _registry: ClassVar[dict[str, type["Capability"]]] = {}

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        # Register subclasses keyed by their declared `type` field default.
        type_name = getattr(cls, "type", None)
        if isinstance(type_name, str) and type_name and type_name != "base":
            Capability._registry[type_name] = cls

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Capability":
        """Polymorphic deserialization keyed by the `type` field."""
        type_name = data.get("type")
        target = cls._registry.get(type_name) if isinstance(type_name, str) else None
        target_cls = target or cls
        # Best-effort attribute copy; subclasses override for richer construction.
        instance = target_cls()
        for k, v in data.items():
            if hasattr(instance, k):
                try:
                    setattr(instance, k, v)
                except Exception:
                    continue
        return instance

    def bind(self, session: Any) -> None:
        """Bind a live session to this capability."""
        self.session = session

    def required_capability_types(self) -> set[str]:
        """Other capability types that must be present alongside this one."""
        return set()

    def tools(self) -> list[Tool]:
        """Tools this capability contributes to the agent."""
        return []

    def process_manifest(self, manifest: Manifest) -> Manifest:
        return manifest

    async def instructions(self, manifest: Manifest) -> str | None:
        """Optional system-prompt fragment appended at session start."""
        return None

    def sampling_params(self, sampling_params: dict[str, Any]) -> dict[str, Any]:
        """Extra kwargs to inject into model requests on this run."""
        return {}

    def process_context(
        self, context: list[TResponseInputItem]
    ) -> list[TResponseInputItem]:
        """Rewrite the model input list before sampling (e.g. compaction)."""
        return context


class CapabilityRegistry:
    """Light wrapper around the global capability subclass registry."""

    @staticmethod
    def register(type_name: str, capability_cls: type[Capability]) -> None:
        Capability._registry[type_name] = capability_cls

    @staticmethod
    def resolve(type_name: str) -> type[Capability] | None:
        return Capability._registry.get(type_name)

    @staticmethod
    def all_types() -> list[str]:
        return sorted(Capability._registry)


__all__ = ["Capability", "CapabilityRegistry"]