"""Tools for synthesis agent."""

from llama_index.core.tools import FunctionTool

from .state import SynthesisState


def get_segment_details(state: SynthesisState, segment_id: int) -> dict:
    """Get detailed info about a segment. Standalone for direct use."""
    seg = state.get_segment(segment_id)
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


def create_naming_tools(state: SynthesisState) -> list[FunctionTool]:
    """Tools available during naming phase."""
    
    def _get_segment_details(segment_id: int) -> dict:
        """Get detailed information about a segment including demographics and outcomes."""
        return get_segment_details(state, segment_id)
    
    def record_segment_name(segment_id: int, name: str) -> str:
        """Record the chosen name for a segment after user confirms."""
        state.set_name(segment_id, name)

        print("recording segment name:", name)

        return f"Recorded name '{name}' for segment {segment_id}"
    
    return [
        FunctionTool.from_defaults(fn=_get_segment_details, name="get_segment_details"),
        FunctionTool.from_defaults(fn=record_segment_name, name="record_segment_name", description="Records the chosen name for a segment after user confirms."),
    ]


def create_strategy_tools(state: SynthesisState) -> list[FunctionTool]:
    """Tools available during strategy phase."""
    
    def _get_segment_details(segment_id: int) -> dict:
        """Get detailed information about a segment including demographics and outcomes."""
        return get_segment_details(state, segment_id)
    
    def record_viability_answer(segment_id: int, question_id: str, answer: bool) -> str:
        """Record answer to a viability question."""
        state.set_viability_answer(segment_id, question_id, answer)
        return f"Recorded {question_id}={answer} for segment {segment_id}"
    
    def record_segment_strategy(segment_id: int, strategy: str) -> str:
        """Record the chosen strategy for a segment."""
        state.set_strategy(segment_id, strategy)
        return f"Recorded strategy '{strategy}' for segment {segment_id}"
    
    return [
        FunctionTool.from_defaults(fn=_get_segment_details, name="get_segment_details"),
        FunctionTool.from_defaults(fn=record_viability_answer, name="record_viability_answer"),
        FunctionTool.from_defaults(fn=record_segment_strategy, name="record_segment_strategy"),
    ]