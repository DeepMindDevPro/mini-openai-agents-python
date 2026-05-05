"""MultiProvider — prefix-routed `ModelProvider` picker.

Routes requests like `"openai/gpt-4o"` or `"claude/opus"` to the registered provider
whose prefix matches. Unknown prefixes fall back to an explicit default (if set) or
raise `UserError`.

    provider = MultiProvider({
        "openai": OpenAIProvider(api_key=os.getenv("OPENAI_API_KEY")),
        "claude": AnthropicProvider(api_key=os.getenv("ANTHROPIC_API_KEY")),
    }, default_prefix="openai")
    model = provider.get_model("openai/gpt-4o-mini")
"""
from __future__ import annotations

from typing import Any

from ..exceptions import UserError
from .interface import Model, ModelProvider


class MultiProvider(ModelProvider):
    """Route `"<prefix>/<model>"` strings to the matching inner provider."""

    def __init__(
        self,
        providers: dict[str, ModelProvider] | None = None,
        *,
        default_prefix: str | None = None,
        separator: str = "/",
    ) -> None:
        self._providers: dict[str, ModelProvider] = dict(providers or {})
        self._default_prefix = default_prefix
        self._separator = separator

    # ---- registry management ----

    def register(self, prefix: str, provider: ModelProvider) -> None:
        self._providers[prefix] = provider

    def unregister(self, prefix: str) -> None:
        self._providers.pop(prefix, None)

    def prefixes(self) -> list[str]:
        return sorted(self._providers)

    # ---- ModelProvider contract ----

    def get_model(self, model_name: str | None) -> Model:
        prefix, suffix = self._split(model_name)
        provider = self._providers.get(prefix)
        if provider is None:
            raise UserError(
                f"No provider registered for prefix {prefix!r}. "
                f"Registered prefixes: {self.prefixes()}."
            )
        return provider.get_model(suffix)

    # ---- internals ----

    def _split(self, model_name: str | None) -> tuple[str, str | None]:
        if not isinstance(model_name, str) or not model_name:
            if self._default_prefix is None:
                raise UserError(
                    "MultiProvider was called without a model name and has no default_prefix."
                )
            return self._default_prefix, None

        if self._separator in model_name:
            prefix, _, suffix = model_name.partition(self._separator)
            if prefix:
                return prefix, (suffix or None)

        # No prefix — fall back to default.
        if self._default_prefix is None:
            raise UserError(
                f"Model name {model_name!r} has no prefix and MultiProvider has no default_prefix."
            )
        return self._default_prefix, model_name


__all__ = ["MultiProvider"]