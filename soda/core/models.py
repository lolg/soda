"""Core models and data structures for segmentation and zone analysis."""

from enum import StrEnum
from typing import Any, Dict, List, Optional

import pandas as pd
from pydantic import BaseModel, ConfigDict, model_validator


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
    description: Optional[str] = None  # Added for enrichment
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
    demographics: Optional[dict] = None

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

class Outcome(BaseModel):
    id: int
    text: str

    @model_validator(mode="after")
    def _nonempty_text(self):
        if not self.text.strip():
            raise ValueError("Outcome text cannot be empty")
        return self

class Outcomes(BaseModel):
    """Outcome definitions lookup."""
    outcomes: list[Outcome]
    
    def get_text(self, outcome_id: int) -> str:
        """Get text for an outcome ID."""
        for o in self.outcomes:
            if o.id == outcome_id:
                return o.text
        raise ValueError(f"Outcome {outcome_id} not found")
    
    def to_dict(self) -> dict[int, str]:
        """Get outcome_id -> text mapping."""
        return {o.id : o.text for o in self.outcomes}


class Respondent(BaseModel):
    """Individual survey respondent with demographics."""
    model_config = ConfigDict(extra='allow')  # Handles D1, D2, D3, etc.
    
    respondentId: int  # Changed to int to match your format
    # No segment_id needed - demographics go in segments, not respondents
    
    # D1, D2, D3, D4, D5, etc. will be captured as extra fields (int values)

class Respondents(BaseModel):
    """Collection of survey respondents."""
    respondents: list[Respondent]
    
    def to_dataframe(self) -> pd.DataFrame:
        """Convert to DataFrame for processing."""
        return pd.DataFrame([r.model_dump() for r in self.respondents])
    
    @classmethod
    def from_dataframe(cls, df: pd.DataFrame) -> 'Respondents':
        """Create from DataFrame."""
        respondents = [Respondent(**row.to_dict()) for _, row in df.iterrows()]
        return cls(respondents=respondents)
    
    def get_respondent(self, respondent_id: int) -> Respondent:
        """Get respondent by ID."""
        for r in self.respondents:
            if r.respondentId == respondent_id:
                return r
        raise ValueError(f"Respondent {respondent_id} not found")
    
    def __len__(self) -> int:
        """Number of respondents."""
        return len(self.respondents)
    
    def get_demographic_values(self, dimension: str) -> list[Any]:
        """Get all values for a specific demographic dimension."""
        values = []
        for respondent in self.respondents:
            respondent_dict = respondent.model_dump()
            if dimension in respondent_dict:
                values.append(respondent_dict[dimension])
        return values

class SegmentAssignmentsMap(BaseModel):
    """Maps segment IDs to respondent IDs."""
    assignments: dict[str, list[int]]  # segment_id -> [respondent_ids]
    
    def get_respondents(self, segment_id: int) -> list[int]:
        """Get respondent IDs for a segment."""
        return self.assignments.get(str(segment_id), [])

class SegmentModelWithAssignments(BaseModel):
    """Complete segment output with optional assignments."""
    segments: list[Segment]  # No respondent_ids field
    segment_assignments: Optional[SegmentAssignmentsMap] = None

class DimensionDefinition(BaseModel):
    """Definition of a single demographic dimension."""
    id: str
    name: str
    text: Optional[str] = None
    type: str  # "categorical", "text", etc.
    options: Optional[dict[str, str]] = None  # code -> label mapping  
    missing_codes: Optional[list[str]] = None

    @model_validator(mode="after")
    def _validate_categorical(self):
        """Ensure categorical dimensions have options."""
        if self.type == "categorical" and not self.options:
            raise ValueError(f"Categorical dimension {self.name} must have options")
        return self

class Codebook(BaseModel):
    """Complete codebook with all dimension definitions."""
    dimensions: list[DimensionDefinition]
    
    def get_dimension(self, name: str) -> DimensionDefinition:
        """Get dimension by name."""
        for dim in self.dimensions:
            if dim.name == name:
                return dim
        raise ValueError(f"Dimension {name} not found")
    
    def get_categorical_dimensions(self) -> list[DimensionDefinition]:
        """Get only categorical dimensions."""
        return [dim for dim in self.dimensions if dim.type == "categorical"]

class BusinessContext(BaseModel):
    """Business context for strategic decision making."""
    business_type: str
    budget: str
    timeline: str
    team_size: int
    constraints: List[str] = []
    priorities: Dict[str, str] = {}
    market_context: Optional[Dict[str, Any]] = None