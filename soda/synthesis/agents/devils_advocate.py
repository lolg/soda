
from soda.synthesis.agents.base_agent import BaseAgent
from soda.synthesis.clients.base_client import LLMClient
from soda.synthesis.config import AgentConfig
from soda.synthesis.models import AgentInput, AgentOutput


class DevilsAdvocateAgent(BaseAgent):
    """Agent that challenges analysis for rigor and identifies weaknesses."""
    
    def __init__(self, llm_client: LLMClient, agent_config: AgentConfig):
        system_prompt = self._load_prompt(agent_config.system_prompt)
        self.llm_config = agent_config.llm_config
        
        super().__init__("Devils_Advocate", llm_client, system_prompt)
    
    

    async def process(self, agent_input: AgentInput) -> AgentOutput:
        """Challenge the provided analysis using chat interface."""
    
        if not agent_input.previous_outputs:
            raise ValueError("DevilsAdvocate needs previous analysis to challenge")
        
        latest_analysis = agent_input.get_latest_output()
        
        # Build conversation for challenging
        conversation = [
            self.client.create_message("system", self.system_prompt),
            self.client.create_message("user", f"Challenge this analysis:\n\n{latest_analysis.content}")
        ]
        
        # Use the inherited chat method
        return await self.chat(conversation)
