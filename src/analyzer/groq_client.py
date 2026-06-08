from __future__ import annotations

import json
import os
import urllib.request
import urllib.error

from dotenv import load_dotenv

from .base import ModelClient

load_dotenv()

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

MAX_TOKENS = 2048
TIMEOUT_SECS = 60


class GroqClient(ModelClient):

    def __init__(self, model: str, temperature: float):
        self.api_key = os.getenv("GROQ_API_KEY")

        if not self.api_key:
            raise RuntimeError(
                "GROQ_API_KEY not found in .env file."
            )

        self.model = model
        self.temperature = temperature

    def complete(self, system: str, user: str) -> str:

        payload = {
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": MAX_TOKENS,
            "stream": False,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }

        body = json.dumps(payload).encode("utf-8")

        req = urllib.request.Request(
            GROQ_API_URL,
            data=body,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "User-Agent": "readmegen/0.1.0",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(
                req,
                timeout=TIMEOUT_SECS
            ) as resp:
                data = json.loads(
                    resp.read().decode("utf-8")
                )

        except urllib.error.HTTPError as e:
            error_body = e.read().decode(
                "utf-8",
                errors="ignore"
            )

            raise RuntimeError(
                f"Groq API error {e.code}: {error_body}"
            ) from e

        except urllib.error.URLError as e:
            raise RuntimeError(
                "Could not reach Groq API."
            ) from e

        return self._extract_content(data)

    @staticmethod
    def _extract_content(data: dict) -> str:
        try:
            return (
                data["choices"][0]
                ["message"]["content"]
                .strip()
            )
        except (KeyError, IndexError) as e:
            raise RuntimeError(
                f"Unexpected Groq response: {data}"
            ) from e

    @property
    def name(self) -> str:
        return f"Groq ({self.model})"