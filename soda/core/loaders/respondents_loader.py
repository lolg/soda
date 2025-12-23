import json

import pandas as pd

from soda.core.loaders.base_loader import BaseLoader
from soda.core.schema import DataKey


class RespondentsLoadError(Exception):
    pass


class RespondentsLoader(BaseLoader):
    """Load respondents from JSONL."""
    
    @property
    def _error_class(self):
        return RespondentsLoadError
    
    def _load_from_file(self, file_handle) -> pd.DataFrame:
        """Load respondents JSONL."""
        rows = []
        
        for i, line in enumerate(file_handle, start=1):
            if isinstance(line, bytes):
                line = line.decode('utf-8')
            if not line.strip():
                continue
            
            try:
                row = json.loads(line)
                rows.append(row)
            except json.JSONDecodeError as e:
                raise RespondentsLoadError(f"Invalid JSON on line {i}: {e}") from e
        
        if not rows:
            raise RespondentsLoadError("No respondents found")
        
        df = pd.DataFrame(rows)
        
        # Validate respondentId exists
        if DataKey.RESPONDENT_ID not in df.columns:
            raise RespondentsLoadError("Missing 'respondentId' column")
        
        # Ensure respondentId is numeric (should be based on your format)
        try:
            df[DataKey.RESPONDENT_ID] = pd.to_numeric(df[DataKey.RESPONDENT_ID])
        except ValueError as e:
            raise RespondentsLoadError(f"respondentId must be numeric: {e}") from e
        
        return df