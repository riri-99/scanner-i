"""
Defines the model client interface. both ollamaclient and groqclient implements this- the rest of the codebase only talks to this interface.
Never to the cliet directly.

"""

from abc import ABC, abstractmethod

class ModelClient(ABC):

    @abstractmethod
    def complete(self, system: str, user: str) -> str:
        # Sends a system plus user prompt to the model and returns the raw response.
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        # Human readable backend name
        ...