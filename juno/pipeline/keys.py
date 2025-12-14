"""
Pipeline context keys for accessing tables and state.

This module defines string constants used to read/write data in the pipeline
`Context`. All data lives in one of two namespaces:

- `ctx.tables[...]`  : tabular artifacts (pandas DataFrames or dicts of them)
- `ctx.state[...]`   : non-tabular artifacts (configs, models, JSON-like dicts)
"""

from enum import StrEnum


class Key(StrEnum):
    # ─────────────────────────────────────────────────────────────────────────────
    # Feature prep and dimensionality reduction
    # ─────────────────────────────────────────────────────────────────────────────

    # Standardized importance values (for PCA/feature scaling)
    # | RespondentID | OutcomeImportance_1 | ... |
    # |--------------|---------------------|-----|
    # | 1            | 0.24                | ... |
    DERIVED_TABLE_IMPORTANCE_STD = "DERIVED_TABLE_IMPORTANCE_STD"

    # Number of retained principal components (int)
    STATE_PARAM_N_COMPONENTS = "STATE_PARAM_N_COMPONENTS"

    # Outcome loadings per component (importance only)
    # |              | PC1   | PC2   | ... |
    # |--------------|-------|-------|-----|
    # | Outcome_1    | 0.34  | 0.45  | ... |
    # | Outcome_2    | ...   | ...   | ... |
    DERIVED_TABLE_PCA_LOADINGS = "DERIVED_TABLE_PCA_LOADINGS"

    # Selected key importance outcomes based on loadings/thresholds
    # Example: ['OutcomeImportance_20', 'OutcomeImportance_11', ...]
    DERIVED_LIST_KEY_OUTCOMES = "DERIVED_LIST_KEY_OUTCOMES"

    # ─────────────────────────────────────────────────────────────────────────────
    # Filtering, opportunity scoring, segmentation
    # ─────────────────────────────────────────────────────────────────────────────

    # Wide table with ONLY the selected outcomes (importance + satisfaction)
    # | RespondentID | OutcomeSatisfaction_10 | ... | OutcomeImportance_10 | ... |
    # |--------------|------------------------|-----|----------------------|-----|
    # | 1            | 4                      | ... | 3                    | ... |
    DERIVED_TABLE_RESPONSES_FILTERED = "DERIVED_TABLE_RESPONSES_FILTERED"

    # FILTERED_RESPONSES plus opportunity scores per selected outcome
    # | RespondentID | ... | Opportunity_10 | Opportunity_11 | ... |
    # |--------------|-----|----------------|----------------|-----|
    DERIVED_TABLE_RESPONSES_FILTERED_OPP = "DERIVED_TABLE_RESPONSES_FILTERED_OPP"

    # FILTERED_RESPONSES plus opportunity scores per selected outcome with segment id
    # | RespondentID | ... | Opportunity_10 | Opportunity_11 | ... | SegmentID |
    # |--------------|-----|----------------|----------------|-----|-----------|
    DERIVED_TABLE_RESPONSES_OPP = "DERIVED_TABLE_RESPONSES_OPP"

    # Full primary table (ALL outcomes) with SegmentID joined back in.
    # (Opportunity columns not included here.)
    # | RespondentID | OutcomeSatisfaction_1..N | OutcomeImportance_1..N | SegmentID |
    # |--------------|--------------------------|------------------------|-----------|
    DERIVED_TABLE_RESPONSES_WIDE_SEG = "DERIVED_TABLE_RESPONSES_WIDE_SEG"

    # ─────────────────────────────────────────────────────────────────────────────
    # Segment characterization (Top-2-Box) and sizes
    # ─────────────────────────────────────────────────────────────────────────────

    # Per (SegmentID, OutcomeID): within-segment Top-Box percentages
    # | SegmentID | OutcomeID | Sat_TB | Imp_TB   | Opp_TB |
    # |-----------|-----------|---------|---------|--------|
    # | 0         | 1         | 73.2    | 94.3    | 9.4    |
    # | 1         | 1         | 54.3    | 47.6    | 5.4    |
    GEN_TABLE_SEGMENT_OUTCOME_T2B = "GEN_TABLE_SEGMENT_OUTCOME_T2B"

    # Segment sizes as % of ALL respondents (sums ~100)
    # | SegmentID | Percentage |
    # |-----------|------------|
    # | 0         | 31.3       |
    # | 1         | 36.1       |
    GEN_TABLE_SEGMENT_SIZES = "GEN_TABLE_SEGMENT_SIZES"