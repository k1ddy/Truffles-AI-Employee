from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class LLMResponse:
    content: str
    model: str
    usage: Optional[dict] = None


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    def generate(
        self,
        messages: List[dict],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1000,
    ) -> LLMResponse:
        """Generate response from LLM."""
        pass
