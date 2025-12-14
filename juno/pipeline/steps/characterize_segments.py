"""
 We now know which respondents belong to which cluster. The process up to this point was:

 Identify important outcomes (via PCA)
    - Compute opportunity scores for those outcomes
    - Segment respondents based on their opportunity profiles

Each respondent is now assigned to a cluster — e.g. Cluster 0, 1, or 2.
Next, we summarize how each cluster feels about each outcome.

For every cluster, we:
    - Select all respondents in that cluster.
    - Look across all outcomes.
    - Count how many respondents rated an outcome as 4 or 5 (on a 1-5 scale).
    - Compute the percentage of such respondents within that cluster.

We repeat this for satisfaction as well as importance.

This gives us a percentage-based view: for each cluster and outcome,
we know what share of respondents rated the importance or satisfaction as high (≥4 or 5).

These percentages become the axes of our opportunity landscape:
    X-axis → % rating the outcome as highly important
    Y-axis → % rating the outcome as highly satisfying

When interpreting the plot, remember:
    A point in the bottom-right (e.g. 90% importance, 20% satisfaction)
    means that most respondents care deeply about this outcome,
    but few are satisfied with it. It's not that satisfaction scores were “low” on average —
    rather, only a small share rated their satisfaction high. That’s what signals opportunity.

We use Top-2-Box because with a 1-5 scale, the Top-2-Box (T2B) method looks at the share
of people who gave the top two ratings (4 or 5).
T2B is basically a “share of enthusiasts” measure — it answers the question:
“What proportion of people really care or are really satisfied?”

The results are in the form:

| SegmentID | OutcomeID | Sat_T2B | Imp_T2B |
------------|---------------------|---------|
| 0         | 12        | 23.4    | 76.2    |
| ...       | ...       | ...     | ...     |
| 1         | 7         | 36.3    | 58.4    |   
| ...       | ...       | ...     | ...     |
| 2         | 23        | 56.4    | 54.3    |

Top-2-Box threshold (that is, importance/satisfaction values of 4 or 5)

Identify columns (kept generic via schema helpers)

"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import ClassVar

import numpy as np
import pandas as pd

from juno.core.schema import (
    DataKey,
    is_importance,
    is_satisfaction,
    validate_threshold,
)
from juno.pipeline.context import Context
from juno.pipeline.keys import Key
from juno.pipeline.opportunity import compute_aggregate_opportunity
from juno.pipeline.step import Step

logger = logging.getLogger(__name__)

def _compute_topbox_percentages(
    df_with_segments : pd.DataFrame,
    top_box_threshold: int = 4
    )-> tuple[pd.DataFrame, pd.Series]:

    if df_with_segments.empty:
        raise ValueError("Cannot compute segment characteristics on an empty DataFrame")
    if not validate_threshold(top_box_threshold):
        raise ValueError("T2B threshold must be between 1 and 5")

    logger.debug(f"Computing segment characteristics with T2B threshold of {top_box_threshold}")

    importance_cols   = sorted([c for c in df_with_segments.columns if is_importance(c)],
                            key=lambda s: int(s.rsplit('_', 1)[-1]))
    satisfaction_cols = sorted([c for c in df_with_segments.columns if is_satisfaction(c)],
                            key=lambda s: int(s.rsplit('_', 1)[-1]))

    if len(importance_cols) != len(satisfaction_cols):
        raise ValueError("Mismatched importance vs satisfaction columns.")

    cluster_sizes = (
        df_with_segments[DataKey.SEGMENT_ID]
        .value_counts(normalize=True)
        .sort_index()
        .mul(100)
        .round(1)
        .reset_index(name=DataKey.SIZE_PCT)
        .rename(columns={'index': DataKey.SEGMENT_ID}))

    records = []

    for cid in sorted(df_with_segments[DataKey.SEGMENT_ID].dropna().unique()):
        m = (df_with_segments[DataKey.SEGMENT_ID] == cid)
        if not np.any(m):
            continue

        sat_t2b = ((df_with_segments.loc[m, satisfaction_cols] >= top_box_threshold)
                .mean(axis=0).mul(100).round(1))
        imp_t2b = ((df_with_segments.loc[m, importance_cols]   >= top_box_threshold)
                .mean(axis=0).mul(100).round(1))

        for sat_col, imp_col in zip(satisfaction_cols, importance_cols):
            outcome_id = int(sat_col.rsplit('_', 1)[-1])
            records.append({
                DataKey.SEGMENT_ID: int(cid),
                DataKey.OUTCOME_ID: outcome_id,
                DataKey.SAT_TB: float(sat_t2b[sat_col]),
                DataKey.IMP_TB: float(imp_t2b[imp_col]),
            })

    results = pd.DataFrame.from_records(records).sort_values(
        [DataKey.SEGMENT_ID, DataKey.OUTCOME_ID]
    ).reset_index(drop=True)

    logger.debug(f"Computed segment characteristics with T2B threshold of {top_box_threshold}")
    
    return results, cluster_sizes

def _add_segment_opportunity_scores(t2b: pd.DataFrame) ->pd.DataFrame:
    """
    Add Opportunity column to segment T2B table.

    Returns:
        DataFrame with added Opportunity column (0-20 scale)
    """

    t2b[DataKey.OPP_TB] = t2b.apply(
        lambda row: compute_aggregate_opportunity(
            row[DataKey.IMP_TB],
            row[DataKey.SAT_TB]),
            axis=1)

    return t2b


@dataclass
class CharacterizeSegments(Step):
    name:ClassVar[str] = "characterize_segments"

    top_box_threshold: int = 0

    def run(self, ctx:Context) -> Context:

        primary_with_segments = ctx.require_table(Key.DERIVED_TABLE_RESPONSES_WIDE_SEG)

        outcome_scores, sizes = _compute_topbox_percentages(
            primary_with_segments,
            self.top_box_threshold)

        outcome_scores = _add_segment_opportunity_scores(outcome_scores)

        ctx.add_table(Key.GEN_TABLE_SEGMENT_OUTCOME_T2B, outcome_scores)
        ctx.add_table(Key.GEN_TABLE_SEGMENT_SIZES, sizes)

        return ctx