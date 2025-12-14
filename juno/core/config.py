"""Definitions for configuration settings for the API and application."""

from __future__ import annotations

import json
from typing import Literal

from pydantic import BaseModel


class Constraint(BaseModel):
    """Defines a constraint on parameter combinations for orchestration search."""
    type: Literal["less_than", "greater_than", "not_equal"]
    left: str
    right: str
    
    def check(self, kwargs: dict) -> bool:
        """Check if constraint is satisfied."""
        if self.left not in kwargs or self.right not in kwargs:
            return True  # Can't check, assume valid
        
        left_val = kwargs[self.left]
        right_val = kwargs[self.right]
        
        if self.type == "less_than":
            return left_val < right_val
        elif self.type == "greater_than":
            return left_val > right_val
        elif self.type == "not_equal":
            return left_val != right_val
        
        return True


class OrchestrationConfig(BaseModel):
    """Configuration object for controlling orchestration of segmentation experiments."""
    parameters: dict[str, list]
    constraints: list[Constraint] = []
    scoring: dict[str, float]
    
    @classmethod
    def from_json(cls, path: str) -> OrchestrationConfig:
        with open(path, 'r') as f:
            data = json.load(f)
        return cls(**data)

    @classmethod
    def default(cls) -> OrchestrationConfig:
        return cls(
            parameters={
                'num_segments': [2, 3, 4],
                'max_cross_loading': [0.36, 0.40, 0.42, 0.46],
                'min_primary_loading': [0.40, 0.44, 0.48, 0.5],
                'random_state': [3, 6, 10, 12]
            },
            constraints=[
                Constraint(type='less_than', left='max_cross_loading', right='min_primary_loading')
            ],
            scoring={'silhouette_weight': 0.6, 'balance_weight': 0.4}
        )