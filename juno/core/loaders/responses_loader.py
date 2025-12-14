import json

import pandas as pd
from pydantic import BaseModel, ValidationError, conint

from juno.core.loaders.base_loader import BaseLoader
from juno.core.schema import (
    DataKey,
    importance_col,
    satisfaction_col,
)


class ResponseRecord(BaseModel):
    """
    One atomic observation: a single respondent’s rating for a single outcome.

    Constraints:
      - importance: integer in [1..5]
      - satisfaction: integer in [1..5]

    Notes:
      - Juno enforces validity here; it does not coerce or impute.
      - This is the fundamental unit used to build wide tables for analysis.
    """
    respondentId: int
    outcomeId: int
    importance: conint(ge=1, le=5)
    satisfaction: conint(ge=1, le=5)


"""
Load responses from a JSON Lines file and pivot to wide format.

Input (JSONL), one object per line, validated via ResponseRecord:
	{
		"respondentId": int,
		"outcomeId": int,
		"importance": 1..5,
		"satisfaction": 1..5
	}

Output (wide DataFrame), columns:
	- InternalCol.INTERNAL_RESPONDENT_ID_COL
	- OutcomeSatisfaction_1..N
	- OutcomeImportance_1..N

Notes
- Duplicates (same respondentId, outcomeId) are aggregated via mean.
- Importance/satisfaction columns are reindexed numerically and renamed via schema helpers.
"""

class ResponseLoadError(Exception):
		"""Raised when response loading fails."""
		pass


class ResponsesLoader(BaseLoader):
    
    @property
    def _error_class(self):
        return ResponseLoadError
    
    def _load_from_file(self, file_handle) -> pd.DataFrame:
        """Load from an open file handle."""
        rows = []
        for i, line in enumerate(file_handle, start=1):
                if isinstance(line, bytes):
                        line = line.decode('utf-8')
                if not line.strip():
                        continue
                try:
                        raw = json.loads(line)
                        row = ResponseRecord(**raw)
                        rows.append(row.model_dump())
                except (json.JSONDecodeError, ValidationError) as e:
                        raise ResponseLoadError(f"Error on line {i}: {e}")
        
        if not rows:
                raise ResponseLoadError("No valid records found")
        
        df =  pd.DataFrame(rows)
        df = self._pivot(df)

        return df

    def _pivot(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Pivot a long response table to wide format with one row per respondent.

        - One and only one response allowed per (respondentId, outcomeId)
        - Fails fast if duplicates exist
        - Ensures numeric outcome IDs, column sort, naming via schema helpers
        """

        # Check for duplicates: same (respondentId, outcomeId)
        duplicates = df.duplicated(
            subset=[DataKey.RESPONDENT_ID, DataKey.OUTCOME_ID], keep=False
        )
        if duplicates.any():
                dup_rows = df.loc[
                        duplicates, [DataKey.RESPONDENT_ID, DataKey.OUTCOME_ID]]
                dup_msg = (
                        "Duplicate (respondentId, outcomeId) pairs found in responses:\n"
                        + dup_rows.to_string(index=False)
                )
                raise ValueError(dup_msg)

        imp = df.pivot(
            index=DataKey.RESPONDENT_ID,
            columns=DataKey.OUTCOME_ID,
            values=DataKey.IMPORTANCE,
        )
        sat = df.pivot(
            index=DataKey.RESPONDENT_ID,
            columns=DataKey.OUTCOME_ID,
            values=DataKey.SATISFACTION,
        )

        # Reindex (re-order the columns)
        imp = imp.reindex(sorted(imp.columns), axis=1)
        sat = sat.reindex(sorted(sat.columns), axis=1)

        # Rename the columns
        imp.columns = [importance_col(int(c)) for c in imp.columns]
        sat.columns = [satisfaction_col(int(c)) for c in sat.columns]

        # Use the respondentId (index) to concat sat and imp
        wide = pd.concat([sat, imp], axis=1).reset_index()
        wide = wide.rename(columns={DataKey.RESPONDENT_ID: DataKey.RESPONDENT_ID})

        return wide