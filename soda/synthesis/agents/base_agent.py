from abc import ABC, abstractmethod
from typing import Any, Dict

from soda.synthesis.clients.base_client import LLMClient
from soda.synthesis.models import (
    AgentInput,
    AgentOutput,
)


class BaseAgent(ABC):
    """Abstract base class for all synthesis agents."""
    
    def __init__(self, name: str, llm_client: LLMClient, system_prompt: str):
        """Initialize base agent.
        
        Args:
            name: Agent identifier (e.g., "ODI_Data_Analyst")
            llm_client: LLM client instance
            system_prompt: System/persona prompt for the agent
        """
        self.name = name
        self.client = llm_client
        self.system_prompt = system_prompt
    
    @abstractmethod
    async def process(self, agent_input: AgentInput) -> AgentOutput:
        """Process agent input and return output.
        
        This is the main method each agent must implement.
        
        Args:
            agent_input: Standardized input containing segments, context, etc.
            
        Returns:
            AgentOutput with analysis, strategies, critiques, etc.
        """
        pass
    
    
    def _validate_agent_input(self, agent_input: AgentInput) -> None:
        """Validate agent input before processing."""
        
        if not agent_input.segments:
            raise ValueError("AgentInput missing segments data")
        
        if not agent_input.context:
            raise ValueError("AgentInput missing business context")
        
        if not agent_input.segments.segments:
            raise ValueError("No segments found in segments data")
    
    def get_agent_info(self) -> Dict[str, Any]:
        """Return agent metadata."""
        return {
            "name": self.name,
            "model": self.client.get_model_info(),
            "system_prompt_length": len(self.system_prompt)
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Test agent functionality with simple prompt."""
        try:
            test_response = await self.client.complete(
                prompt="Respond with 'OK' if you can process this message.",
                max_tokens=10,
                temperature=0.1
            )
            
            return {
                "status": "healthy",
                "response": test_response.content,
                "model": test_response.model,
                "provider": test_response.provider.value
            }
        except Exception as e:
            return {
                "status": "unhealthy", 
                "error": str(e),
                "agent": self.name
            }