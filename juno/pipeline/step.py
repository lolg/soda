"""
Abstract base class for all pipeline steps.

Every pipeline step should inherit from this class and implement the `run` method,
which receives the pipeline context and returns the updated context after the step's
logic.

"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import ClassVar

from .context import Context


class Step(ABC):
    """Base class for all pipeline steps.
    
    Subclasses must implement the run() method to define step behavior.
    Optionally override the 'name' attribute for better logging/metrics.
    
    Attributes:
        name: Human-readable name for logs and metrics
    """
    
    name: ClassVar[str] = "step"

    @abstractmethod
    def run(self, ctx: Context) -> Context:
        """Execute the step's logic.
        
        Args:
            ctx: Pipeline context containing data and state
            
        Returns:
            Updated context after step execution
        """
        ...