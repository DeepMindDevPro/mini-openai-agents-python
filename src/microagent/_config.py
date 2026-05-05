"""Process-wide default configuration for the OpenAI addon.

Mirrors the upstream `openai-agents-python` config surface: a small set of mutable
globals that the OpenAI provider reads when no explicit override is passed. Keeping
these as setters means tests / multi-tenant apps can rebind without touching env vars.

Nothing here imports `openai` directly — that addon reads via `get_default_*` accessors.
"""
from __future__ import annotations

from typing import Any, Literal


# ---- internal storage --------------------------------------------------------

_default_openai_key: str | None = None
_use_default_key_for_tracing: bool = True

_default_openai_client: Any | None = None
_use_default_client_for_tracing: bool = True

_default_openai_api: Literal["chat_completions", "responses"] = "responses"
_default_openai_responses_transport: Literal["http", "websocket"] = "http"
_default_openai_harness_id: str | None = None
_default_openai_agent_registration: Any | None = None


# ---- setters (public via top-level package) ----------------------------------


def set_default_openai_key(key: str, use_for_tracing: bool = True) -> None:
    global _default_openai_key, _use_default_key_for_tracing
    _default_openai_key = key
    _use_default_key_for_tracing = use_for_tracing


def set_default_openai_client(client: Any, use_for_tracing: bool = True) -> None:
    global _default_openai_client, _use_default_client_for_tracing
    _default_openai_client = client
    _use_default_client_for_tracing = use_for_tracing


def set_default_openai_api(api: Literal["chat_completions", "responses"]) -> None:
    global _default_openai_api
    _default_openai_api = api


def set_default_openai_responses_transport(
    transport: Literal["http", "websocket"],
) -> None:
    global _default_openai_responses_transport
    _default_openai_responses_transport = transport


def set_default_openai_harness(harness_id: str | None) -> None:
    global _default_openai_harness_id
    _default_openai_harness_id = harness_id


def set_default_openai_agent_registration(config: Any | None) -> None:
    global _default_openai_agent_registration
    _default_openai_agent_registration = config


# ---- accessors ---------------------------------------------------------------


def get_default_openai_key() -> str | None:
    return _default_openai_key


def get_default_openai_client() -> Any | None:
    return _default_openai_client


def get_default_openai_api() -> Literal["chat_completions", "responses"]:
    return _default_openai_api


def get_default_openai_responses_transport() -> Literal["http", "websocket"]:
    return _default_openai_responses_transport


def get_default_openai_harness() -> str | None:
    return _default_openai_harness_id


def get_default_openai_agent_registration() -> Any | None:
    return _default_openai_agent_registration


def use_default_key_for_tracing() -> bool:
    return _use_default_key_for_tracing


def use_default_client_for_tracing() -> bool:
    return _use_default_client_for_tracing


__all__ = [
    "get_default_openai_agent_registration",
    "get_default_openai_api",
    "get_default_openai_client",
    "get_default_openai_harness",
    "get_default_openai_key",
    "get_default_openai_responses_transport",
    "set_default_openai_agent_registration",
    "set_default_openai_api",
    "set_default_openai_client",
    "set_default_openai_harness",
    "set_default_openai_key",
    "set_default_openai_responses_transport",
    "use_default_client_for_tracing",
    "use_default_key_for_tracing",
]