from soda.synthesis.agents.data_analyst import DataAnalystAgent
from soda.synthesis.clients.factory import ClientFactory
from soda.synthesis.config import SynthesisConfig


class AgentFactory:
    """Create agents from YAML config."""
    
    def __init__(self, config: SynthesisConfig):
        self.config = config
    
    def create_data_analyst(self) -> DataAnalystAgent:
        """Create data analyst agent from config."""
        
        agent_config = self.config.synthesis.agents["data_analyst"]
        provider_config = self.config.synthesis.providers[agent_config.provider]
        
        client = ClientFactory.create_client(provider_config, agent_config)
        return DataAnalystAgent(client, agent_config)