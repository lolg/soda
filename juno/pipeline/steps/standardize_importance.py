"""
    Step to standardize respondents' importance ratings onto a common scale.
    People use rating scales differently, some respondents are "tough graders"
    and never mark above 3, others are "kind graders" and mark above 3 and some
    will use the full range. Even if tough graders and kind graders care about the
    same things, there responses will look very different. 
    Standardization fixes that by putting every column (outcome) on a common scale
     — mean = 0, standard deviation = 1.
    So instead of using raw 1-5 values, we express each rating in terms of how far
    it is from the average (in units of standard deviations).
    For each importance outcome value, we end up with what is known as the z-score.
    This is nothing more than:
    
    x - mean (x) / std(x), where x is the importance value.

    Standardizing the importance data, results in values like:
    
    | OutcomeImportance_1 | OutcomeImportance_2 | ... |
    |---------------------|---------------------|-----|
    |          0.5        |          0.43       | ... |
    where the rows are the z-scores (scaled values) for each respondent
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import ClassVar

import pandas as pd
from sklearn.preprocessing import StandardScaler

from juno.core.schema import is_importance
from juno.pipeline.context import Context
from juno.pipeline.keys import Key
from juno.pipeline.step import Step

logger = logging.getLogger(__name__)


def _standardize_importance(data: pd.DataFrame) -> pd.DataFrame: 
    """Return a DataFrame of column-wise standardized importance features."""

    if data is None or data.empty:
        raise ValueError("Primary dataset is empty; no importance values to standardize")

    importance_cols = [col for col in data.columns if is_importance(col)]

    logger.debug(f"Standardizing {len(importance_cols)} importance columns")

    if not importance_cols:
        raise ValueError("No importance columns found in data")

    importance_data = data[importance_cols]
    scaler = StandardScaler(with_mean=True, with_std=True)

    importance_data_standardized = pd.DataFrame(
        scaler.fit_transform(importance_data),
        columns=importance_cols,
        index=data.index)

    logger.debug(f"Standardized {len(importance_cols)} importance columns")
    
    return importance_data_standardized


@dataclass(frozen=True)
class StandardizeImportance(Step):
    """Pipeline step: compute and store column-wise standardized importance features."""
    
    name: ClassVar[str] = "standardize_importance"

    def run(self, ctx: Context) -> Context:

        primary:pd.DataFrame = ctx.require_primary()

        imp_std = _standardize_importance(primary)
        ctx.add_table(Key.DERIVED_TABLE_IMPORTANCE_STD, imp_std)

        return ctx

# ------------------------------------------------------------------------------
