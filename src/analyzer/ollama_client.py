# Ollama backend calls the local ollama server at local host 11434


from __future__ import annotations

import json
import urllib.request
import urllib.error
from typing import Iterator

from .base import ModelClient

class OllamaClient(ModelClient):
    def __init__(self, host: str, model: str, temperature: float, timeout: int):
        self.host = host
        self.model = model
        self.temperature = temperature
        self.timeout = timeout

    def complete(self, system: str, user:str) -> str:
        payload = {
            "model": self.model,
            "stream": True,
            "options": {"temperature": self.temperature},
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }

        url = f"{self.host}/api/chat"
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=body,
            headers = {
                "Content-Type": "application/json",
                "User-Agent": "readmegen/0.1.0",
            },
            method = "POST",
        )

        try :
            with urllib.request.urlopen(req, timeout = self.timeout) as resp:
                return self._assemble_stream(resp)
            
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8", errors="ignore")
            raise RuntimeError(
                f"Ollama returned HTTP {e.code}: {error_body}"
            ) from e
        
        except urllib.error.URLError as e:
            raise RuntimeError(
                f"Could not reach Ollama at {self.host} - is it running?"
            ) from e
        
    # Stream Assembler
    
    def _assemble_stream(self, response) -> str:
        parts: list[str] = []

        for chunk in self._iter_lines(response):
            if not chunk:
                continue
            try:
                data = json.loads(chunk)
            except json.JSONDecodeError:
                continue

            # Extract continue from this chunk
            content = data.get("message", {}).get("content", "")
            if content:
                parts.append(content)

            # stop when ollama signals the stream is done
            if data.get("done", False):
                break
        result = "".join(parts).strip()

        if not result:
            raise RuntimeError("Ollama returned an empty response.")
        
        return result
    
    @staticmethod
    def _iter_lines(response) -> Iterator[str]:
        buffer = b""
        while True:
            chunk = response.read(512)
            if not chunk:
                if buffer:
                    yield buffer.decode("utf-8", errors = "ignore")
                break
            buffer += chunk
            while b"\n" in buffer:
                line, buffer = buffer.split(b"\n", 1)
                yield line.decode("utf-8", errors ="ignore")
    
    @property
    def name(self) -> str:
        return f"Ollama({self.model})"
    
