"""
Opportunity Score Calculations for ODI Methodology

This module contains the two core opportunity score calculations used in ODI:

1. Individual-level opportunity (for segmentation/clustering)
   - Uses raw 1-5 Likert scores per respondent
   - Scale: 1-10
   - Purpose: Identify respondents with similar need profiles

2. Aggregate-level opportunity (for outcome characterization)
   - Uses Top-2-Box percentages across respondents
   - Scale: 0-20
   - Purpose: Identify underserved/overserved outcomes per ODI standard

Both use the same Ulwick formula: Opportunity = Importance + max(Importance - Satisfaction, 0)
The difference is the input scale and interpretation.

References:
- Ulwick, A. (2005). "What Customers Want"
- Strategyn ODI Methodology
"""

from __future__ import annotations

import numpy as np


def compute_individual_opportunity(importance: int, satisfaction: int) -> int:
    """
    Calculate opportunity score at the individual respondent level.
    
    Used for clustering/segmentation - each respondent gets their own opportunity
    score based on their personal ratings.
    
    Formula: Opportunity = Importance + max(Importance - Satisfaction, 0)

    Returns:
        Opportunity score on 1-10 scale
    """
    return importance + np.maximum(importance - satisfaction, 0)


def compute_aggregate_opportunity(
    importance_t2b: float, 
    satisfaction_t2b: float
) -> float:
    """Calculate opportunity score at the aggregate outcome level using Top-2-Box."""

    if not (0 <= importance_t2b <= 100 and 0 <= satisfaction_t2b <= 100):
        raise ValueError(
            f"T2B percentages must be 0-100. "
            f"Got importance_t2b={importance_t2b}, satisfaction_t2b={satisfaction_t2b}"
        )
    
    # Convert from percentage (0-100) to 0-10 scale
    imp_scaled = importance_t2b / 10
    sat_scaled = satisfaction_t2b / 10
    
    return imp_scaled + np.maximum(imp_scaled - sat_scaled, 0)