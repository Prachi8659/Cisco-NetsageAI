from abc import ABC, abstractmethod
from typing import Any, Dict

class BaseAiProvider(ABC):
    """Abstract interface for AI model providers."""

    @abstractmethod
    def generate_diagnosis(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str,
        timeout: int = 30
    ) -> Dict[str, Any]:
        """
        Send prompt to AI provider and return parsed JSON response dict.
        Must raise an exception or return a valid JSON dict.
        """
        pass
