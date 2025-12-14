"""Orchestration engine for running and evaluating segmentation experiments."""

import math
from itertools import product
from typing import Iterator

from juno.core.config import OrchestrationConfig
from juno.core.models import SegmentationMetrics
from juno.core.segment_builder import SegmentBuilder


def score_config(metrics: SegmentationMetrics, weights: dict[str, float]) -> float:
    """Score a configuration based on existing metrics."""
    
    # Normalize silhouette (0 to 1 scale, where 0.5 is excellent)
    silhouette_score = min(metrics.silhouette_mean / 0.5, 1.0)
    
    # Balance score: penalize imbalance
    sizes = metrics.cluster_sizes_pct
    max_size = max(sizes)
    min_size = min(sizes)
    balance_score = 1.0 - ((max_size - min_size) / 100.0)
    
    # Weighted combination
    total_score = (
        silhouette_score * weights.get('silhouette_weight', 0.6) +
        balance_score * weights.get('balance_weight', 0.4)
    )
    
    return total_score


class Orchestrator:
    """Run and score multiple configurations."""
    
    def __init__(self, config: OrchestrationConfig):
        self.config = config
    
    def count_configs(self) -> int:
        """Count total number of configs (before filtering)."""
        param_values = [self.config.parameters[name] for name in self.config.parameters]
        return math.prod(len(values) for values in param_values)
    
    def _is_valid_config(self, kwargs: dict) -> bool:
        """Check if parameter combination satisfies all constraints."""
        return all(constraint.check(kwargs) for constraint in self.config.constraints)
    
    def _get_valid_configs(self) -> list[dict]:
        """Generate all valid parameter combinations."""
        params = self.config.parameters
        param_names = list(params.keys())
        param_values = [params[name] for name in param_names]
        
        # Generate all combinations
        all_combos = list(product(*param_values))
        
        # Filter valid combinations
        valid_combos = []
        for combo in all_combos:
            kwargs = dict(zip(param_names, combo))
            if self._is_valid_config(kwargs):
                valid_combos.append(kwargs)
        
        return valid_combos
    
    def get_valid_config_count(self) -> int:
        """Get count of valid configurations after filtering."""
        return len(self._get_valid_configs())
    
    def run(self, responses_df) -> Iterator[dict]:
        """
        Run all valid parameter combinations.
        
        Yields results one at a time for progress tracking.
        
        Yields:
            dict: Result containing params, analyzer, metrics, score
        """
        valid_configs = self._get_valid_configs()
        
        for kwargs in valid_configs:
            # Run analysis
            segmenter = SegmentBuilder(**kwargs)
            segmenter.fit(responses_df)
            
            # Score
            score = score_config(segmenter.metrics, self.config.scoring)
            
            yield {
                'params': kwargs,
                'analyzer': segmenter,
                'metrics': segmenter.metrics,
                'score': score
            }
    
    def run_all(self, responses_df) -> list[dict]:
        """
        Run all configs and return sorted results.
        
        Returns:
            list[dict]: All results sorted by score (highest first)
        """
        results = list(self.run(responses_df))
        results.sort(key=lambda x: x['score'], reverse=True)
        return results
    
    def get_best(self, responses_df) -> dict:
        """Run all configs and return best result."""
        results = self.run_all(responses_df)
        return results[0]

    def get_best_per_segment_count(self, responses_df) -> dict[int, dict]:
        """
        Run all configs and return best result for each segment count.
        
        Returns:
            dict[int, dict]: Mapping of num_segments -> best result for that count
        """
        results = self.run_all(responses_df)
        
        best_per_k = {}
        for result in results:
            k = result['params']['num_segments']
            if k not in best_per_k:
                best_per_k[k] = result
            # Already sorted by score, so first seen is best
        
        return best_per_k