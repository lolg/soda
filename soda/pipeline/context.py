"""Core pipeline context for managing data flow."""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

import pandas as pd


@dataclass
class Context:
    """A lightweight pipeline context.

    Attributes:
        responses: The main DataFrame flowing through the pipeline
        tables: Named side artifacts (e.g., 'loadings', 'segment_sizes')
        state: Key/value metadata (params, metrics, timings, etc.)
    """

    responses: pd.DataFrame = None
    tables: Dict[str, pd.DataFrame] = field(default_factory=dict)
    state: Dict[str, Any] = field(default_factory=dict)

    # State methods

    def get_state(self, key: str, default: Any = None) -> Any:
        return self.state.get(key, default)

    def set_state(self, key:str, value:Any) -> Any:
        if key in self.state:
            raise KeyError(f"State key '{key}' already exists")

        if value is None:
            raise KeyError(f"State value cannot be None")
            
        self.state[key] = value

    def require_state(self, key: str) -> Any:
        if key not in self.state:
            raise KeyError(f"Required state key '{key}' not found in context")
        return self.state[key]

    def has_state(self, key: str) -> bool:
        return key in self.state

    # Table methods

    def get_table(
        self, key: str, default: Optional[pd.DataFrame] = None
    ) -> Optional[pd.DataFrame]:
        return self.tables.get(key, default)

    def require_table(self, key: str) -> pd.DataFrame:
        if key not in self.tables:
            raise KeyError(f"Required table key '{key}' not found in context")
        return self.tables[key]

    def has_table(self, key: str) -> bool:
        return key in self.tables

    # Primary methods

    def require_primary(self) -> pd.DataFrame:
        if self.responses is None:
            raise ValueError("Primary DataFrame is not set (value is None)")
        if not isinstance(self.responses, pd.DataFrame):
            raise TypeError(f"Primary must be a pandas DataFrame, got {type(self.responses)}")
        if self.responses.empty:
            raise ValueError("Primary DataFrame is empty")
        return self.responses

    def set_primary(self, df: Any) -> None:
        if not isinstance(df, pd.DataFrame):
            raise TypeError(f"primary must be a pandas DataFrame, got {type(df)}")
        self.responses = df

    def add_table(self, key: str, df: Any) -> None:
        if not isinstance(df, pd.DataFrame):
            raise TypeError(f"Table must be a pandas DataFrame, got {type(df)}")
        self.tables[key] = df
