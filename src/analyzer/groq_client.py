# Groq backend - call api.groq.com (ffree tier fallback)

from .base import ModelClient

class GroqClient(ModelClient):
    def __init__(self, api_key: str, model: str, temperature: float):
        self.api_key = api_key
        self.model = model
        self.temperature = temperature

    def complete(self, system: str, user: str) -> str:
        raise NotImplementedError("GroqClient.complete() - in progress")
    
    @property
    def name(self) -> str:
        return f"Groq({self.model})"
    
