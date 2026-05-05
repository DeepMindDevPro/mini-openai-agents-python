"""Structured-output schemas for agents.

`AgentOutputSchema` wraps a user-provided Pydantic model / dataclass / TypedDict and produces:
- The strict JSON Schema sent to the LLM.
- A `validate_json(json_str)` that returns the parsed instance or raises `ModelBehaviorError`.
"""
from __future__ import annotations

import abc
import json
from dataclasses import dataclass
from typing import Any

from pydantic import TypeAdapter, ValidationError

from .exceptions import ModelBehaviorError, UserError
from .strict_schema import ensure_strict_json_schema

_WRAPPER_DICT_KEY = "response"


class AgentOutputSchemaBase(abc.ABC):
    """Abstract contract for agent output schemas."""

    @abc.abstractmethod
    def is_plain_text(self) -> bool: ...

    @abc.abstractmethod
    def name(self) -> str: ...

    @abc.abstractmethod
    def json_schema(self) -> dict[str, Any]: ...

    @abc.abstractmethod
    def is_strict_json_schema(self) -> bool: ...

    @abc.abstractmethod
    def validate_json(self, json_str: str) -> Any: ...


@dataclass(init=False)
class AgentOutputSchema(AgentOutputSchemaBase):
    """Default implementation, backed by a `pydantic.TypeAdapter`."""

    output_type: type[Any]
    _type_adapter: TypeAdapter[Any]
    _is_wrapped: bool
    strict: bool

    def __init__(
        self, output_type: type[Any], *, strict_json_schema: bool = True
    ) -> None:
        if output_type is None:
            raise UserError("AgentOutputSchema requires a non-None output_type")
        self.output_type = output_type
        # Whether the model response must be wrapped in a `{"response": ...}` object.
        # Pydantic will emit a trivial schema for primitive types (str, int); for OpenAI strict
        # mode we wrap them so the JSON always is an object.
        is_primitive = output_type in (str, int, float, bool)
        self._is_wrapped = is_primitive
        if self._is_wrapped:
            self._type_adapter = TypeAdapter(dict[str, output_type])
        else:
            self._type_adapter = TypeAdapter(output_type)
        self.strict = strict_json_schema

    def is_plain_text(self) -> bool:
        return self.output_type is str

    def name(self) -> str:
        return getattr(self.output_type, "__name__", "output")

    def json_schema(self) -> dict[str, Any]:
        schema = self._type_adapter.json_schema()
        if self._is_wrapped:
            schema = {
                "type": "object",
                "properties": {_WRAPPER_DICT_KEY: schema},
                "required": [_WRAPPER_DICT_KEY],
                "additionalProperties": False,
            }
        if self.strict:
            return ensure_strict_json_schema(schema)
        return schema

    def is_strict_json_schema(self) -> bool:
        return self.strict

    def validate_json(self, json_str: str) -> Any:
        try:
            parsed = self._type_adapter.validate_json(json_str)
        except ValidationError as exc:
            raise ModelBehaviorError(f"Failed to validate agent output: {exc}") from exc
        if self._is_wrapped:
            if not isinstance(parsed, dict) or _WRAPPER_DICT_KEY not in parsed:
                raise ModelBehaviorError(
                    f"Expected wrapped output {{'{_WRAPPER_DICT_KEY}': ...}}, got {parsed!r}"
                )
            return parsed[_WRAPPER_DICT_KEY]
        return parsed


__all__ = ["AgentOutputSchema", "AgentOutputSchemaBase"]