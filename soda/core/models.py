"""Core models and data structures for segmentation and zone analysis."""

from enum import StrEnum
from typing import List

from pydantic import BaseModel


class ZoneType(StrEnum):
    UNDERSERVED = "UNDER"
    OVERSERVED = "OVER"
    TABLE_STAKES = "TABLE"
    APPROPRIATELY_SERVED = "APPROP"

class SegmentOutcome(BaseModel):
    """
    Represents a single outcome for a segment, including Top-Box metrics and
    opportunity score.
    """
    outcome_id: int
    sat_tb: float
    imp_tb: float
    opportunity: float
    zone: ZoneType

class ZoneOutcome(BaseModel):
    """Outcome data within a zone (no zone field needed since placement indicates zone)."""
    outcome_id: int
    sat_tb: float
    imp_tb: float
    opportunity: float

class ZoneCategory(BaseModel):
    """A zone category with percentage and outcomes."""
    pct: float
    outcomes: List[ZoneOutcome]

class SegmentZones(BaseModel):
    """All zone categories for a segment."""
    underserved: ZoneCategory
    overserved: ZoneCategory
    table_stakes: ZoneCategory
    appropriate: ZoneCategory

class Segment(BaseModel):
    """Represents a segment with its size and associated outcomes."""
    segment_id: int
    size_pct: float
    zones: SegmentZones

class SegmentModel(BaseModel):
    """A structured representation of all segments, each with outcomes and metrics."""
    segments: list[Segment]

    def get_segment(self, segment_id: int) -> Segment:
        """Get a segment by its ID."""
        for segment in self.segments:
            if segment.segment_id == segment_id:
                return segment
        raise ValueError(f"Segment {segment_id} not found")


class SegmentationMetrics(BaseModel):
    """
    Clustering/segmentation metrics describing the fit and properties
    of the solution.
    """
    method: str  
    k: int
    random_state: int
    silhouette_mean: float
    silhouette_by_cluster: list[float]
    cluster_sizes_pct: list[float]
    min_cluster_pct: float

class SegmentAssignments(BaseModel):
    """Maps each respondent to their segment."""
    assignments: dict[int, int]  # respondent_id -> segment_id
    
    def get_respondents(self, segment_id: int) -> list[int]:
        """Get all respondent IDs in a segment."""
        return [rid for rid, sid in self.assignments.items() if sid == segment_id]
    
    def get_segment(self, respondent_id: int) -> int:
        """Get segment for a respondent."""
        return self.assignments[respondent_id]
    
    def segment_sizes(self) -> dict[int, int]:
        """Get count of respondents per segment."""
        counts = {}
        for segment_id in self.assignments.values():
            counts[segment_id] = counts.get(segment_id, 0) + 1
        return counts
    
    def get_unique_segments(self) -> list[int]:
        """Get list of unique segment IDs."""
        return sorted(set(self.assignments.values()))