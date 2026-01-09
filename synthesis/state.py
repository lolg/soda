"""Synthesis state for tracking agent decisions."""

from soda.core.models import SegmentModelWithAssignments


class SynthesisState:
    """Holds segment data and tracks synthesis decisions.
    
    The agent reads segment data and records decisions via tools.
    This class is the shared state those tools operate on.
    """
    
    def __init__(self, segment_model: SegmentModelWithAssignments):
        self.segment_model = segment_model
        
        # Decisions tracked by segment_id
        self.names: dict[int, str] = {}
        self.viability_answers: dict[int, dict[str, bool]] = {}
        self.strategies: dict[int, str] = {}
    
    @property
    def segments(self):
        return self.segment_model.segments
    
    @property
    def num_segments(self) -> int:
        return len(self.segments)

    def get_segment(self, segment_id: int):
        """Get a specific segment by ID."""
        self._validate_segment_id(segment_id)
        for seg in self.segments:
            if seg.segment_id == segment_id:
                return seg
    
    def get_summary(self) -> str:
        """Overview of segments for agent to read."""
        lines = [f"{self.num_segments} segments:\n"]
        
        for seg in self.segments:
            zones = seg.zones
            total_outcomes = (
                len(zones.underserved.outcomes) +
                len(zones.overserved.outcomes) +
                len(zones.table_stakes.outcomes) +
                len(zones.appropriate.outcomes)
            )
            
            line = (
                f"- Segment {seg.segment_id}: "
                f"{seg.size_pct:.1f}% of respondents, "
                f"{len(zones.underserved.outcomes)} underserved, "
                f"{len(zones.overserved.outcomes)} overserved, "
                f"{total_outcomes} total outcomes"
            )
            lines.append(line)
        
        return "\n".join(lines)
    
    def get_progress(self) -> dict:
        """Check what's done and what's remaining."""
        completed = []
        remaining = []
        
        for seg in self.segments:
            sid = seg.segment_id
            status = {
                "segment_id": sid,
                "has_name": sid in self.names,
                "has_strategy": sid in self.strategies,
            }
            
            if status["has_name"] and status["has_strategy"]:
                completed.append(sid)
            else:
                remaining.append(status)
        
        return {
            "completed": completed,
            "remaining": remaining,
            "all_done": len(remaining) == 0
        }
    
    def is_complete(self) -> bool:
        """All segments named and strategy assigned."""
        return self.get_progress()["all_done"]
    
    def set_name(self, segment_id: int, name: str) -> None:
        """Record chosen name for a segment."""
        self._validate_segment_id(segment_id)
        self.names[segment_id] = name
    
    def set_strategy(self, segment_id: int, strategy: str) -> None:
        """Record chosen strategy for a segment."""
        self._validate_segment_id(segment_id)
        self.strategies[segment_id] = strategy
    
    def set_viability_answer(self, segment_id: int, question_id: str, answer: bool) -> None:
        """Record answer to a viability question."""
        self._validate_segment_id(segment_id)
        if segment_id not in self.viability_answers:
            self.viability_answers[segment_id] = {}
        self.viability_answers[segment_id][question_id] = answer
    
    def get_viability_answers(self, segment_id: int) -> dict[str, bool]:
        """Get all viability answers for a segment."""
        return self.viability_answers.get(segment_id, {})
    
    def to_dict(self) -> dict:
        """Export for synthesis.json."""
        segments_output = []
        
        for seg in self.segments:
            sid = seg.segment_id
            segments_output.append({
                "segment_id": sid,
                "name": self.names.get(sid),
                "strategy": self.strategies.get(sid),
                "viability_answers": self.viability_answers.get(sid, {}),
                "size_pct": seg.size_pct,
            })
        
        return {
            "segments": segments_output,
            "complete": self.is_complete()
        }
    
    def _validate_segment_id(self, segment_id: int) -> None:
        """Raise if segment_id doesn't exist."""
        valid_ids = [s.segment_id for s in self.segments]
        if segment_id not in valid_ids:
            raise ValueError(f"Invalid segment_id {segment_id}. Valid: {valid_ids}")
