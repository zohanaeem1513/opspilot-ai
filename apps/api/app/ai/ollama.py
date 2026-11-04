from __future__ import annotations

import httpx

from app.ai.base import AIProviderError

REQUEST_TIMEOUT_SECONDS = 120.0


class OllamaProvider:
    """Generate text using a locally running Ollama server."""

    def __init__(self, base_url: str, model: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model

    async def generate(self, prompt: str) -> str:
        url = f"{self._base_url}/api/generate"

        payload = {
            "model": self._model,
            "prompt": prompt,
            "stream": False,
        }

        try:
            async with httpx.AsyncClient(
                timeout=REQUEST_TIMEOUT_SECONDS
            ) as client:
                response = await client.post(
                    url,
                    json=payload,
                )

                response.raise_for_status()

        except httpx.HTTPError as exc:
            raise AIProviderError(
                "Ollama request failed"
            ) from exc

        try:
            data = response.json()
            text = data["response"].strip()

        except (
            AttributeError,
            KeyError,
            TypeError,
            ValueError,
        ) as exc:
            raise AIProviderError(
                "Ollama returned an invalid response"
            ) from exc

        if not text:
            raise AIProviderError(
                "Ollama returned an empty response"
            )

        return text