"""Events for synthesis workflow."""

from llama_index.core.workflow import Event


class NamingPhaseEvent(Event):
    """Start naming phase for a segment."""
    segment_id: int


class SynthesisCompleteEvent(Event):
    """All segments processed."""
    pass