"""JSON Schema strict-mode normalization.

Used by Agent output schemas, FunctionTool parameters, Handoff input schemas, and MCP tool
registrations. Strict mode (as defined by the OpenAI function-calling / structured-output APIs)
requires:

1. `additionalProperties: false` on every object schema.
2. `required` lists every declared property.
3. `$ref` is resolved inline (no external references).
4. `anyOf / oneOf` branches follow the same rules recursively.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any

SCHEMA_NORMALIZATION_MARKER = "__microagent_strict__"


def ensure_strict_json_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """Return a new strict-mode JSON Schema dict.

    The original dict is not mutated. `$ref` entries are resolved against the root
    `$defs` (and legacy `definitions`) before normalization.
    """
    if not isinstance(schema, dict):
        return schema
    cloned = deepcopy(schema)
    if cloned.get(SCHEMA_NORMALIZATION_MARKER):
        return cloned
    defs = cloned.get("$defs") or cloned.get("definitions") or {}
    return _normalize(cloned, defs, is_root=True)


def _normalize(node: Any, defs: dict[str, Any], *, is_root: bool = False) -> Any:
    if isinstance(node, dict):
        if "$ref" in node and isinstance(node["$ref"], str):
            ref = node["$ref"]
            if ref.startswith("#/$defs/") or ref.startswith("#/definitions/"):
                name = ref.split("/")[-1]
                target = defs.get(name)
                if target is not None:
                    merged = deepcopy(target)
                    for k, v in node.items():
                        if k == "$ref":
                            continue
                        merged[k] = v
                    return _normalize(merged, defs)
        # Normalize object schemas.
        if node.get("type") == "object" or "properties" in node:
            props = node.get("properties")
            if isinstance(props, dict):
                node["properties"] = {k: _normalize(v, defs) for k, v in props.items()}
                if "required" not in node or not isinstance(node.get("required"), list):
                    node["required"] = list(node["properties"].keys())
                else:
                    # Ensure every property is in required for strict mode.
                    node["required"] = list(node["properties"].keys())
                node.setdefault("additionalProperties", False)
        # Recurse into array items, anyOf / oneOf / allOf branches.
        for key in ("items", "prefixItems"):
            if key in node:
                node[key] = _normalize(node[key], defs)
        for key in ("anyOf", "oneOf", "allOf"):
            if key in node and isinstance(node[key], list):
                node[key] = [_normalize(b, defs) for b in node[key]]
        if is_root:
            node[SCHEMA_NORMALIZATION_MARKER] = True
        return node
    if isinstance(node, list):
        return [_normalize(n, defs) for n in node]
    return node