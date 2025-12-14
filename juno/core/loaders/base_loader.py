"""Provides the abstract base loader class for reading data files into DataFrames."""

import io
import json
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Union

import pandas as pd


class BaseLoader(ABC):
    """Base class for file loaders."""
    
    def __init__(self, source: Union[str, Path, io.IOBase]):
        """
        Args:
            source: File path (str/Path) or file-like object
        """
        if isinstance(source, (str, Path)):
            self.path = Path(source)
            self.file_obj = None
        else:
            self.path = None
            self.file_obj = source
    
    def load(self) -> pd.DataFrame:
        """Load data from source."""
        if self.path:
            with open(self.path, 'r', encoding='utf-8') as f:
                return self._load_from_file(f)
        else:
            if hasattr(self.file_obj, 'seek'):
                self.file_obj.seek(0)
            return self._load_from_file(self.file_obj)
    
    @abstractmethod
    def _load_from_file(self, file_handle) -> pd.DataFrame:
        """Load from open file handle. Subclasses implement."""
        pass
    
    def _load_json(self, file_handle, expect_list: bool = True):
        """Helper: Load and validate JSON."""
        try:
            data = json.load(file_handle)
        except json.JSONDecodeError as e:
            raise self._error_class(f"Invalid JSON: {e}") from e
        
        if expect_list and not isinstance(data, list):
            raise self._error_class("JSON must contain a top-level list")
        
        if expect_list and not data:
            raise self._error_class("JSON list cannot be empty")
        
        return data
    
    @property
    @abstractmethod
    def _error_class(self):
        """Return the exception class for this loader."""
        pass