from typing import List, Optional

import openai

from soda.synthesis.clients.base_client import LLMClient, LLMMessage, LLMProvider, LLMResponse


class OpenAIClient(LLMClient):
    """OpenAI GPT client implementation."""
    
    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4",
        **kwargs
    ):
        super().__init__(api_key, model, **kwargs)
        self.client = openai.AsyncOpenAI(api_key=api_key)
    
    @property
    def provider(self) -> LLMProvider:
        return LLMProvider.OPENAI
    
    async def complete(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None
    ) -> LLMResponse:
        """Generate completion using OpenAI API."""
        
        # Convert to chat format
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=self._get_max_tokens(max_tokens),
                temperature=self._get_temperature(temperature)
            )
            
            return LLMResponse(
                content=response.choices[0].message.content,
                model=self.model,
                provider=self.provider
            )
            
        except Exception as e:
            await self._handle_provider_error(e)
    
    async def chat(
        self,
        messages: List[LLMMessage],
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None
    ) -> LLMResponse:
        """Generate chat response using OpenAI API."""
        
        # Convert LLMMessage to OpenAI format
        openai_messages = []
        for msg in messages:
            openai_messages.append({
                "role": msg.role,
                "content": msg.content
            })
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=openai_messages,
                max_tokens=self._get_max_tokens(max_tokens),
                temperature=self._get_temperature(temperature)
            )
            
            return LLMResponse(
                content=response.choices[0].message.content,
                model=self.model,
                provider=self.provider
            )
            
        except Exception as e:
            await self._handle_provider_error(e)