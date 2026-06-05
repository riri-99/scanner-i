# Groq backend - call api.groq.com (ffree tier fallback)

from __future__ import annotations
 
import json
import urllib.request
import urllib.error
 
from .base import ModelClient
 
 
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
 
# Groq free tier hard limits — stay well under these
MAX_TOKENS   = 2048     # max response tokens to request
TIMEOUT_SECS = 60       # Groq is fast, 60s is more than enough
 
 
class GroqClient(ModelClient):
 
    def __init__(self, api_key: str, model: str, temperature: float):
        self.api_key     = api_key
        self.model       = model
        self.temperature = temperature
 
    # Public interface 
 
    def complete(self, system: str, user: str) -> str:
        """
        Send a chat completion request to Groq and return the response string.
        Uses the OpenAI-compatible /v1/chat/completions endpoint.
        """
        payload = {
            "model":       self.model,
            "temperature": self.temperature,
            "max_tokens":  MAX_TOKENS,
            "stream":      False,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user",   "content": user},
            ],
        }
 
        body = json.dumps(payload).encode("utf-8")
        req  = urllib.request.Request(
            GROQ_API_URL,
            data=body,
            headers={
                "Content-Type":  "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )
 
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT_SECS) as resp:
                data = json.loads(resp.read().decode("utf-8"))
 
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8", errors="ignore")
            self._raise_groq_error(e.code, error_body)
 
        except urllib.error.URLError as e:
            raise RuntimeError(
                "Could not reach Groq API — check your internet connection."
            ) from e
 
        return self._extract_content(data)
 
    # Response parsing 
 
    @staticmethod
    def _extract_content(data: dict) -> str:
        """
        Pull the assistant message content out of the OpenAI-format response.
 
        Response structure:
          {
            "choices": [
              {"message": {"role": "assistant", "content": "..."}, ...}
            ]
          }
        """
        try:
            content = data["choices"][0]["message"]["content"].strip()
        except (KeyError, IndexError) as e:
            raise RuntimeError(
                f"Unexpected Groq response structure: {data}"
            ) from e
 
        if not content:
            raise RuntimeError("Groq returned an empty response.")
 
        return content
 
    @staticmethod
    def _raise_groq_error(status_code: int, body: str) -> None:
        """Map common Groq HTTP errors to clear, actionable messages."""
        messages = {
            401: "Invalid GROQ_API_KEY — check the key in your .env file.",
            429: "Groq rate limit hit — wait a moment and try again.",
            413: "Request too large — the repo context may be too long for this model.",
            503: "Groq service temporarily unavailable — try again shortly.",
        }
        msg = messages.get(status_code, f"Groq API error {status_code}: {body}")
        raise RuntimeError(msg)
 
    @property
    def name(self) -> str:
        return f"Groq ({self.model})"