"""Synthesis workflow for segment naming."""

from llama_index.core.agent.workflow import AgentWorkflow
from llama_index.core.workflow import (
    Context,
    HumanResponseEvent,
    InputRequiredEvent,
    StartEvent,
    StopEvent,
    Workflow,
    step,
)
from llama_index.llms.anthropic import Anthropic

from .events import NamingPhaseEvent, SynthesisCompleteEvent
from .models import NameSuggestions
from .state import SynthesisState
from .tools import create_naming_tools

NAMING_PROMPT = """You are naming a market segment based on its characteristics.

1. Call get_segment_details to understand the segment
2. Respond with a JSON object containing your suggestions:
```json
{
  "summary": "Brief description of the segment",
  "options": ["Name Option 1", "Name Option 2", "Name Option 3"]
}
```

3. Wait for user to choose
4. Record the chosen name with record_segment_name

Keep names concise (2-4 words). Base them on WHO these people are or WHAT they need.
Always respond with valid JSON when presenting options."""


class SynthesisWorkflow(Workflow):
    """Workflow for naming segments."""
    
    def __init__(self, state: SynthesisState, **kwargs):
        super().__init__(**kwargs)
        self.state = state
        self.llm = Anthropic(model="claude-sonnet-4-20250514")
    
    @step
    async def start(self, ctx: Context, ev: StartEvent) -> NamingPhaseEvent | SynthesisCompleteEvent:
        """Begin with first segment that needs naming."""
        for seg in self.state.segments:
            if seg.segment_id not in self.state.names:
                return NamingPhaseEvent(segment_id=seg.segment_id)
        
        return SynthesisCompleteEvent()
    
    @step
    async def naming_phase(self, ctx: Context, ev: NamingPhaseEvent) -> InputRequiredEvent:
        """Run naming agent for a segment."""
        tools = create_naming_tools(self.state)
        
        agent = AgentWorkflow.from_tools_or_functions(
            tools_or_functions=tools,
            llm=self.llm,
            system_prompt=NAMING_PROMPT,
            output_cls=NameSuggestions
        )
        
        response = await agent.run(user_msg=f"Name segment {ev.segment_id}")
        
        suggestions: NameSuggestions = response.get_pydantic_model(NameSuggestions)
    
        self.state.pending = suggestions
        self._segment_id = ev.segment_id
        self._agent = agent
    
        return InputRequiredEvent(prefix="")
    
    @step
    async def handle_response(self, ctx: Context, ev: HumanResponseEvent) -> NamingPhaseEvent | SynthesisCompleteEvent | InputRequiredEvent:
        """Send choice to agent, let it record."""
        segment_id = self._segment_id
        agent = self._agent
        suggestions = self.state.pending
        
        # Resolve choice to name
        choice = ev.response.strip()
        if choice.isdigit() and 1 <= int(choice) <= len(suggestions.options):
            name = suggestions.options[int(choice) - 1]
        else:
            name = choice
        
        # Tell agent the choice - it will call record_segment_name
        await agent.run(user_msg=f"The user chose '{name}' for segment {segment_id}. Call record_segment_name with segment_id={segment_id} and name='{name}'.")
        
        # Check if name was recorded
        if segment_id in self.state.names:
            for seg in self.state.segments:
                if seg.segment_id not in self.state.names:
                    return NamingPhaseEvent(segment_id=seg.segment_id)
            return SynthesisCompleteEvent()
    
    @step
    async def complete(self, ctx: Context, ev: SynthesisCompleteEvent) -> StopEvent:
        """All segments named."""
        return StopEvent(result=self.state.to_dict())