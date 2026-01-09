import logging

import pandas as pd

from soda.core.models import Codebook, Outcomes, SegmentModelWithAssignments

logger = logging.getLogger(__name__)

def enrich(
    segment_model: SegmentModelWithAssignments,
    outcomes: Outcomes | None = None,
    respondents_df: pd.DataFrame | None = None,
    codebook: Codebook | None = None
) -> SegmentModelWithAssignments:
    """
    Enrich a SegmentModelWithAssignments with additional information.

    Optionally adds outcome descriptions (if `outcomes` is provided)
    and/or demographic distributions for each segment (if both
    `respondents_df` and `codebook` are provided).

    Args:
        segment_model: The segment model to enrich.
        outcomes: Outcomes object for adding outcome descriptions. Optional.
        respondents_df: DataFrame with respondent demographics. Optional.
        codebook: Codebook object describing demographic fields. Required if respondents_df is provided.

    Returns:
        SegmentModelWithAssignments: The enriched segment model.
    """
    
    if outcomes is not None:
        segment_model = _enrich_with_outcomes(segment_model, outcomes)
    
    if respondents_df is not None:
        if codebook is None:
            raise ValueError("codebook required when enriching with demographics")
        segment_model = _enrich_with_demographics(segment_model, respondents_df, codebook)
    
    return segment_model

def _enrich_with_outcomes(segment_model: SegmentModelWithAssignments, outcomes: Outcomes) -> SegmentModelWithAssignments:
    """Add outcome descriptions to all zone outcomes."""
    
    for segment in segment_model.segments:
        for zone_name, zone_category in segment.zones.__dict__.items():
            for outcome in zone_category.outcomes:
                try:
                    outcome.description = outcomes.get_text(outcome.outcome_id)
                except ValueError:
                    print(f"Warning: No description found for outcome {outcome.outcome_id}")
                    outcome.description = f"Outcome {outcome.outcome_id} (description missing)"
    
    return segment_model



def _enrich_with_demographics(segment_model: SegmentModelWithAssignments, respondents_df:pd.DataFrame, codebook: Codebook) -> SegmentModelWithAssignments:
    """Add demographic distributions to segments."""
    
    # Check we have segment assignments
    if not segment_model.segment_assignments:
        raise ValueError("No segment assignments found - cannot enrich demographics")
    
    # For each segment
    for segment in segment_model.segments:
        logger.info(f"Processing segment {segment.segment_id}")
        
        # Step 1: Get respondents in this segment
        respondent_ids = segment_model.segment_assignments.get_respondents(segment.segment_id)
        if not respondent_ids:
            logger.info(f"  No respondents in segment {segment.segment_id}")
            segment.demographics = {}
            continue
        
        # Filter respondents to only those in this segment
        segment_respondents = respondents_df[respondents_df['respondentId'].isin(respondent_ids)]
        logger.info(f"  Found {len(segment_respondents)} respondents")
        
        segment.demographics = {}
        
        # Step 2: For each categorical dimension, calculate percentages
        for dimension in codebook.dimensions:
            if dimension.type != "categorical":
                continue  # Skip text dimensions like D4
            
            logger.info(f"    Processing {dimension.name} ({dimension.id})")
            
            # Get data for this dimension (e.g., D1, D2, D3)
            if dimension.id not in segment_respondents.columns:
                logger.info(f"    Warning: {dimension.id} not found in data")
                continue
            
            dimension_data = segment_respondents[dimension.id]
            
            # Remove missing codes (e.g., "No Response")
            if dimension.missing_codes:
                # Convert missing codes to int for comparison
                missing_codes_int = [int(code) for code in dimension.missing_codes]
                valid_data = dimension_data[~dimension_data.isin(missing_codes_int)]
            else:
                valid_data = dimension_data
            
            if len(valid_data) == 0:
                segment.demographics[dimension.name] = {}
                continue
            
            # Step 3: Count values and convert to percentages
            value_counts = valid_data.value_counts()
            total = len(valid_data)
            
            # Step 4: Map codes to labels and calculate percentages
            percentages = {}
            for value, count in value_counts.items():
                # Look up the label for this value (e.g., 1 -> "Female")
                value_str = str(value)
                if dimension.options and value_str in dimension.options:
                    label = dimension.options[value_str]
                else:
                    label = f"Unknown ({value})"
                
                percentage = round((count / total) * 100, 1)
                percentages[label] = percentage
                print(f"      {label}: {percentage}%")
            
            # Sort by percentage (highest first)
            sorted_percentages = dict(sorted(percentages.items(), key=lambda x: x[1], reverse=True))
            segment.demographics[dimension.name] = sorted_percentages
    
    return segment_model