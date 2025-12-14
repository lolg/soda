"""
    Input: the loading_matrix from PCA

            Outcome             |   PC1   |   PC2   |   PC3
    ----------------------------|---------|---------|---------
    OutcomeImportance_1         |  0.21   |  0.18   |  0.09
    OutcomeImportance_2         |  0.65   |  0.10   |  0.12
    OutcomeImportance_3         |  0.07   |  0.71   |  0.22
    OutcomeImportance_4         |  0.09   |  0.05   |  0.68

    Each column (PC1, PC2, PC3) represents a latent theme.
    Large absolute values mean that outcome contributes strongly to that theme.

    Goal:

    - For each component, pick one (or a few) outcomes that best represent it.
    - Avoid outcomes that load strongly on multiple components (cross-loading).

    Clean structure (good):
    PC1: "Ease of Use"     → OutcomeImportance_3 (0.72), OutcomeImportance_7 (0.68)
    PC2: "Speed/Efficiency" → OutcomeImportance_2 (0.71), OutcomeImportance_9 (0.65)

    Cross-loading (confusing):
    PC1: "Ease of Use"     → OutcomeImportance_5 (0.65), OutcomeImportance_7 (0.68)
    PC2: "Speed/Efficiency" → OutcomeImportance_2 (0.71), OutcomeImportance_5 (0.58)  

    The cross-loadings here show that OutcomeImportance_5, contributes to PC1 and PC2,
    this makes it harder to explain what each component represents

    The return value is a list of outcome importances e.g. 

    OutcomeImportance_20, OutcomeImportance_11, OutcomeImportance_3
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import ClassVar

import pandas as pd

from juno.pipeline.context import Context
from juno.pipeline.keys import Key
from juno.pipeline.step import Step

logger = logging.getLogger(__name__)


def _select_key_outcomes(
    
    loading_matrix : pd.DataFrame,
    max_outcomes_per_component: int = 2,
    maximum_cross_loading : float = 0.30,
    minimal_primary_loading: float = 0.35) -> list[str] :

    if minimal_primary_loading < 0 or maximum_cross_loading < 0:
        raise ValueError('Both thresholds must be greater than 0')

    valid = (
        0 <= maximum_cross_loading
        and maximum_cross_loading < minimal_primary_loading
        and minimal_primary_loading <= 1.0)

    if not valid:
        raise ValueError(
            f"Invalid thresholds: max_cross_loading must be < minimal_primary_loading "
            f"and both in [0,1]. Got max_cross={maximum_cross_loading}, primary={minimal_primary_loading}")

    logger.debug(f"Selecting key outcomes using {maximum_cross_loading} minimal "
                f"cross loading and {minimal_primary_loading} minimal primary loading")

    key_outcome_names = []
    
    for comp in loading_matrix.columns:
        sorted_by_strength = loading_matrix[comp].abs().sort_values(ascending=False)
        
        chosen_for_this_comp = []
        for feat_name, strength in sorted_by_strength.items():
            if len(chosen_for_this_comp) >= max_outcomes_per_component:
                break  # Stop after getting enough outcomes
            
            if strength < minimal_primary_loading:
                continue
                
            # Check cross-loading
            others = [c for c in loading_matrix.columns if c != comp]
            cross = loading_matrix.loc[feat_name, others].abs().max() if others else 0.0
            
            if cross < maximum_cross_loading:
                chosen_for_this_comp.append(feat_name)
        
        # If nothing found, take the strongest
        if not chosen_for_this_comp:
            chosen_for_this_comp = [sorted_by_strength.index[0]]
        
        key_outcome_names.extend(chosen_for_this_comp)  # Add all chosen outcomes
    
    # De-duplicate while preserving order
    seen = set()
    key_outcome_names = [k for k in key_outcome_names if not (k in seen or seen.add(k))]

    logger.debug(f"Selected {len(key_outcome_names)} key outcomes")

    return key_outcome_names


@dataclass
class SelectKeyOutcomes(Step):
    """
    Pipeline step: gets the key outcomes (importances) - those outcomes that drive a particular
    theme (or primary component) like "speed of use" or "speed/efficiency"
    """
    name:ClassVar[str] = "select_key_outcomes"

    max_outcomes_per_component:int = 2
    maximum_cross_loading : float = 0.30
    minimal_primary_loading: float = 0.35

    def run(self, ctx:Context) -> Context:

        loadings = ctx.require_table(Key.DERIVED_TABLE_PCA_LOADINGS)
        
        if loadings.empty:
            raise ValueError(f"{Key.DERIVED_TABLE_PCA_LOADINGS} cannot be empty")

        key_outcomes = _select_key_outcomes(
            loadings,
            max_outcomes_per_component=self.max_outcomes_per_component,
            maximum_cross_loading=self.maximum_cross_loading,
            minimal_primary_loading=self.minimal_primary_loading)

        ctx.set_state(Key.DERIVED_LIST_KEY_OUTCOMES, key_outcomes)

        return ctx