from __future__ import annotations

from typing import Protocol


class AIProviderError(Exception):
    """Raised when an AI provider cannot generate a response."""


class AIProvider(Protocol):
    """Common interface implemented by all AI generation providers."""

    async def generate(self, prompt: str) -> str:
        """Generate text from a prompt."""
        ...
        