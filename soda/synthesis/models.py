from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from soda.core.models import SegmentModelWithAssignments


class BusinessContext(BaseModel):
    """Business context for strategic decision making."""
    business_type: str
    budget: str
    timeline: str
    team_size: int
    constraints: List[str] = []
    priorities: Dict[str, str] = {}
    market_context: Optional[Dict[str, Any]] = None

class AgentOutput(BaseModel):
    """Output from an agent."""
    agent_name: str
    content: str
    confidence: float
    timestamp: datetime = datetime.now()    

class AgentInput(BaseModel):
    """Input to an agent."""
    segments: SegmentModelWithAssignments
    context: BusinessContext
    previous_outputs: List[AgentOutput] = Field(default_factory=list)
    
    def add_previous_output(self, output: AgentOutput) -> None:
        """Add an agent output to the conversation history."""
        self.previous_outputs.append(output)
    
    def get_latest_output(self) -> Optional[AgentOutput]:
        """Get the most recent output."""
        if not self.previous_outputs:
            return None
        return self.previous_outputs[-1]