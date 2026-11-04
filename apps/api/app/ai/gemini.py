from __future__ import annotations

import httpx

from app.ai.base import AIProviderError

GEMINI_API_URL = (
    "https://generativelanguage.googleapis.com/"
    "v1beta/models/{model}:generateContent"
)

REQUEST_TIMEOUT_SECONDS = 60.0


class GeminiProvider:
    """Generate text using Google's Gemini API."""

    def __init__(self, api_key: str, model: str) -> None:
        self._api_key = api_key
        self._model = model

    async def generate(self, prompt: str) -> str:
        url = GEMINI_API_URL.format(model=self._model)

        payload = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": prompt,
                        }
                    ]
                }
            ]
        }

        try:
            async with httpx.AsyncClient(
                timeout=REQUEST_TIMEOUT_SECONDS
            ) as client:
                response = await client.post(
                    url,
                    headers={
                        "x-goog-api-key": self._api_key,
                    },
                    json=payload,
                )

                response.raise_for_status()

        except httpx.HTTPError as exc:
            raise AIProviderError("Gemini request failed") from exc

        try:
            data = response.json()
            parts = data["candidates"][0]["content"]["parts"]

            text = "".join(
                part.get("text", "")
                for part in parts
            ).strip()

        except (
            AttributeError,
            IndexError,
            KeyError,
            TypeError,
            ValueError,
        ) as exc:
            raise AIProviderError(
                "Gemini returned an invalid response"
            ) from exc

        if not text:
            raise AIProviderError(
                "Gemini returned an empty response"
            )

        return text