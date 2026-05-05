"""OpenAI addon for microagent - ChatCompletions support."""

from .model import OpenAIModel
from .provider import OpenAIProvider

__all__ = [
    "OpenAIModel",
    "OpenAIProvider",
]