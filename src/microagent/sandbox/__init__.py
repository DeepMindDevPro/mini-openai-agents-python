"""Sandbox abstractions — declarative `Manifest` + composable `Capability` framework.

Core ships the protocols and the registry machinery so addons can plug in concrete
sandbox backends (`microagent-sandbox`: local/docker; cloud addons: blaxel / cloudflare
/ daytona / e2b / modal / runloop / vercel). The core has **zero** dependency on
subprocess / docker / any cloud SDK.
"""
from __future__ import annotations

from .capability import Capability, CapabilityRegistry
from .manifest import Manifest, MountEntry
from .options import BaseSandboxClientOptions
from .session import BaseSandboxSession, SandboxResult
from .types import ExecResult, ExposedPortEndpoint, FileMode, Group, Permissions, User

__all__ = [
    "BaseSandboxClientOptions",
    "BaseSandboxSession",
    "Capability",
    "CapabilityRegistry",
    "ExecResult",
    "ExposedPortEndpoint",
    "FileMode",
    "Group",
    "Manifest",
    "MountEntry",
    "Permissions",
    "SandboxResult",
    "User",
]