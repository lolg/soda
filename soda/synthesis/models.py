from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel

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

class AgentInput(BaseModel):
    """Input to an agent."""
    segments: SegmentModelWithAssignments
    context: BusinessContext

class AgentOutput(BaseModel):
    """Output from an agent."""
    agent_name: str
    content: str
    confidence: float
    timestamp: datetime = datetime.now()