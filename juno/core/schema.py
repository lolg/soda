"""
Schema definitions for data keys and column names.

This module defines the unified schema used throughout Juno:

DataKey
-------
Keys used in JSON files, DataFrames, and Pydantic models. These maintain
the camelCase convention from the input JSON format.

Prefix
------
Prefixes for dynamically generated column names in wide-format DataFrames.

Internal Analysis Schema
------------------------
The internal column names are used for analysis DataFrames. For example, the
aggregated results table consists of one row per (Segment x Outcome):

| SEGMENT_ID | OUTCOME_ID | IMP_TB | SAT_TB | 
|------------|------------|--------|--------|
| 0          | 1          | 77%    | 42%    | 
| 0          | 2          | 90%    | 77%    |
| 1          | 1          | 56%    | 80%    |
| 1          | 2          | 65%    | 62%    |
"""

from enum import StrEnum
from typing import Final

import pandas as pd


class DataKey (StrEnum):
    RESPONDENT_ID = "respondentId"
    OUTCOME_ID = "outcomeId"
    IMPORTANCE = "importance"
    SATISFACTION = "satisfaction"
    SEGMENT_ID = "segmentId"
    SAT_TB = "sat_tb"
    IMP_TB = "imp_tb"
    OPP_TB = "opp_tb"
    SIZE_PCT = "size_pct"
    SEGMENTS = "segments"
    OUTCOMES = "outcomes"

# Rating bounds
MIN_OUTCOME_RATING: Final[int] = 1
MAX_OUTCOME_RATING: Final[int] = 5

class Prefix(StrEnum):
    IMPORTANCE_PREFIX = "outcomeImportance_"
    SATISFACTION_PREFIX = "outcomeSatisfaction_"
    OPPORTUNITY_PREFIX = "opportunity_"
    PRIMARY_COMPONENT_PREFIX = "pc_"
 

def importance_col(i: int) -> str:
    return f"{Prefix.IMPORTANCE_PREFIX}{i}"


def satisfaction_col(i: int) -> str:
    return f"{Prefix.SATISFACTION_PREFIX}{i}"


def primary_component_col(i: int) -> str:
    return f"{Prefix.PRIMARY_COMPONENT_PREFIX}{i}"


def opportunity_col(i: int) -> str:
    return f"{Prefix.OPPORTUNITY_PREFIX}{i}"


def is_importance(col: str) -> bool:
    return col.startswith(Prefix.IMPORTANCE_PREFIX)


def is_opportunity(col: str) -> bool:
    return col.startswith(Prefix.OPPORTUNITY_PREFIX)


def is_satisfaction(col: str) -> bool:
    return col.startswith(Prefix.SATISFACTION_PREFIX)


def corresponding_satisfaction(importance_column: str) -> str:
    return importance_column.replace(
        Prefix.IMPORTANCE_PREFIX, Prefix.SATISFACTION_PREFIX
    )


def corresponding_importance(satisfaction_column: str) -> str:
    return satisfaction_column.replace(
        Prefix.SATISFACTION_PREFIX, Prefix.IMPORTANCE_PREFIX
    )


def corresponding_opportunity(importance_column: str) -> str:
    return importance_column.replace(
        Prefix.IMPORTANCE_PREFIX, Prefix.OPPORTUNITY_PREFIX
    )

def list_opportunity_columns(df: pd.DataFrame) -> list[str]:
    return [c for c in df.columns if is_opportunity(c)]


def validate_rating(value: int) -> bool:
    return MIN_OUTCOME_RATING <= value <= MAX_OUTCOME_RATING


def validate_threshold(value: int) -> bool:
    return MIN_OUTCOME_RATING <= value <= MAX_OUTCOME_RATING