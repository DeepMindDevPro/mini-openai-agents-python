"""Tool subpackage — facade re-exports.

Core splits the monolithic `tool.py` of upstream `openai-agents` into focused files:

- `outputs.py`  — `ToolOutputText / ToolOutputImage / ToolOutputFileContent` + dict variants
- `origin.py`   — `ToolOrigin / ToolOriginType`
- `function.py` — `FunctionTool`, `FunctionToolResult`, `function_tool` decorator

`ComputerTool` / `ShellTool` / `HostedMCPTool` are concrete implementations that ship via
addons (`microagent-sandbox`, `microagent-mcp`); the core only exposes the `Tool` Protocol
they all satisfy.
"""
from __future__ import annotations

from .function import (
    DEFAULT_APPROVAL_REJECTION_MESSAGE,
    FunctionTool,
    FunctionToolResult,
    Tool,
    ToolErrorFunction,
    default_tool_error_function,
    function_tool,
)
from .origin import ToolOrigin, ToolOriginType
from .outputs import (
    ToolOutputFileContent,
    ToolOutputFileContentDict,
    ToolOutputImage,
    ToolOutputImageDict,
    ToolOutputText,
    ToolOutputTextDict,
    ValidToolOutput,
    ValidToolOutputDict,
)

__all__ = [
    "DEFAULT_APPROVAL_REJECTION_MESSAGE",
    "FunctionTool",
    "FunctionToolResult",
    "Tool",
    "ToolErrorFunction",
    "ToolOrigin",
    "ToolOriginType",
    "ToolOutputFileContent",
    "ToolOutputFileContentDict",
    "ToolOutputImage",
    "ToolOutputImageDict",
    "ToolOutputText",
    "ToolOutputTextDict",
    "ValidToolOutput",
    "ValidToolOutputDict",
    "default_tool_error_function",
    "function_tool",
]