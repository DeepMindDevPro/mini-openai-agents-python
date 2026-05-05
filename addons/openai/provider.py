"""OpenAI provider for microagent."""

from __future__ import annotations

from typing import Any, Dict

from microagent.models.interface import ModelProvider

from .model import OpenAIModel


class OpenAIProvider(ModelProvider):
    """OpenAI model provider."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout: float = 60.0,
        max_retries: int = 2,
        **kwargs: Any,
    ) -> None:
        """Initialize OpenAI provider."""
        self.api_key = api_key
        self.base_url = base_url
        self.timeout = timeout
        self.max_retries = max_retries
        self._kwargs = kwargs

    def get_model(self, model_name: str | None = None) -> OpenAIModel:
        """Get OpenAI model by name."""
        if model_name is None:
            model_name = "gpt-4o-mini"
        
        return OpenAIModel(
            model=model_name,
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=self.timeout,
            max_retries=self.max_retries,
            **self._kwargs,
        )

    def list_models(self) -> list[str]:
        """List available OpenAI models."""
        return [
            "gpt-4o",
            "gpt-4o-mini",
            "gpt-4-turbo",
            "gpt-3.5-turbo",
            "o1-preview",
            "o1-mini",
        ]

    def get_model_info(self, model_name: str) -> Dict[str, Any]:
        """Get information about a specific model."""
        model_info = {
            "gpt-4o": {
                "description": "Most advanced multimodal model",
                "max_tokens": 128000,
                "supports_vision": True,
                "supports_tools": True,
            },
            "gpt-4o-mini": {
                "description": "Fast, affordable small model",
                "max_tokens": 128000,
                "supports_vision": True,
                "supports_tools": True,
            },
            "gpt-4-turbo": {
                "description": "High-performance model",
                "max_tokens": 128000,
                "supports_vision": True,
                "supports_tools": True,
            },
            "gpt-3.5-turbo": {
                "description": "Cost-effective model",
                "max_tokens": 16385,
                "supports_vision": False,
                "supports_tools": True,
            },
            "o1-preview": {
                "description": "Reasoning model preview",
                "max_tokens": 128000,
                "supports_vision": True,
                "supports_tools": False,
            },
            "o1-mini": {
                "description": "Fast reasoning model",
                "max_tokens": 128000,
                "supports_vision": True,
                "supports_tools": False,
            },
        }
        
        return model_info.get(model_name, {
            "description": f"Unknown model: {model_name}",
            "max_tokens": 4096,
            "supports_vision": False,
            "supports_tools": True,
        })