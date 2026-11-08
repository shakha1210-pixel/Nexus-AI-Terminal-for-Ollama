"""Built-in provider adapters."""

from app.providers.adapters.ollama import OllamaAdapter
from app.providers.adapters.openai_compatible import OpenAICompatibleAdapter

__all__ = ["OllamaAdapter", "OpenAICompatibleAdapter"]
