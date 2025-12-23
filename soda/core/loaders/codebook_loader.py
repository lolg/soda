from loaders.base_loader import BaseLoader

from soda.core.models import Codebook, DimensionDefinition


class CodebookLoadError(Exception):
    pass


class CodebookLoader(BaseLoader):
    
    @property
    def _error_class(self):
        return CodebookLoadError
    
    def load(self) -> Codebook:
        """Load codebook directly as Pydantic model."""
        if self.path:
            with open(self.path, 'r', encoding='utf-8') as f:
                data = self._load_json(f, expect_list=True)
        else:
            if hasattr(self.file_obj, 'seek'):
                self.file_obj.seek(0)
            data = self._load_json(self.file_obj, expect_list=True)
        
        if not data:
            raise CodebookLoadError("Codebook is empty")
        
        try:
            # Create DimensionDefinition objects from JSON array
            dimensions = [DimensionDefinition(**item) for item in data]
            codebook = Codebook(dimensions=dimensions)
        except Exception as e:
            raise CodebookLoadError(f"Invalid codebook format: {e}") from e
        
        return codebook
    
    def _load_from_file(self, file_handle):
        """Not used - overridden by load()."""
        raise NotImplementedError("Use load() directly")