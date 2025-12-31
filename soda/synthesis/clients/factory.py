import os

from soda.synthesis.clients.anthropic_client import AnthropicClient
from soda.synthesis.clients.base_client import LLMClient
from soda.synthesis.clients.openai_client import OpenAIClient


class ClientFactory:
    """Create LLM clients from config."""
    
    @staticmethod
    def create_client(provider_config: dict, agent_config: dict) -> LLMClient:
        """Create client from provider and agent config."""
        
        provider = agent_config.provider
        api_key = os.getenv(provider_config.api_key_env)
        model = provider_config.default_model 
        
        if provider == "anthropic":
            return AnthropicClient(api_key=api_key, model=model)
        elif provider == "openai":
            return OpenAIClient(api_key=api_key, model=model)
        else:
            raise ValueError(f"Unsupported provider: {provider}")