"""High-level naming API."""

import asyncio
from typing import Callable

from llama_index.core.agent import ReActAgent
from llama_index.core.tools import FunctionTool
from llama_index.llms.anthropic import Anthropic
from pydantic import BaseModel

from soda.core.models import SegmentModelWithAssignments, Segment


class NameSuggestions(BaseModel):
    summary: str
    options: list[str]

SYSTEM_PROMPT = """You are an expert in Outcome-Driven Innovation (ODI) and Jobs-to-be-Done (JTBD) methodology.

You help product teams analyze market segments based on customer outcome data. You understand:
- Underserved outcomes indicate opportunity for differentiation
- Overserved outcomes indicate potential for disruption or cost reduction
- Segment demographics help characterize who the customers are
- Good segment names capture the essence of who they are or what they need
"""

NAMING_PROMPT = """You are naming market segments. Work through ALL unnamed segments.

For each unnamed segment:
1. Call get_segments_overview to see which need naming
2. Call get_segment_details for the segment
3. Call request_user_choice - this is REQUIRED to get user input
4. Call record_segment_name with the returned name

You MUST call request_user_choice to present options to the user. Do not output suggestions directly.

Continue until all segments are named."""


def get_segment_details(segment_model: SegmentModelWithAssignments, segment_id: int) -> dict:
    """Get detailed info about a segment."""
    seg = next(s for s in segment_model.segments if s.segment_id == segment_id)
    return {
        "segment_id": segment_id,
        "size_pct": seg.size_pct,
        "demographics": seg.demographics or {},
        "underserved_outcomes": [
            {"id": o.outcome_id, "description": o.description}
            for o in seg.zones.underserved.outcomes[:5]
        ],
        "overserved_outcomes": [
            {"id": o.outcome_id, "description": o.description}
            for o in seg.zones.overserved.outcomes[:5]
        ],
    }


def create_naming_tools(
    segment_model: SegmentModelWithAssignments,
    on_input: Callable[[NameSuggestions, Segment], str]
) -> list[FunctionTool]:
    """Tools for naming phase."""
    
    def get_segments_overview() -> dict:
        """Get overview of all segments - which need naming."""
        return {
            "total_segments": len(segment_model.segments),
            "segments": [
                {
                    "id": s.segment_id,
                    "size_pct": s.size_pct,
                    "name": s.name,
                    "needs_naming": s.name is None
                }
                for s in segment_model.segments
            ]
        }
    
    def get_segment_details(segment_id: int) -> dict:
        """Get detailed information about a segment."""
        seg = next(s for s in segment_model.segments if s.segment_id == segment_id)
        return {
            "segment_id": segment_id,
            "size_pct": seg.size_pct,
            "demographics": seg.demographics or {},
            "underserved_outcomes": [
                {"id": o.outcome_id, "description": o.description}
                for o in seg.zones.underserved.outcomes[:5]
            ],
            "overserved_outcomes": [
                {"id": o.outcome_id, "description": o.description}
                for o in seg.zones.overserved.outcomes[:5]
            ],
        }
    
    def request_user_choice(segment_id: int, summary: str, options: list[str]) -> str:
        """Present naming options to user and get their choice."""
        suggestions = NameSuggestions(summary=summary, options=options)
        segment = next(s for s in segment_model.segments if s.segment_id == segment_id)
        choice = on_input(suggestions, segment)
        
        # Resolve choice to name
        if choice.isdigit() and 1 <= int(choice) <= len(options):
            return options[int(choice) - 1]
        return choice
    
    def record_segment_name(segment_id: int, name: str) -> str:
        """Record the chosen name for a segment."""
        seg = next(s for s in segment_model.segments if s.segment_id == segment_id)
        seg.name = name
        return f"Recorded name '{name}' for segment {segment_id}"
    
    return [
        FunctionTool.from_defaults(
            fn=get_segments_overview, 
            name="get_segments_overview",
            description="Get overview of all segments showing which need naming"
        ),
        FunctionTool.from_defaults(
            fn=get_segment_details, 
            name="get_segment_details",
            description="Get detailed info about a segment including demographics and outcomes"
        ),
        FunctionTool.from_defaults(
            fn=request_user_choice, 
            name="request_user_choice",
            description="REQUIRED: Present naming options to user and get their choice. Args: segment_id (int), summary (str), options (list of 3 name strings). Returns the chosen name."
        ),
        FunctionTool.from_defaults(
            fn=record_segment_name, 
            name="record_segment_name",
            description="Record the final chosen name for a segment"
        ),
    ]


async def _name_async(
    segment_model: SegmentModelWithAssignments,
    on_input: Callable[[NameSuggestions, Segment], str]
) -> SegmentModelWithAssignments:
    """Name all unnamed segments - agent controls the loop."""
    
    # Check if any need naming
    unnamed = [s for s in segment_model.segments if s.name is None]
    if not unnamed:
        print("All segments already named. Nothing to do.")
        return segment_model
    
    print(f"{len(unnamed)} segment(s) need naming...")

    llm = Anthropic(model="claude-sonnet-4-20250514")
    tools = create_naming_tools(segment_model, on_input)
    
    agent = ReActAgent(
        tools=tools,
        llm=llm,
        system_prompt=SYSTEM_PROMPT + "\n\n" + NAMING_PROMPT
        )
    
    response = await agent.run(user_msg="Name all unnamed segments")
    print(f"Agent response: {response}")

    return segment_model

def name(
    segment_model: SegmentModelWithAssignments,
    on_input: Callable[[NameSuggestions, Segment], str]
) -> SegmentModelWithAssignments:
    """Name unnamed segments. Sync wrapper."""
    return asyncio.run(_name_async(segment_model, on_input))