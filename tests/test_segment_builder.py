import pandas as pd
import pytest

from juno.core.schema import DataKey, importance_col, satisfaction_col
from juno.core.segment_builder import SegmentBuilder


def make_responses(n_respondents=10, n_outcomes=3):
    """Generate test response data."""
    data = {DataKey.RESPONDENT_ID: list[int](range(1, n_respondents + 1))}
    
    # Base pattern to repeat
    sat_pattern = [3, 4, 5, 2, 4]
    imp_pattern = [4, 5, 3, 5, 4]
    
    # Add satisfaction and importance for each outcome
    for i in range(1, n_outcomes + 1):
        # Repeat pattern and truncate to exact length
        sat_values = (sat_pattern * (n_respondents // len(sat_pattern) + 1))[:n_respondents]
        imp_values = (imp_pattern * (n_respondents // len(imp_pattern) + 1))[:n_respondents]
        
        data[satisfaction_col(i)] = sat_values
        data[importance_col(i)] = imp_values
    
    return pd.DataFrame(data)


def test_segment_builder_basic():
    """Test basic segmentation workflow."""
    responses = make_responses(n_respondents=20, n_outcomes=5)
    
    builder = SegmentBuilder(num_segments=3, random_state=42)
    builder.fit(responses)
    
    # Test model structure
    model = builder.model 
    assert len(model.segments) == 3
    
    # Each segment has outcomes
    for segment in model.segments:
        assert len(segment.outcomes) == 5  # n_outcomes
        assert 0 < segment.size_pct <= 100
        
        # Each outcome has metrics
        for outcome in segment.outcomes:
            assert outcome.outcome_id in range(1, 6)
            assert 0 <= outcome.sat_tb <= 100
            assert 0 <= outcome.imp_tb <= 100


def test_segment_builder_assignments():
    """Test segment assignments are consistent."""
    responses = make_responses(n_respondents=20, n_outcomes=5)
    
    builder = SegmentBuilder(num_segments=3, random_state=42)
    builder.fit(responses)
    
    assignments = builder.assignments
    
    # All respondents assigned
    assert len(assignments.assignments) == 20
    
    # Segment sizes match
    sizes = assignments.segment_sizes()
    assert len(sizes) == 3
    assert sum(sizes.values()) == 20
    
    # No duplicate assignments
    assert len(set(assignments.assignments.values())) <= 3


def test_segment_builder_metrics():
    """Test segmentation quality metrics."""
    responses = make_responses(n_respondents=20, n_outcomes=5)
    
    builder = SegmentBuilder(num_segments=3, random_state=42)
    builder.fit(responses)
    
    metrics = builder.metrics
    
    assert metrics.k == 3
    assert metrics.method == "kmeans"
    assert -1 <= metrics.silhouette_mean <= 1
    assert len(metrics.silhouette_by_cluster) == 3
    assert len(metrics.cluster_sizes_pct) == 3
    assert sum(metrics.cluster_sizes_pct) == pytest.approx(100, abs=0.1)


def test_segment_builder_validation():
    """Test input validation."""
    # Too few respondents
    responses = make_responses(n_respondents=2, n_outcomes=3)
    builder = SegmentBuilder(num_segments=3)
    
    with pytest.raises(ValueError, match="Need at least 3 respondents"):
        builder.fit(responses)
    
    # Empty DataFrame
    with pytest.raises(ValueError, match="cannot be empty"):
        builder.fit(pd.DataFrame())


def test_segment_builder_not_fitted():
    """Test accessing results before fitting raises error."""
    builder = SegmentBuilder(num_segments=3)
    
    with pytest.raises(ValueError, match="not fitted"):
        _ = builder.model
    
    with pytest.raises(ValueError, match="not fitted"):
        _ = builder.assignments
    
    with pytest.raises(ValueError, match="not fitted"):
        _ = builder.metrics