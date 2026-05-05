"""Declarative `Manifest` — the data passed into a sandbox session at start.

A manifest describes **what the sandbox should contain**: mounts (files / directories
brought in from S3 / GCS / local paths), environment variables, and the list of
capabilities enabled for this run. It is plain data (`dataclass`) so it round-trips
cleanly through RunState.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from .types import Permissions


@dataclass
class MountEntry:
    """One file or directory to materialize inside the sandbox.

    `source` is provider-specific (e.g. an S3 URL handled by the mount provider addon,
    or a local path handled by the unix-local sandbox backend).
    """

    source: str
    target: str
    kind: Literal["file", "directory"] = "file"
    permissions: Permissions | None = None
    provider: str | None = None  # e.g. "s3", "gcs", "local"; None means auto-detect
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Manifest:
    """Full description of a sandbox session's declarative inputs."""

    mounts: list[MountEntry] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)
    workdir: str | None = None
    capabilities: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def with_mount(self, entry: MountEntry) -> "Manifest":
        """Return a new Manifest with `entry` appended (immutability helper)."""
        new = Manifest(
            mounts=[*self.mounts, entry],
            env=dict(self.env),
            workdir=self.workdir,
            capabilities=list(self.capabilities),
            metadata=dict(self.metadata),
        )
        return new

    def with_env(self, **kwargs: str) -> "Manifest":
        return Manifest(
            mounts=list(self.mounts),
            env={**self.env, **kwargs},
            workdir=self.workdir,
            capabilities=list(self.capabilities),
            metadata=dict(self.metadata),
        )


__all__ = ["Manifest", "MountEntry"]