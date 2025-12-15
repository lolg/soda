"""Orchestration engine for running segmentation experiments."""

import math
from itertools import product
from typing import Iterator

from soda.core.config import OrchestrationConfig, SegmentBuilderConfig
from soda.core.segment_builder import SegmentBuilder


class Orchestrator:
    """Run multiple segmentation parameter combinations."""
    
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
    
    def _create_segment_builder_config(self, orchestration_params: dict) -> SegmentBuilderConfig:
        """
        Create SegmentBuilderConfig from orchestration parameters.
        
        Maps orchestration params to SegmentBuilderConfig, using defaults for non-varying params.
        """
        # Start with default config
        config_dict = SegmentBuilderConfig().model_dump()
        
        # Override with orchestration parameters
        config_dict.update(orchestration_params)
        
        return SegmentBuilderConfig(**config_dict)
    
    def get_valid_config_count(self) -> int:
        """Get count of valid configurations after filtering."""
        return len(self._get_valid_configs())
    
    def run(self, responses_df) -> Iterator[dict]:
        """
        Run all valid parameter combinations.
        
        Yields results one at a time for progress tracking.
        
        Yields:
            dict: Result containing config, analyzer, metrics
        """
        valid_configs = self._get_valid_configs()
        
        for orchestration_params in valid_configs:
            # Create SegmentBuilderConfig from orchestration parameters
            segment_config = self._create_segment_builder_config(orchestration_params)
            
            # Run analysis with config object
            segmenter = SegmentBuilder(segment_config)
            segmenter.fit(responses_df)
            
            yield {
                'config': segment_config,           # Full config object
                'params': orchestration_params,     
                'metrics': segmenter.metrics        # Results for evaluation
            }
    
    def run_all(self, responses_df) -> list[dict]:
        """
        Run all configs and return all results.
        
        Returns:
            list[dict]: All results (no sorting, no filtering)
        """
        return list(self.run(responses_df))