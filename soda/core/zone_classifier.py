"""
Applies zone classification to segment outcomes
"""

from soda.core.config import ZoneClassificationRules
from soda.core.models import SegmentModel, ZoneType


class ZoneClassifier:

    def __init__(self, zone_rules: ZoneClassificationRules):
        """
        Args:
            zone_rules: ZoneClassificationRules from YAML config
        """
        self.config = zone_rules
    
    def classify_outcome(self, imp_tb: float, sat_tb: float, opportunity: float) -> ZoneType:
        """Classify single outcome using ODI methodology."""
        high_opportunity = opportunity >= self.config.opportunity_threshold
        high_importance = imp_tb >= self.config.importance_threshold
        high_satisfaction = sat_tb >= self.config.satisfaction_threshold
        
        if high_opportunity and not high_satisfaction:
            return ZoneType.UNDERSERVED
        elif high_importance and high_satisfaction:
            return ZoneType.TABLE_STAKES
        elif not high_opportunity and high_satisfaction and not high_importance:
            return ZoneType.OVERSERVED
        else:
            return ZoneType.APPROPRIATELY_SERVED
    
    def classify_segment_model(self, segment_model: SegmentModel) -> SegmentModel:
        """Apply zone classification to all outcomes in all segments."""
        for segment in segment_model.segments:
            for outcome in segment.outcomes:
                outcome.zone = self.classify_outcome(
                    outcome.imp_tb,
                    outcome.sat_tb, 
                    outcome.opportunity
                )
        
        return segment_model