"""SegmentationSelector for selecting the best solution."""

from typing import Dict, List

from soda.core.config import SelectionRulesConfig
from soda.core.models import SegmentationMetrics


class SegmentationSelector:
    """Filter and select best segmentation configuration from orchestrator results."""
    
    def __init__(self, selection_config: SelectionRulesConfig):
        """
        Args:
            selection_config: SelectionRulesConfig from YAML
        """
        self.config = selection_config
    
    def _score_config(self, metrics: SegmentationMetrics) -> float:
        """Score using proven silhouette + balance formula."""
        # Normalize silhouette (0 to 1 scale, where 0.5 is excellent)
        silhouette_score = min(metrics.silhouette_mean / 0.5, 1.0)
        
        # Balance score: penalize imbalance
        sizes = metrics.cluster_sizes_pct
        balance_score = 1.0 - ((max(sizes) - min(sizes)) / 100.0)
        
        # Weighted combination
        return (silhouette_score * self.config.silhouette_weight +
                balance_score * self.config.balance_weight)
    
    def select_best(self, all_results: List[Dict]) -> Dict:
        """Filter by hard constraints, then select best by scoring."""
        # Filter: apply hard constraints
        viable = [r for r in all_results 
                 if (min(r['metrics'].cluster_sizes_pct) >= self.config.min_segment_size_percent and 
                     r['metrics'].silhouette_mean >= self.config.min_silhouette)]
        
        if not viable:
            raise ValueError("No configurations meet constraints")
        
        # Rank: weighted scoring
        return max(viable, key=lambda r: self._score_config(r['metrics']))