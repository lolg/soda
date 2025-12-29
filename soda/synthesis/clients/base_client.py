from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional


class LLMProvider(Enum):
    """Supported LLM providers."""
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    GOOGLE = "google"


@dataclass
class LLMResponse:
    """Standardized response from any LLM provider."""
    content: str
    model: str
    provider: LLMProvider


class LLMClientError(Exception):
    """Base exception for LLM client errors."""
    pass


class LLMProviderError(LLMClientError):
    """Provider-specific errors (API failures, rate limits, etc.)."""
    pass


class LLMValidationError(LLMClientError):
    """Input validation errors."""
    pass


class LLMClient(ABC):
    """Abstract base class for all LLM provider clients."""
    
    def __init__(
        self, 
        api_key: str,
        model: str,
        default_max_tokens: int = 1000,
        default_temperature: float = 0.7
    ):
        self.api_key = api_key
        self.model = model
        self.default_max_tokens = default_max_tokens
        self.default_temperature = default_temperature
        
    @property
    @abstractmethod
    def provider(self) -> LLMProvider:
        """Return the provider type."""
        pass
    
    @abstractmethod
    async def complete(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None
    ) -> LLMResponse:
        """Generate a completion for a single prompt."""
        pass
    
    def get_model_info(self) -> Dict[str, Any]:
        """Return model information."""
        return {
            "provider": self.provider.value,
            "model": self.model
        }
    
    def _get_max_tokens(self, max_tokens: Optional[int]) -> int:
        """Get max tokens, using default if not specified."""
        return max_tokens if max_tokens is not None else self.default_max_tokens
    
    def _get_temperature(self, temperature: Optional[float]) -> float:
        """Get temperature, using default if not specified."""
        return temperature if temperature is not None else self.default_temperature
    
    async def _handle_provider_error(self, error: Exception) -> None:
        """Handle provider-specific errors consistently."""
        raise LLMProviderError(f"{self.provider.value} API error: {str(error)}") from error