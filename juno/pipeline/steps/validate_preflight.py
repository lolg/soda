"""Validation step for minimum sample size and segmentation assumptions before main analysis."""

import logging
from dataclasses import dataclass
from typing import ClassVar

from juno.pipeline.context import Context
from juno.pipeline.step import Step

logger = logging.getLogger(__name__)


class InsufficientSampleError(ValueError):
    """Raised when n respondents is too small for the requested number of segments."""


def validate_segments(
    n_respondents: int,
    n_segments: int,
    min_per_segment: int = 60,
    strict: bool = False) -> None:
    """
    The rule of thumb (from the Strategyn/ODI literature) is to sample at least 60
    respondents for every segment that could get created. The goal is to ensure the
    smallest segment will contain a minimum of 30 respondents.
    """
    required = min_per_segment * n_segments

    if n_respondents < required:
        msg = (f"Only {n_respondents} respondents; a {n_segments}-segment solution "
               f"ideally needs ≥{required} (≈{min_per_segment}/segment).")
        if strict:
            raise InsufficientSampleError(msg)
        logger.warning(msg + " Proceeding, but segmentation stability may be weak.")
    else:
        logger.debug(
            f"Sample size OK for {n_segments} segments "
            f"(have {n_respondents}, need ≥{required})."
        )


@dataclass
class ValidatePreflight(Step):
    """Pipeline step: runs dataset-level preflight checks before segmentation."""
    name: ClassVar[str] = "validate_preflight"

    num_segments: int
    min_per_segment: int = 60
    strict: bool = False

    def run(self, ctx: Context) -> Context:

        logger.debug("Performing preflight validation")

        n = len(ctx.responses)
        validate_segments(n, self.num_segments, self.min_per_segment, self.strict)

        logger.debug("Preflight validation complete")

        return ctx