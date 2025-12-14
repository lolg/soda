"""
Pipeline runner that executes steps sequentially and records per-step
timing metrics.

This module provides the main function for advancing a pipeline through
its ordered steps, updating the context and capturing how long each step
takes to run.
"""

from __future__ import annotations

import logging
import time
from typing import Dict, Iterable

from .context import Context
from .step import Step

logger = logging.getLogger(__name__)


def run_pipeline(ctx: Context, steps: Iterable[Step]) -> Context:
    """Execute pipeline steps in order and record timing metrics."""
    metrics: Dict[str, float] = {}

    for step in steps:
        t0 = time.perf_counter()

        try:
            ctx = step.run(ctx)
        except Exception as e:
            logger.error(f"Step {step.name} failed: {e}")
            raise

        if ctx is None:
            raise ValueError(f"Step {step.name} returned None")
    
        # Get step name (use 'name' attribute if available, otherwise class name)
        step_name = getattr(step, "name", step.__class__.__name__)
        
        # Calculate elapsed time in milliseconds
        elapsed_seconds = time.perf_counter() - t0
        elapsed_ms = elapsed_seconds * 1000.0
        elapsed_ms_rounded = round(elapsed_ms, 2)
        
        # Store timing metric
        metric_key = f"{step_name}.ms"
        metrics[metric_key] = elapsed_ms_rounded

    # Log all metrics at the end
    if metrics:
        logger.debug("Pipeline execution metrics:")
        for key, value in metrics.items():
            logger.debug(f"  {key}: {value}ms")
        total_ms = sum(metrics.values())
        logger.debug(f"  Total execution time: {total_ms:.2f}ms")

    return ctx