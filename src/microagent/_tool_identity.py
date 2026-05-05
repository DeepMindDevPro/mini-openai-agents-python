"""Tool identity helpers (namespace + approval key resolution).

In upstream `openai-agents`, tool lookup keys are a tagged union type-alias:

    FunctionToolLookupKey = Bare | Namespaced | DeferredTopLevel
    NamedToolLookupKey = FunctionToolLookupKey | str

We keep the same structural model but expose simple helpers. Tool identities must be stable
across RunState snapshots so interrupted approvals can be matched on resume even if agents are
rebuilt with new Python objects. MCP namespace disambiguation and (de)serialization helpers
live here so the RunState schema can use them without importing from addon packages.
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Literal

BareFunctionToolLookupKey = tuple[Literal["bare"], str]
NamespacedFunctionToolLookupKey = tuple[Literal["namespaced"], str, str]
DeferredTopLevelFunctionToolLookupKey = tuple[Literal["deferred_top_level"], str]
FunctionToolLookupKey = (
    BareFunctionToolLookupKey
    | NamespacedFunctionToolLookupKey
    | DeferredTopLevelFunctionToolLookupKey
)
NamedToolLookupKey = FunctionToolLookupKey | str


def get_mapping_or_attr(value: Any, key: str) -> Any:
    if isinstance(value, Mapping):
        return value.get(key)
    return getattr(value, key, None)


def tool_qualified_name(name: str | None, namespace: str | None = None) -> str | None:
    """Return `namespace.name` when a namespace exists, otherwise `name`."""
    if not isinstance(name, str) or not name:
        return None
    if isinstance(namespace, str) and namespace:
        return f"{namespace}.{name}"
    return name


def tool_trace_name(name: str | None, namespace: str | None = None) -> str | None:
    if is_reserved_synthetic_tool_namespace(name, namespace):
        return name
    return tool_qualified_name(name, namespace)


def is_reserved_synthetic_tool_namespace(name: str | None, namespace: str | None) -> bool:
    return (
        isinstance(name, str)
        and bool(name)
        and isinstance(namespace, str)
        and bool(namespace)
        and namespace == name
    )


def get_tool_call_name(tool_call: Any) -> str | None:
    name = get_mapping_or_attr(tool_call, "name")
    return name if isinstance(name, str) and name else None


def get_tool_call_namespace(tool_call: Any) -> str | None:
    namespace = get_mapping_or_attr(tool_call, "namespace")
    return namespace if isinstance(namespace, str) and namespace else None


def get_function_tool_lookup_key(
    name: str | None, namespace: str | None = None
) -> FunctionToolLookupKey | None:
    if not isinstance(name, str) or not name:
        return None
    if isinstance(namespace, str) and namespace:
        return ("namespaced", namespace, name)
    return ("bare", name)


def get_function_tool_approval_keys(
    *,
    tool_name: str | None,
    tool_namespace: str | None,
    tool_lookup_key: NamedToolLookupKey | None = None,
    include_legacy_deferred_key: bool = False,
) -> list[NamedToolLookupKey]:
    """Return the ordered list of approval cache keys to try for a tool."""
    keys: list[NamedToolLookupKey] = []
    qualified = tool_qualified_name(tool_name, tool_namespace)
    if qualified:
        keys.append(qualified)
    key = get_function_tool_lookup_key(tool_name, tool_namespace)
    if key is not None and key not in keys:
        keys.append(key)
    if tool_lookup_key is not None and tool_lookup_key not in keys:
        keys.append(tool_lookup_key)
    if include_legacy_deferred_key and isinstance(tool_name, str) and tool_name:
        keys.append(("deferred_top_level", tool_name))
    return keys


__all__ = [
    "BareFunctionToolLookupKey",
    "DeferredTopLevelFunctionToolLookupKey",
    "FunctionToolLookupKey",
    "NamedToolLookupKey",
    "NamespacedFunctionToolLookupKey",
    "get_function_tool_approval_keys",
    "get_function_tool_lookup_key",
    "get_mapping_or_attr",
    "get_tool_call_name",
    "get_tool_call_namespace",
    "is_reserved_synthetic_tool_namespace",
    "tool_qualified_name",
    "tool_trace_name",
]