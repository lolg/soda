"""Tools for synthesis agent."""

from llama_index.core.tools import FunctionTool

from .state import SynthesisState


def create_tools(state: SynthesisState) -> list[FunctionTool]:
    """Create tools bound to synthesis state."""
    
    def get_segments_summary() -> str:
        """Get overview of all segments including size and outcome distribution."""
        return state.get_summary()
    
    def get_synthesis_progress() -> dict:
        """Check what's been completed and what still needs to be done."""
        return state.get_progress()
    
    def record_segment_name(segment_id: int, name: str) -> str:
        """Record the chosen name for a segment. Call this after user confirms a name."""
        state.set_name(segment_id, name)
        return f"Recorded name '{name}' for segment {segment_id}"

    def get_segment_details(segment_id: int) -> dict:
        """Get detailed information about a specific segment including demographics and key outcomes."""
        seg = state.get_segment(segment_id)  
        
        return {
            "segment_id": segment_id,
            "size_pct": seg.size_pct,
            "demographics": seg.demographics or {},
            "underserved_outcomes": [
                {"id": o.outcome_id, "description": o.description}
                for o in seg.zones.underserved.outcomes[:5]  # top 5
            ],
            "overserved_outcomes": [
                {"id": o.outcome_id, "description": o.description}
                for o in seg.zones.overserved.outcomes[:5]
            ],
        }
    
    return [
        FunctionTool.from_defaults(
            fn=get_segments_summary,
            name="get_segments_summary",
            description="Get overview of all segments including size and outcome distribution."
        ),
        FunctionTool.from_defaults(
            fn=get_synthesis_progress,
            name="get_synthesis_progress",
            description="Check what's been completed and what still needs to be done. Returns completed segments and remaining work."
        ),
        FunctionTool.from_defaults(
            fn=record_segment_name,
            name="record_segment_name",
            description="Record the chosen name for a segment after user confirms. Args: segment_id (int), name (str)"
        ),
         FunctionTool.from_defaults(
            fn=get_segment_details,
            name="get_segment_details",
            description="Get detailed information about a specific segment including demographics and key outcomes"
        )
    ]