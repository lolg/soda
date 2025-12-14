"""
    PCA looks for patterns of correlation among outcomes. In plain terms,
    it's like asking:
    
    “Are there groups of outcomes that tend to rise and fall together
    across respondents?”
    
    When many outcomes move together, they likely reflect the same underlying
    *theme* or *dimension*. PCA finds these themes automatically by identifying
    directions (called “components”) in the data where responses vary the most.
    
    Example interpretation:
    
    | Component | Underlying Theme            | Outcomes that load strongly |
    |-----------|-----------------------------|-----------------------------|
    | PC1       | “Ease of use / convenience” | 3, 5, 9, 14, 27             |
    | PC2       | “Speed / efficiency”        | 2, 7, 10, 11, 19            |
    
    So each PCA component corresponds to a cluster of related outcomes—
    outcomes that customers jointly rate as important (or not). This helps
    remove noise and redundancy from the data.

    Visual intuition:
    
    Imagine we had 3 outcomes (3 features). We can plot them in 3D space,
    where each point represents a respondent’s ratings on those 3 outcomes.
    PCA then finds the vector (a line through the origin) that passes through
    the direction of greatest variance—the “longest stretch” of the data cloud.
    
    The first component (PC1) captures that main direction of variation.
    The second component (PC2) is drawn perpendicular to the first and
    captures the next largest pattern.
    
    Outcomes that lie close to the same direction as a component “load” strongly
    on it, meaning they contribute most to that underlying theme.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import ClassVar

import numpy as np
import pandas as pd
from sklearn.decomposition import PCA

from juno.pipeline.context import Context
from juno.pipeline.keys import Key
from juno.pipeline.step import Step

logger = logging.getLogger(__name__)

def _components_using_kaiser(pca : PCA) -> int:

    # Kaiser rule: eigenvalue > 1

    eigenvalues = pca.explained_variance_
    number_of_components = np.sum(eigenvalues > 1)

    return int(number_of_components)

def _components_using_variance(pca : PCA) -> int:

     # Keep components that explain at least 80% of variance

    explained_variance_ratio = pca.explained_variance_ratio_

    cumsum = np.cumsum(explained_variance_ratio)
    number_of_components = np.argmax(cumsum >= 0.8) + 1

    return number_of_components

def _determine_components(imp_data : pd.DataFrame, method: str = "kaiser") -> int:
    """
    After we fit PCA (with no limit on components), we get a set of eigenvalues
    — one per component.  Each eigenvalue tells us how much variance that
    component explains.
     
    Because each original variable (outcome) was standardized to have
    variance = 1.
    So a principal component with eigenvalue > 1 (Kaiser rule) explains more
    variance than one original outcome, and thus is considered “worth keeping.”
    
    Another way of looking at it — again using the 3D example.
    Imagine plotting 3 outcomes: Outcome1, Outcome2, and Outcome3.
    Each respondent is a point in 3D space with coordinates (x, y, z),
    one for each outcome rating.
    
    The points form a cloud — stretched out like a blimp.
    The first principal component (PC1) is like pushing a skewer
    lengthwise through that blimp. It represents the single direction
    along which the data varies the most.
    
    Next, we rotate the entire coordinate system — all points and all axes —
    so that PC1 now lies along the X-axis. Each respondent's x-coordinate
    in this rotated system is their “score” on PC1 — how much they align
    with that underlying pattern of variation.
    
    We then look for the next principal component (PC2) in a direction
    perpendicular to PC1. This ensures that PC2 captures the largest
    possible remaining variance that has nothing to do with PC1.
    That's what “orthogonal” means here — independent directions of variation.
    """

    logger.debug(
        f"Starting component determination using method '{method}' on {len(imp_data.columns)} standardized features."
    )

    if imp_data.empty:
        raise ValueError("Cannot determine components from an empty DataFrame")

    pca = PCA()
    pca.fit_transform(imp_data)

    n_components = 0

    if method == 'kaiser':
        n_components = _components_using_kaiser(pca)
    elif method == 'variance_threshold':
        n_components = _components_using_variance(pca)
    else:
        raise ValueError(f"Unsupported method: {method}")

    logger.debug(
        f"Determined optimal number of components: {n_components} (method: '{method}')"
    )

    return n_components


@dataclass 
class ComputePCAComponents (Step):
    """
    Pipeline step for determining the number of components

    Components are the orthogonal vectors in N-dimensional space that capture
    the directions of maximum variance in the standardized importance data
    
    """

    name:ClassVar[str] = "determine_components"
    method: str = "kaiser"

    def run(self, ctx: Context) -> Context:

        imp_std = ctx.require_table(Key.DERIVED_TABLE_IMPORTANCE_STD)
        number_of_components = _determine_components(imp_std, self.method)
        ctx.set_state(Key.STATE_PARAM_N_COMPONENTS, number_of_components)

        return ctx