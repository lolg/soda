"""High-level segmentation API."""

import logging
from copy import deepcopy

import pandas as pd

from soda.core.config import RulesConfig
from soda.core.models import SegmentModelWithAssignments
from soda.core.orchestrator import Orchestrator
from soda.core.segment_builder import SegmentBuilder
from soda.core.selection import SegmentationSelector

logger = logging.getLogger(__name__)


def segment(
    responses_df: pd.DataFrame, 
    rules: RulesConfig,
    num_segments: int | None = None
) -> SegmentModelWithAssignments:
    """Run full segmentation pipeline.
    
    Args:
        responses_df: Respondent outcome ratings (importance + satisfaction)
        rules: Business rules config. Uses defaults if None.
        num_segments: Force specific segment count. Auto-selects best if None.
        
    Returns:
        Segment model with zones, outcomes, and respondent assignments.
    """
    
    rules = deepcopy(rules)
    
    if num_segments is not None:
        rules.orchestration.parameters["num_segments"] = [num_segments]

    # Orchestration (lightweight - config + metrics only)
    orchestrator = Orchestrator(rules.orchestration)

    all_results = orchestrator.run_all(responses_df)
    logger.info(f"Generated {len(all_results)} candidate solutions")
    
    # Select the best solution based on the rules
    selector = SegmentationSelector(rules.selection_rules)
    recommended = selector.select_best(all_results)

    logger.info(f"Recommended configuration: {recommended['config'].num_segments} segments")

    # Build final model and output JSON
    logger.info("Building final model for recommended configuration...")
    winning_config = recommended['config']

    segmenter = SegmentBuilder(winning_config)
    segmenter.fit(responses_df)
    
    return segmenter.model_with_assignments