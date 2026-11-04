from __future__ import annotations

from app.ai.base import AIProvider, AIProviderError
from app.ai.gemini import GeminiProvider
from app.ai.ollama import OllamaProvider
from app.core.config import settings


def get_ai_provider() -> AIProvider:
    """Create the AI provider selected by backend configuration."""

    provider_name = settings.ai_provider.strip().lower()

    if provider_name == "gemini":
        if not settings.gemini_api_key:
            raise AIProviderError(
                "Gemini API key is not configured"
            )

        return GeminiProvider(
            api_key=settings.gemini_api_key,
            model=settings.gemini_model,
        )

    if provider_name == "ollama":
        return OllamaProvider(
            base_url=settings.ollama_base_url,
            model=settings.ollama_model,
        )

    raise AIProviderError(
        "Unsupported AI provider configuration"
    )