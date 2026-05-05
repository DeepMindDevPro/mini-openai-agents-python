"""`BaseSandboxClientOptions` — Pydantic polymorphic registry for sandbox clients.

Each sandbox backend addon defines a subclass with a unique `type` literal. We use
`__init_subclass__` to register subclasses; `from_dict` then dispatches polymorphically:

    >>> data = {"type": "unix_local", "workspace": "/tmp/foo"}
    >>> options = BaseSandboxClientOptions.from_dict(data)  # picks the right subclass

This is the same `_subclass_registry` design used by `openai-agents-python`.
"""
from __future__ import annotations

from typing import Any, ClassVar

try:
    from pydantic import BaseModel, ConfigDict, Field
except ImportError as exc:  # pragma: no cover - pydantic is a hard dep
    raise ImportError("microagent.sandbox requires pydantic>=2") from exc


class BaseSandboxClientOptions(BaseModel):
    """Base class for sandbox client option payloads.

    Subclasses set `type` to a stable string literal; the registry uses that field for
    polymorphic deserialization.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="allow")

    type: str = Field(..., description="Stable identifier for the sandbox backend.")

    # Subclass registry keyed by the value of the `type` field default.
    _subclass_registry: ClassVar[dict[str, type["BaseSandboxClientOptions"]]] = {}

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        BaseSandboxClientOptions._register_subclass(cls)

    @classmethod
    def _register_subclass(cls, subcls: type["BaseSandboxClientOptions"]) -> None:
        """Look up the literal default for `type` on `subcls` and register it."""
        type_default: str | None = None
        # `model_fields` is populated by pydantic after class creation; we run lazily.
        try:
            fields = getattr(subcls, "model_fields", None) or {}
            field = fields.get("type")
            if field is not None:
                value = getattr(field, "default", None)
                if isinstance(value, str):
                    type_default = value
        except Exception:
            type_default = None
        if type_default and type_default not in BaseSandboxClientOptions._subclass_registry:
            BaseSandboxClientOptions._subclass_registry[type_default] = subcls

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BaseSandboxClientOptions":
        """Polymorphically deserialize based on the `type` discriminator."""
        cls._ensure_registry_populated()
        type_name = data.get("type")
        target = (
            cls._subclass_registry.get(type_name)
            if isinstance(type_name, str)
            else None
        )
        return (target or cls).model_validate(data)

    @classmethod
    def list_registered_types(cls) -> list[str]:
        cls._ensure_registry_populated()
        return sorted(cls._subclass_registry)

    @classmethod
    def _ensure_registry_populated(cls) -> None:
        """Re-walk subclasses and (re)register them. Cheap enough on demand."""
        for sub in BaseSandboxClientOptions.__subclasses__():
            cls._register_subclass(sub)


# Two minimal built-in option shapes so users have something to reference. Concrete
# behavior is delegated to addon backends.


class UnixLocalSandboxClientOptions(BaseSandboxClientOptions):
    """Local-host process sandbox (no isolation; for tests / hello-world)."""

    type: str = "unix_local"
    workspace: str = "/tmp/microagent-sandbox"
    user: str | None = None
    timeout_seconds: float = 30.0


class DockerSandboxClientOptions(BaseSandboxClientOptions):
    """Docker-backed sandbox; requires `microagent-sandbox-docker` addon at runtime."""

    type: str = "docker"
    image: str = "python:3.12-slim"
    workspace: str = "/workspace"
    timeout_seconds: float = 60.0
    cpu_limit: float | None = None
    memory_limit_mb: int | None = None
    network: str = "none"


__all__ = [
    "BaseSandboxClientOptions",
    "DockerSandboxClientOptions",
    "UnixLocalSandboxClientOptions",
]