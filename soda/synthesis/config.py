from pathlib import Path
from typing import Any, Dict

import yaml
from pydantic import BaseModel


class ProviderConfig(BaseModel):
    api_key_env: str
    default_model: str

class ModelConfig(BaseModel):
    temperature: float
    max_tokens: int

class AgentConfig(BaseModel):
    provider: str
    system_prompt: str
    user_prompt: str
    llm_config: ModelConfig

class SynthesisSection(BaseModel):
    providers: Dict[str, ProviderConfig]
    agents: Dict[str, AgentConfig]

class SynthesisConfig(BaseModel):
    metadata: Dict[str, Any]
    synthesis: SynthesisSection
    
    @classmethod
    def from_file(cls, config_path: Path) -> 'SynthesisConfig':
        """Load synthesis config from YAML file."""
        with open(config_path, 'r') as f:
            data = yaml.safe_load(f)
        return cls(**data)