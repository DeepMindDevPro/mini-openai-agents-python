"""Model provider abstractions and built-in implementations.

Built-ins (v0.1 MVP):
- `interface.Model` / `ModelProvider` / `ModelTracing` — the abstract contracts.
- `fake_model.FakeModel`                               — deterministic in-process model for tests.

Addons (v0.2+):
- `microagent-openai`  — ChatCompletions + Responses.
- `microagent-anthropic` — Claude.
- `microagent-bedrock` — AWS Bedrock (titan / claude).
"""

from .fake_model import FakeModel, FakeModelTurn
from .interface import Model, ModelProvider, ModelTracing

__all__ = ["FakeModel", "FakeModelTurn", "Model", "ModelProvider", "ModelTracing"]