"""`BaseSandboxSession` — abstract async context manager for a live sandbox run.

Addons subclass this to back the session with a concrete runtime (local subprocess,
Docker, E2B, Cloudflare, Modal, …). The abstract surface is intentionally narrow so
capability plug-ins can compose without caring about the backend.
"""
from __future__ import annotations

import abc
from dataclasses import dataclass, field
from typing import Any

from .manifest import Manifest
from .types import ExecResult, User


@dataclass
class SandboxResult:
    """Outcome of a completed sandbox session (exit, logs, artifacts)."""

    exit_code: int = 0
    stdout: str = ""
    stderr: str = ""
    artifacts: dict[str, Any] = field(default_factory=dict)


class BaseSandboxSession(abc.ABC):
    """Async-context-manager contract for one sandbox session.

    A session is opened with a `Manifest`, used via capability-contributed tools, and
    closed (or `__aexit__`-unwound) once the agent run is done. Backends may implement
    persistence or snapshotting by subclassing.
    """

    manifest: Manifest

    def __init__(self, manifest: Manifest) -> None:
        self.manifest = manifest

    # ---- lifecycle ----

    async def __aenter__(self) -> "BaseSandboxSession":
        await self.start()
        return self

    async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        await self.close()

    @abc.abstractmethod
    async def start(self) -> None: ...

    @abc.abstractmethod
    async def close(self) -> None: ...

    # ---- primitive operations ----

    @abc.abstractmethod
    async def exec(
        self,
        command: str | list[str],
        *,
        user: User | None = None,
        timeout: float | None = None,
        env: dict[str, str] | None = None,
        workdir: str | None = None,
    ) -> ExecResult: ...

    @abc.abstractmethod
    async def read_file(self, path: str) -> bytes: ...

    @abc.abstractmethod
    async def write_file(self, path: str, content: bytes | str) -> None: ...

    # ---- optional introspection ----

    async def list_files(self, path: str) -> list[str]:
        """Default implementation uses `exec`. Backends may override for efficiency."""
        result = await self.exec(["ls", "-1", path])
        if not result.succeeded:
            return []
        return [line for line in result.stdout.splitlines() if line]


__all__ = ["BaseSandboxSession", "SandboxResult"]