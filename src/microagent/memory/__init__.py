"""Session memory — protocol + in-memory default.

`Session` is a `@runtime_checkable Protocol` with 4 async methods. Third parties integrate
by implementing the Protocol; they do not need to subclass `SessionABC`.

Built-ins (v0.1):
- `InMemorySession` — single-process dict-backed session (default).

Addons (v0.2+):
- `microagent-session-sqlite` — file-backed persistent session (`SQLiteSession`).
- `microagent-session-redis`  — distributed session.
- `microagent-session-sqlalchemy` — SQL backend.

Capability detection: addon sessions may opt-in to features (e.g. OpenAI Responses
conversation compaction) by implementing marker methods or by declaring a
`supports_*` class attribute. `is_openai_responses_compaction_aware_session`
duck-types that contract so the runner can branch without importing addon code.
"""
from __future__ import annotations

from typing import Any, TypeGuard

from .in_memory_session import InMemorySession
from .session import Session, SessionABC, is_runtime_session
from .session_settings import SessionSettings, resolve_session_limit
from .util import SessionInputCallback


def is_openai_responses_compaction_aware_session(
    value: Any,
) -> TypeGuard[Session]:
    """Duck-typing check: does the session implement the compaction-aware contract?

    An addon session that participates in OpenAI Responses conversation compaction exposes
    either `supports_openai_responses_compaction = True` or an `openai_responses_compaction`
    attribute. Core only branches on the check; the actual behavior lives in the addon.
    """
    if not is_runtime_session(value):
        return False
    flag = getattr(value, "supports_openai_responses_compaction", None)
    if isinstance(flag, bool) and flag:
        return True
    return hasattr(value, "openai_responses_compaction")


__all__ = [
    "InMemorySession",
    "Session",
    "SessionABC",
    "SessionInputCallback",
    "SessionSettings",
    "is_openai_responses_compaction_aware_session",
    "is_runtime_session",
    "resolve_session_limit",
]