"""
Load outcomes from a JSON file.

The input file (outcomes.json) must contain a top-level list of outcome objects.
Example format:

[
  {
    "id": 1,
    "text": "Minimize the time..."
  },
  // ...
]

Each outcome object will be validated using the Outcome class.
"""

from soda.core.loaders.base_loader import BaseLoader
from soda.core.models import Outcome, Outcomes


class OutcomesLoadError(Exception):
    """Raised when outcome loading fails."""
    pass

class OutcomesLoader(BaseLoader):

    @property
    def _error_class(self):
        return OutcomesLoadError

    def load(self) -> Outcomes:
        """Load outcomes directly as Pydantic model."""
        if self.path:
            with open(self.path, 'r', encoding='utf-8') as f:
                data = self._load_json(f, expect_list=True)
        else:
            if hasattr(self.file_obj, 'seek'):
                self.file_obj.seek(0)
            data = self._load_json(self.file_obj, expect_list=True)
        
        try:
            outcomes = [Outcome(**o) for o in data]
        except Exception as e:
            raise OutcomesLoadError(f"Invalid outcome: {e}") from e
        
        return Outcomes(outcomes=outcomes)

    def _load_from_file(self, file_handle):
        """Not used - overridden by load()."""
        raise NotImplementedError("Use load() directly")