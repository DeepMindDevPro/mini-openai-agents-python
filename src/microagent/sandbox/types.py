"""Shared sandbox types (users, files, exec results, port endpoints)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


FileMode = Literal["r", "rb", "w", "wb", "a", "ab"]


@dataclass(frozen=True)
class User:
    """Sandbox user identity."""

    uid: int = 0
    name: str = "root"


@dataclass(frozen=True)
class Group:
    gid: int = 0
    name: str = "root"


@dataclass(frozen=True)
class Permissions:
    """POSIX-style permission bits (octal; e.g. 0o755)."""

    mode: int = 0o644
    user: User | None = None
    group: Group | None = None


@dataclass
class ExecResult:
    """Result of a single shell / command execution inside the sandbox."""

    exit_code: int
    stdout: str = ""
    stderr: str = ""
    duration_seconds: float | None = None
    timed_out: bool = False

    @property
    def succeeded(self) -> bool:
        return self.exit_code == 0 and not self.timed_out


@dataclass(frozen=True)
class ExposedPortEndpoint:
    """Public endpoint surfacing a sandbox-internal port."""

    internal_port: int
    public_url: str
    protocol: Literal["http", "https", "tcp", "udp"] = "https"


class SandboxError(RuntimeError):
    """Base class for sandbox-side failures (transport, timeout, workspace, …)."""


__all__ = [
    "ExecResult",
    "ExposedPortEndpoint",
    "FileMode",
    "Group",
    "Permissions",
    "SandboxError",
    "User",
]