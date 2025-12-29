from datetime import datetime
from pathlib import Path

from soda.synthesis.agents.base_agent import BaseAgent
from soda.synthesis.clients.base_client import LLMClient
from soda.synthesis.config import AgentConfig
from soda.synthesis.models import AgentInput, AgentOutput


class DataAnalystAgent(BaseAgent):
    """ODI expert agent that analyzes segment data and identifies strategic patterns."""
    
    def __init__(self, llm_client: LLMClient, agent_config: AgentConfig):
        
        system_prompt = self._load_prompt(agent_config.system_prompt)
        self.user_prompt_template = self._load_prompt(agent_config.user_prompt)
        self.llm_config = agent_config.llm_config
        
        super().__init__("ODI_Data_Analyst", llm_client, system_prompt)
    
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
    
    async def process(self, agent_input: AgentInput) -> AgentOutput:
        """Analyze segments using ODI methodology."""

        # Serialize to JSON for LLM consumption
        segments_json = agent_input.segments.model_dump_json(indent=2)
        context_json = agent_input.context.model_dump_json(indent=2)
        
        # Substitute variables in user prompt template
        user_prompt = self._substitute_variables(
            self.user_prompt_template,
            segments_json=segments_json,
            context_json=context_json
        )
        
        try:
            response = await self.client.complete(
                prompt=user_prompt,
                system_prompt=self.system_prompt,
                max_tokens=self.llm_config.max_tokens,
                temperature=self.llm_config.temperature
            )
            
            return AgentOutput(
                agent_name=self.name,
                content=response.content,
                confidence=0.0,
                timestamp=datetime.now()
            )
            
        except Exception as e:
            raise RuntimeError(f"DataAnalyst processing failed: {str(e)}")