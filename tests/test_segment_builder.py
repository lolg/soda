import pandas as pd

from soda.core.config import ZoneClassificationRules
from soda.core.schema import DataKey, importance_col, satisfaction_col
from soda.core.segment_builder import SegmentBuilder, SegmentBuilderConfig
from soda.core.models import ZoneType


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

    config = SegmentBuilderConfig()
    config.num_segments = 3

    rules = ZoneClassificationRules()
    
    builder = SegmentBuilder(config, rules)
    builder.fit(responses)
    
    # Test model structure
    model = builder.model 
    assert len(model.segments) == 3
    
    # Each segment has outcomes
    for segment in model.segments:

        assert segment.zones.total_outcomes() == 5
        assert 0 < segment.size_pct <= 100
        
        assert segment.size_pct in range(0, 100)
        assert segment.zones.get_total_outcomes_by_zone(ZoneType.UNDERSERVED) in range(0, 6)
        assert segment.zones.get_total_outcomes_by_zone(ZoneType.OVERSERVED) in range(0, 6)
        assert segment.zones.get_total_outcomes_by_zone(ZoneType.TABLE_STAKES) in range(0, 6)
        assert segment.zones.get_total_outcomes_by_zone(ZoneType.APPROPRIATELY_SERVED) in range(0, 6)
