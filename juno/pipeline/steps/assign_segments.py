"""
Up to now, every respondent has their own set of opportunity scores for each outcome.
But not all respondents think alike.
    - Some might be very frustrated about speed and efficiency.
    - Others might care more about reliability or ease of use.

So, by clustering respondents based on their opportunity profiles, we can identify segments of people
who share the same unmet needs. That’s the practical goal of this step:

“Find groups of customers who feel underserved in similar ways.”

We can imagine the opportunity scores for each of our chosen outcomes as a point cloud in N-dimensional
space, each axis is a outcome id and a single point represents a respondent. E.g. for if we only had
3 outcomes:

Say you only had 3 outcomes:

    - Outcome A: OpportunityA
    - Outcome B: OpportunityB
    - Outcome C: OpportunityC

Then each respondent looks like this: 

| Respondent_ID | Opportunity_A | Opportunity_B | Opportunity_C |
----------------|-------------------------------|---------------|
| 1      	    | 7             | 3             | 5			    |
| 2     		| 6             | 2             | 4 			|
| 3      		| 2             | 8             | 1				|

And with K-means, its like looking at this point cloud in N-dimensional space and
and trying to draw invisible “bubbles” around dense groups.

The output is our original data but with additional columns, one for each cluster 

RespondentID | OutcomeImp_1 | OutcomeImp_N |...| OutcomeSat_1 | OutcomeSat_N |...| Opp_12 | Opp_23 |...| SegmentID

this table has:
    - all respondents,
    - all outcomes, 
    - *only* the opportunities we selected from the PCA steps
    - the id of the associated cluster for the respondent

The table says, this respondent, has these opportunity scores for the outcomes we
identified as most significant and belongs to these clusters

So A cluster is a group of respondents with similar rating patterns. We're not
clustering the outcomes themselves — we’re clustering people based on how they
evaluate the outcomes. This is important. People naturally cluster because their
contexts, goals, and constraints form patterns:
    - A group of customers who care most about speed and simplicity → “Convenience seekers.”
    - Another group who cares about control and customization → “Power users.”
    - Another who values price and reliability → “Cost-conscious pragmatists.”

If we cluster outcomes, you might find themes like:

“Ease of use”, “Speed”, “Reliability.” That’s useful — but it doesn’t tell us who feels
underserved or how big that market is. If we cluster respondents, we get:

“Cluster A = 25% of customers, focused on convenience.”
“Cluster B = 15%, focused on control.”

With that we can:
    - Size the opportunity.
    - Prioritize which unmet needs to pursue.
    - Target messaging and product positioning.

That's where ODI turns into actual strategic guidance, so:

PCA = group outcomes by correlation → find themes.
KMeans = group respondents by similarity → find market segments.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import ClassVar

import pandas as pd
from sklearn.cluster import KMeans

from juno.core.schema import DataKey, list_opportunity_columns
from juno.pipeline.context import Context
from juno.pipeline.keys import Key
from juno.pipeline.step import Step

logger = logging.getLogger(__name__)

def _add_segments(
    data : pd.DataFrame,
    num_segments : int,
    random_state : int = 10):
    """
    Define segments based on the required target number and random state

    The number of segments is a strategtic choice here. We could choose one
    by comparing different segments to their silhouette scores, but here, the
    number of segments is a key decision.
    """

    if data.empty:
        raise ValueError("Cannot add segments to an empty DataFrame")
    if num_segments <= 0:
        raise ValueError("Number of segments must be greater than 0")

    logger.debug(
        f"Starting KMeans clustering with {num_segments} segments on {len(data)} respondents. "
        f"Using {len(list_opportunity_columns(data))} opportunity columns"
    )

    data_with_segments = data.copy()
    
    opportunity_columns = list_opportunity_columns(data)
    opportunity_scores = data[opportunity_columns].values

    kmeans = KMeans(n_clusters=num_segments, random_state=random_state, n_init="auto")
    segment_labels = kmeans.fit_predict(opportunity_scores)

    data_with_segments[DataKey.SEGMENT_ID] = segment_labels 

    logger.debug(
        f"KMeans clustering completed. Assigned segment labels to {len(data_with_segments)} respondents."
    )
    
    return data_with_segments

def _join(primary: pd.DataFrame, with_opp_and_seg: pd.DataFrame) -> pd.DataFrame:
    """
    Join segment assignments from the filtered opportunity+segmentation table back to the primary table.

    Returns:
        pd.DataFrame: Primary table with segment assignments added as a new column.
    """
    # Defensive check: ensure respondent ID columns exist
    for col in [DataKey.RESPONDENT_ID]:
        if col not in primary.columns:
            raise KeyError(f"Primary table missing required column '{col}'")
        if col not in with_opp_and_seg.columns:
            raise KeyError(f"with_opp_and_seg missing required column '{col}'")
    if DataKey.SEGMENT_ID not in with_opp_and_seg.columns:
        raise KeyError(f"with_opp_and_seg missing required column '{DataKey.SEGMENT_ID}'")

    # Drop duplicate respondent assignments, if any, in the lookup table
    seg_assignments = (
        with_opp_and_seg[[DataKey.RESPONDENT_ID, DataKey.SEGMENT_ID]]
        .drop_duplicates(subset=[DataKey.RESPONDENT_ID])
        .reset_index(drop=True)
    )

    # Merge on respondent ID
    merged = primary.merge(
        seg_assignments,
        on=DataKey.RESPONDENT_ID,
        how="left",
        validate="m:1"  # many rows in primary, one in seg_assignments
    )

    # Optionally warn if any segment assignments are missing post-merge
    missing_assignments = merged[DataKey.SEGMENT_ID].isnull().sum()
    if missing_assignments > 0:
        logger.warning(f"{missing_assignments} rows in primary table could not be assigned a segment.")

    return merged

@dataclass
class AssignSegments(Step):
    """Segment using the opportunity scores, (for the reduced set of outcomes)"""
    name:ClassVar[str] = "assign_segments"

    num_segments:int
    random_state: int = 10

    def run(self, ctx:Context) -> Context:

        filtered_with_opportunity = ctx.require_table(
            Key.DERIVED_TABLE_RESPONSES_FILTERED_OPP)

        with_opp_seg = _add_segments(
            filtered_with_opportunity,
            self.num_segments,
            self.random_state)

        # with_opp_seg contains the satisfaction, importance and opportunity
        # scores along with the segment id as follows:
        #
        # | respondentId | ... | opportunity_1 | ... | segmentId |
        # |--------------|-----|----------------|-----|-----------|

        ctx.add_table(Key.DERIVED_TABLE_RESPONSES_OPP, with_opp_seg)

        primary_with_seg = _join(ctx.responses, with_opp_seg)

        # primary_with_seg contains the satisfaction and importance scores
        # along with the segment id as follows:
        #
        # | respondentId | ... | opportunity_1 | ... | segmentId |
        # |--------------|-----|---------------|-----|-----------|

        ctx.add_table(Key.DERIVED_TABLE_RESPONSES_WIDE_SEG, primary_with_seg)

        return ctx