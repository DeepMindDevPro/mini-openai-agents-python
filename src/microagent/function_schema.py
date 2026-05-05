"""Python function → JSON Schema extraction for tool registration.

Produces a `FuncSchema` that contains:
- `name` / `description` (from function name + docstring).
- `params_pydantic_model` — a generated Pydantic model mirroring the parameters.
- `params_json_schema` — the JSON schema for the LLM.
- `takes_context` — True if the first parameter is `RunContextWrapper` or `ToolContext`.

Supports all 5 parameter kinds (`POSITIONAL_ONLY`, `POSITIONAL_OR_KEYWORD`, `VAR_POSITIONAL`,
`KEYWORD_ONLY`, `VAR_KEYWORD`).

Optional `griffelib` integration for richer docstring parsing (Google / NumPy style) lives
behind a `docstring` extras install; core stays dependency-light.
"""
from __future__ import annotations

import inspect
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, get_type_hints

from pydantic import BaseModel, Field, create_model
from pydantic.fields import FieldInfo

from .exceptions import UserError
from .run_context import RunContextWrapper
from .strict_schema import ensure_strict_json_schema
from .tool_context import ToolContext


@dataclass
class FuncSchema:
    name: str
    description: str | None
    params_pydantic_model: type[BaseModel]
    params_json_schema: dict[str, Any]
    signature: inspect.Signature
    takes_context: bool = False
    strict_json_schema: bool = True

    def to_call_args(self, data: BaseModel) -> tuple[list[Any], dict[str, Any]]:
        positional: list[Any] = []
        keyword: dict[str, Any] = {}
        seen_var_positional = False
        for idx, (pname, param) in enumerate(self.signature.parameters.items()):
            if self.takes_context and idx == 0:
                continue
            value = getattr(data, pname, None)
            kind = param.kind
            if kind == param.VAR_POSITIONAL:
                positional.extend(value or [])
                seen_var_positional = True
            elif kind == param.VAR_KEYWORD:
                keyword.update(value or {})
            elif kind in (param.POSITIONAL_ONLY, param.POSITIONAL_OR_KEYWORD):
                if not seen_var_positional:
                    positional.append(value)
                else:
                    keyword[pname] = value
            else:  # KEYWORD_ONLY
                keyword[pname] = value
        return positional, keyword


def _takes_context(func: Callable[..., Any]) -> bool:
    try:
        sig = inspect.signature(func)
    except (ValueError, TypeError):
        return False
    try:
        hints = get_type_hints(func, include_extras=False)
    except Exception:
        hints = {}
    params = list(sig.parameters.values())
    if not params:
        return False
    first = params[0]
    annot = hints.get(first.name, first.annotation)
    if annot is inspect.Parameter.empty:
        return False
    # Accept direct subclass or parameterized generic of RunContextWrapper/ToolContext.
    origin = getattr(annot, "__origin__", annot)
    try:
        return isinstance(origin, type) and issubclass(
            origin, (RunContextWrapper, ToolContext)
        )
    except TypeError:
        return False


def function_schema(
    func: Callable[..., Any],
    *,
    name_override: str | None = None,
    description_override: str | None = None,
    strict_json_schema: bool = True,
) -> FuncSchema:
    """Build a `FuncSchema` from a Python function."""
    if not callable(func):
        raise UserError(f"function_schema expected a callable, got {type(func).__name__}")
    try:
        sig = inspect.signature(func)
    except (ValueError, TypeError) as exc:
        raise UserError(f"Cannot introspect signature of {func!r}: {exc}") from exc
    try:
        hints = get_type_hints(func, include_extras=True)
    except Exception:
        hints = {}

    takes_context = _takes_context(func)
    fields: dict[str, tuple[Any, FieldInfo]] = {}

    for idx, (pname, param) in enumerate(sig.parameters.items()):
        if takes_context and idx == 0:
            continue
        annotation = hints.get(pname, param.annotation)
        if annotation is inspect.Parameter.empty:
            annotation = Any  # let pydantic accept anything
        default = param.default
        info_kwargs: dict[str, Any] = {}
        if param.kind == param.VAR_POSITIONAL:
            # Represent *args as list[Annotation]
            annotation = list[annotation]  # type: ignore[valid-type]
            default = []
        elif param.kind == param.VAR_KEYWORD:
            annotation = dict[str, annotation]  # type: ignore[valid-type]
            default = {}
        if default is inspect.Parameter.empty:
            fields[pname] = (annotation, Field(..., **info_kwargs))
        else:
            fields[pname] = (annotation, Field(default=default, **info_kwargs))

    model_name = f"{(name_override or func.__name__).title().replace('_', '')}Args"
    if fields:
        params_model: type[BaseModel] = create_model(model_name, **fields)  # type: ignore[call-overload]
    else:
        # Empty parameter model — pydantic requires at least a dummy sentinel to build schema.
        params_model = create_model(model_name)

    raw_schema = params_model.model_json_schema()
    if strict_json_schema:
        schema = ensure_strict_json_schema(raw_schema)
    else:
        schema = raw_schema

    description = description_override or inspect.getdoc(func)
    if description:
        description = description.strip()

    return FuncSchema(
        name=name_override or func.__name__,
        description=description,
        params_pydantic_model=params_model,
        params_json_schema=schema,
        signature=sig,
        takes_context=takes_context,
        strict_json_schema=strict_json_schema,
    )


__all__ = ["FuncSchema", "function_schema"]