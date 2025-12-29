from typing import Optional

import anthropic

from soda.synthesis.clients.base_client import LLMClient, LLMProvider, LLMResponse


class AnthropicClient(LLMClient):
    """Anthropic Claude client implementation."""
    
    def __init__(
        self, 
        api_key: str, 
        model: str = "claude-4-sonnet-20250514",
        **kwargs
    ):
        super().__init__(api_key, model, **kwargs)
        self.client = anthropic.AsyncAnthropic(api_key=api_key)
    
    @property
    def provider(self) -> LLMProvider:
        return LLMProvider.ANTHROPIC
    
    async def complete(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None
    ) -> LLMResponse:
        """Generate completion using Anthropic API."""
        
        try:
            response = await self.client.messages.create(
                model=self.model,
                system=system_prompt or "",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=self._get_max_tokens(max_tokens),
                temperature=self._get_temperature(temperature)
            )
            
            return LLMResponse(
                content=response.content[0].text,
                model=self.model,
                provider=self.provider
            )
            
        except Exception as e:
            await self._handle_provider_error(e)