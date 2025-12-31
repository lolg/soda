from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from soda.synthesis.clients.base_client import LLMClient, LLMMessage
from soda.synthesis.models import AgentInput, AgentOutput


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

    async def chat(self, conversation: List[LLMMessage]) -> AgentOutput:
        """Handle conversation-based interaction."""
    
        try:
            response = await self.client.chat(
                messages=conversation,
                max_tokens=self.client.default_max_tokens,
                temperature=self.client.default_temperature
            )
            
            return AgentOutput(
                agent_name=self.name,
                content=response.content,
                confidence=0.0,
                timestamp=datetime.now()
            )
        
        except Exception as e:
            raise RuntimeError(f"{self.name} chat failed: {str(e)}")
    
    def _load_prompt(self, prompt_path: str) -> str:
        """Load prompt from file path."""
        # Resolve relative path from current working directory
        full_path = Path.cwd() / prompt_path
        
        with open(full_path, 'r', encoding='utf-8') as f:
            return f.read().strip()
    
    def _substitute_variables(self, template: str, **variables) -> str:
        """Replace variables in template."""
        for key, value in variables.items():
            template = template.replace(f"{{{{{key}}}}}", str(value))
        return template
    
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