from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

import yaml
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
    """Configuration for parameter exploration and basic scoring."""
    parameters: dict[str, list]
    constraints: list[Constraint] = []
    
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
            ]
        )

class SegmentBuilderConfig(BaseModel):
    """Configuration for SegmentBuilder parameters."""
    num_segments: int = 3
    segment_method: str = "kmeans"
    pca_method: str = 'kaiser'
    random_state: int = 10
    max_outcomes_per_component: int = 1
    max_cross_loading: float = 0.30
    min_primary_loading: float = 0.35
    top_box_threshold: int = 4


class SelectionRulesConfig(BaseModel):
    """Configuration for final segmentation selection."""
    min_segment_size_percent: float = 10.0
    min_silhouette: float = 0.25
    silhouette_weight: float = 0.6
    balance_weight: float = 0.4

class ZoneClassificationRules(BaseModel):
    opportunity_threshold: float = 10.0   
    importance_threshold: float = 60.0    
    satisfaction_threshold: float = 50.0

class StrategyQuestion(BaseModel):
    """A viability question for a strategy."""
    id: str
    text: str

class StrategyDefinition(BaseModel):
    """Definition of a single strategy."""
    description: str
    conditions: list[str] = []  # e.g. ["has_underserved", "has_overserved"]
    questions: list[StrategyQuestion] = []
    default: bool = False  # sustaining is default when nothing else

class StrategyConfig(BaseModel):
    """Configuration for strategy assignment."""
    strategies: dict[str, StrategyDefinition] = {}
    
    def get_possible(self, has_underserved: bool, has_overserved: bool) -> list[str]:
        """Return strategies whose conditions are met."""
        possible = []
        for name, defn in self.strategies.items():
            if defn.default:
                continue
            
            meets_conditions = True
            for cond in defn.conditions:
                if cond == "has_underserved" and not has_underserved:
                    meets_conditions = False
                elif cond == "has_overserved" and not has_overserved:
                    meets_conditions = False
            
            if meets_conditions:
                possible.append(name)
        
        return possible if possible else [self.get_default()]
    
    def get_default(self) -> str:
        """Return the default strategy name."""
        for name, defn in self.strategies.items():
            if defn.default:
                return name
        return "sustaining"


class RulesConfig(BaseModel):
    """Comprehensive ODI business rules configuration."""
    metadata: dict = {}
    orchestration: OrchestrationConfig
    selection_rules: SelectionRulesConfig
    zone_rules: ZoneClassificationRules
    strategies: StrategyConfig = None
    
    @classmethod
    def from_file(cls, path: str) -> RulesConfig:
        """Load complete rules configuration from YAML or JSON file."""
        file_path = Path(path)
        
        with open(file_path, 'r') as f:
            if file_path.suffix.lower() in ['.yml', '.yaml']:
                data = yaml.safe_load(f)
            else:
                data = json.load(f)
        
        # Extract sections, use defaults if missing
        orchestration_data = data.get('orchestration', {})
        selection_rules_data = data.get('selection_rules', {}) 
        zone_rules_data = data.get('zone_classification', {})
        strategies_data = data.get('strategies', {})

        # Parse strategies if present
        strategies = None
        if strategies_data:
            strategies = StrategyConfig(strategies={
            name: StrategyDefinition(**defn) 
            for name, defn in strategies_data.items()
        })
        
        return cls(
            metadata=data.get('metadata', {}),
            orchestration=OrchestrationConfig(**orchestration_data) if orchestration_data else OrchestrationConfig.default(),
            selection_rules=SelectionRulesConfig(**selection_rules_data) if selection_rules_data else SelectionRulesConfig(),
            zone_rules = ZoneClassificationRules(**zone_rules_data) if zone_rules_data else ZoneClassificationRules(),
            strategies=strategies
        )
    
    @classmethod 
    def default(cls) -> RulesConfig:
        """Create default rules configuration."""
        return cls(
            metadata={'version': '1.0.0', 'description': 'Default SODA rules'},
            orchestration=OrchestrationConfig.default(),
            selection_rules=SelectionRulesConfig()
        )


# Legacy support for existing code
def load_orchestration_config(path: str) -> OrchestrationConfig:
    """Legacy function for backward compatibility."""
    rules = RulesConfig.from_file(path)
    return rules.orchestration