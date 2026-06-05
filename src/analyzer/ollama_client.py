# Ollama backend calls the local ollama server at local host 11434

from .base import ModelClient

class OllamaClient(ModelClient):
    def __init__(self, host: str, model: str, temperature: float, timeout: int):
        self.host = host
        self.model = model
        self.temperature = temperature
        self.timeout = timeout

    def complete(self, system: str, user:str) -> str:
        raise NotImplementedError("OllamaClient.complete() - in progress")
    
    @property
    def name(self) -> str:
        return f"Ollama({self.model})"
    
