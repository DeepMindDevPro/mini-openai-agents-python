"""Function tool implementation."""

from __future__ import annotations

import functools
from typing import Any, Callable, Dict, List, Optional

from pydantic import BaseModel


class FunctionTool:
    """A tool that wraps a function."""

    def __init__(
        self,
        func: Callable[..., Any],
        name: str | None = None,
        description: str | None = None,
    ):
        """Initialize FunctionTool."""
        self.func = func
        self.name = name or func.__name__
        self.description = description or func.__doc__ or ""
        
        # Create schema from function signature
        self.schema = self._create_schema(func)

    def _create_schema(self, func: Callable[..., Any]) -> Dict[str, Any]:
        """Create JSON schema for the function."""
        import inspect
        
        sig = inspect.signature(func)
        parameters = {}
        
        for name, param in sig.parameters.items():
            param_type = param.annotation if param.annotation != inspect.Parameter.empty else Any
            parameters[name] = {
                "type": "string",  # Simplified
                "description": f"Parameter {name}",
            }
        
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": parameters,
                "required": [name for name, param in sig.parameters.items() if param.default == inspect.Parameter.empty],
            },
        }

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        """Call the wrapped function."""
        return self.func(*args, **kwargs)

    @classmethod
    def wrap(cls, func: Callable[..., Any]) -> FunctionTool:
        """Wrap a function as a tool."""
        return cls(func)


def tool(name: str | None = None, description: str | None = None) -> Callable[[Callable[..., Any]], FunctionTool]:
    """Decorator to create a FunctionTool."""
    def decorator(func: Callable[..., Any]) -> FunctionTool:
        return FunctionTool(func, name, description)
    return decorator


__all__ = ["FunctionTool", "tool"]