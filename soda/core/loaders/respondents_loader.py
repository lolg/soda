import json

import pandas as pd

from soda.core.loaders.base_loader import BaseLoader
from soda.core.models import Respondents
from soda.core.schema import DataKey


class RespondentsLoadError(Exception):
    pass


class RespondentsLoader(BaseLoader):
    """Load respondents from JSONL."""
    
    def __init__(self, path=None, file_obj=None, as_model=False):
        super().__init__(path, file_obj)
        self.as_model = as_model
    
    @property
    def _error_class(self):
        return RespondentsLoadError
    
    def load(self):
        """Load respondents as DataFrame or Pydantic model."""
        if self.as_model:
            return self._load_as_model()
        else:
            return self._load_as_dataframe()
    
    def _load_as_model(self) -> Respondents:
        """Load as Pydantic Respondents model."""
        df = self._load_as_dataframe()
        return Respondents.from_dataframe(df)
    
    def _load_as_dataframe(self) -> pd.DataFrame:
        """Load as DataFrame."""
        if self.path:
            with open(self.path, 'r', encoding='utf-8') as f:
                return self._load_from_file(f)
        else:
            return self._load_from_file(self.file_obj)
    
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