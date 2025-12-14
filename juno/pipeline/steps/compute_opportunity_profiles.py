"""
    Using the key variables, we build a smaller, focused respondent-level table:

    | RespondentID | OutcomeImportance_7  | OutcomeImportance_12 | 
    |--------------|----------------------|----------------------|
    | 1            | 4                    | 3                    |                  
    | 2            | 3                    | 4                    |                  
    | 3            | 5                    | 4                    |        

    We then add the matching satisfaction values. These values are NOT standardized —
    they remain as the original 1–5 survey ratings.

    | RespondentID | OutcomeSat_7 | OutcomeSat_12 | OutcomeImp_3 | OutcomeImp_4 |
    |--------------|--------------|---------------|--------------|--------------|
    | 1            | 4            | 3             | 2            | 5            |
    | 2            | 3            | 4             | 2            | 4            |
    | 3            | 5            | 4             | 3            | 5            |

    This `filtered_data` table keeps only the outcomes that define the major PCA themes.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import ClassVar, List

import pandas as pd

from juno.core.schema import (
    DataKey,
    corresponding_opportunity,
    corresponding_satisfaction,
    is_importance,
    is_satisfaction,
)
from juno.pipeline.context import Context
from juno.pipeline.keys import Key
from juno.pipeline.opportunity import compute_individual_opportunity
from juno.pipeline.step import Step

logger = logging.getLogger(__name__)

def _filter_to_key_outcomes(
    data : pd.DataFrame,
    key_outcomes : list[str]) -> pd.DataFrame:

    if data.empty:
        raise ValueError("Cannot select key outcomes from an empty DataFrame")

    logger.debug(
        f"Filtering data to {len(key_outcomes)} key outcomes"
    )

    importance_features = [col for col in data.columns if is_importance(col)]
    satisfaction_features = [col for col in data.columns if is_satisfaction(col)]

    logger.debug(
        f"Identified {len(importance_features)} importance features and "
        f"{len(satisfaction_features)} satisfaction features in the dataset."
    )

    importance_data = data[importance_features]
    satisfaction_data = data[satisfaction_features]

    respondent_ids = data[DataKey.RESPONDENT_ID]

    # Map to paired satisfaction columns and build the filtered table used downstream

    filtered_importance_data = importance_data[key_outcomes]

    key_satisfaction_variables = [
        corresponding_satisfaction(col) for col in key_outcomes
    ]

    logger.debug(
        f"Paired satisfaction variables for key outcomes: {', '.join(key_satisfaction_variables)}"
    )

    filtered_satisfaction_data = satisfaction_data[key_satisfaction_variables]

    filtered_data = pd.concat(
        [respondent_ids, filtered_satisfaction_data, filtered_importance_data],
        axis=1
    )

    logger.debug(
        f"Filtered dataset now contains respondent IDs, {len(key_satisfaction_variables)} satisfaction columns, "
        f"and {len(key_outcomes)} importance columns. Shape: {filtered_data.shape}"
    )

    return filtered_data

def _add_opportunity_scores(
    filtered_data: pd.DataFrame
) -> pd.DataFrame:

    if filtered_data.empty:
        raise ValueError("Cannot add opportunity scores to an empty DataFrame")

    logger.debug("Adding opportunity scores to filtered DataFrame with shape %s", filtered_data.shape)

    data = filtered_data.copy()

    importance_columns = [c for c in data.columns if is_importance(c)]
    logger.debug("Identified %d importance columns: %s", len(importance_columns), ", ".join(importance_columns))

    for importance_column in importance_columns:
        satisfaction_column = corresponding_satisfaction(importance_column)
        opportunity_column = corresponding_opportunity(importance_column)

        logger.debug(
            "Computing opportunity for importance: '%s', satisfaction: '%s', storing in: '%s'",
            importance_column, satisfaction_column, opportunity_column
        )

        # Vectorized ODI calculation
        data[opportunity_column] = data.apply(
            lambda row: compute_individual_opportunity(row[importance_column], row[satisfaction_column]),
            axis=1
        )

    added_columns = [corresponding_opportunity(col) for col in importance_columns]
    logger.debug(
        "Added %d opportunity score columns, resulting DataFrame shape: %s",
        len(added_columns), data.shape
    )

    return data

@dataclass
class ComputeOpportunityProfiles (Step):
    """
    Filter the original data based on the key (importance) outcomes, this gives us
    as a subset of non-standardized (original) importance and satisfaction values

    | RespondentID | OutcomeImp_4 | OutcomeImp_16 |...| OutcomeSat_4 | OutcomeSatis_16
    |-------------------------------------------------------------------------------
    | 1            | 5            | 2             |   | 3            | 1
      """
    name:ClassVar[str] = "filter_to_key_outcomes"

    def run(self, ctx:Context) -> Context:

        ctx.require_primary()
        key_outcomes:List(str) = ctx.require_state(Key.DERIVED_LIST_KEY_OUTCOMES)

        filtered_outcomes = _filter_to_key_outcomes(ctx.responses, key_outcomes)

        df = _add_opportunity_scores(filtered_outcomes)
        ctx.add_table(Key.DERIVED_TABLE_RESPONSES_FILTERED_OPP, df)
        
        return ctx