"""Run grouping — the stable ID hierarchy used for prompt-cache / tracing grouping."""
from __future__ import annotations

import hashlib
from typing import Any, Literal
from uuid import uuid4

from ..memory.session import Session

RunGroupingKind = Literal["conversation", "session", "group", "run"]
RunGrouping = tuple[RunGroupingKind, str]


def resolve_run_grouping(
    *,
    conversation_id: str | None,
    session: Session | None,
    group_id: str | None,
) -> RunGrouping:
    """Return the most stable id available, in priority order: conversation > session > group > run."""
    if conversation_id and conversation_id.strip():
        return ("conversation", conversation_id.strip())
    if session is not None:
        sid = getattr(session, "session_id", None)
        if isinstance(sid, str) and sid.strip():
            return ("session", sid.strip())
    if group_id and group_id.strip():
        return ("group", group_id.strip())
    return ("run", uuid4().hex)


def resolve_run_grouping_id(**kwargs: object) -> str:
    kind, value = resolve_run_grouping(**kwargs)  # type: ignore[arg-type]
    return f"run-{value}" if kind == "run" else value


def generate_prompt_cache_key(
    *,
    system_instructions: str | None,
    model_input: list[dict[str, Any]],
    model_name: str,
    tools: list[str] | None = None,
) -> str:
    """Generate a cache key for prompt caching.
    
    v0.2: Hierarchical cache key generation for prompt caching.
    """
    # Create a normalized representation of the prompt
    cache_data = {
        "model": model_name,
        "system": system_instructions or "",
        "messages": model_input,
        "tools": tools or [],
    }
    
    # Convert to JSON string with consistent ordering
    import json
    cache_json = json.dumps(cache_data, sort_keys=True, separators=(',', ':'))
    
    # Generate hash
    cache_hash = hashlib.sha256(cache_json.encode('utf-8')).hexdigest()
    
    return cache_hash


def get_cache_key_hierarchy(
    *,
    conversation_id: str | None = None,
    session_id: str | None = None,
    group_id: str | None = None,
    run_id: str | None = None,
) -> list[str]:
    """Get cache key hierarchy from most specific to least specific."""
    hierarchy = []
    
    # Most specific: run-specific cache
    if run_id:
        hierarchy.append(f"run:{run_id}")
    
    # Group-level cache
    if group_id:
        hierarchy.append(f"group:{group_id}")
    
    # Session-level cache
    if session_id:
        hierarchy.append(f"session:{session_id}")
    
    # Conversation-level cache
    if conversation_id:
        hierarchy.append(f"conversation:{conversation_id}")
    
    # Global cache
    hierarchy.append("global")
    
    return hierarchy


def select_best_cache_key(
    *,
    prompt_cache_key: str,
    hierarchy: list[str],
    existing_keys: list[str],
) -> str | None:
    """Select the best cache key from the hierarchy.
    
    Returns the most specific cache key that exists in the existing keys.
    """
    # Check hierarchy from most specific to least specific
    for level in hierarchy:
        candidate_key = f"{level}:{prompt_cache_key}"
        if candidate_key in existing_keys:
            return candidate_key
    
    return None


def get_prompt_cache_key_with_context(
    *,
    system_instructions: str | None,
    model_input: list[dict[str, Any]],
    model_name: str,
    tools: list[str] | None = None,
    conversation_id: str | None = None,
    session_id: str | None = None,
    group_id: str | None = None,
    run_id: str | None = None,
) -> tuple[str, list[str]]:
    """Generate prompt cache key and hierarchy for a specific context."""
    # Generate base cache key
    base_key = generate_prompt_cache_key(
        system_instructions=system_instructions,
        model_input=model_input,
        model_name=model_name,
        tools=tools,
    )
    
    # Get hierarchy
    hierarchy = get_cache_key_hierarchy(
        conversation_id=conversation_id,
        session_id=session_id,
        group_id=group_id,
        run_id=run_id,
    )
    
    return base_key, hierarchy


__all__ = [
    "RunGrouping", 
    "RunGroupingKind", 
    "resolve_run_grouping", 
    "resolve_run_grouping_id",
    "generate_prompt_cache_key",
    "get_cache_key_hierarchy",
    "select_best_cache_key",
    "get_prompt_cache_key_with_context",
]