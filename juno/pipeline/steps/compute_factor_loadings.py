"""
    This step uses PCA (again) with the number of components.
    
    When we call:
    
    pca.fit_transform(importance_data_standardized), it would return
    importance pca scores in the form below:
     
    For 3 components it looks like this:
    
    | Respondent | PC1  | PC2  | PC3  |
    |------------|------|------|------|
    | 1          | 0.61 | 0.54 | 0.38 |
    | 2          | 0.52 | 0.34 | 0.52 |
    | 3          | 0.56 | 0.47 | 0.62 |
    
    Each principal component (PC1, PC2, PC3) is a *direction* in N-dimensional space.
    You can think of it as a vector that describes a pattern of how outcomes tend to
    vary together. Each respondent contributes a value (score) along that direction,
    showing how strongly their answers align with that underlying pattern.

    Remember we have a "cloud" of respondents in N-dimensional space where each
    axis is an importance feature, OutcomeImportance_1, OutcomeImportance_2 etc..

    The loading matrix, on the other hand, tells us how strongly each outcome
    contributes to each principal component. Large positive or negative loadings
    mean that outcome helps define the pattern represented by that component.
    
    | Outcome            | PC1  | PC2 | PC3   |
    |--------------------|------|-----|-------|
    | OutcomeImportance1 | 0.21 | 0.21 | 0.18 |
    | OutcomeImportance2 | 0.22 | 0.23 | 0.22 |
    | OutcomeImportance3 | 0.36 | 0.67 | 0.32 |
    
    In short:
        - principal component scores → show how respondents align with each underlying pattern.
        - loading_matrix → shows which outcomes define those patterns.
    
    We don't need the principal component scores, so we only return the loading_matrix.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import ClassVar

import pandas as pd
from sklearn.decomposition import PCA

from juno.core.schema import primary_component_col
from juno.pipeline.context import Context
from juno.pipeline.keys import Key
from juno.pipeline.step import Step

logger = logging.getLogger(__name__)


def _determine_loadings(
    imp_std: pd.DataFrame,
    n_components: int) -> pd.DataFrame:

    if imp_std.columns.empty:
        raise ValueError("Cannot determine loadings from an empty data frame")
    
    if n_components == 0:
        raise ValueError("The number of components must be greater than one in order to determine the loadings")

    logger.debug(
        f"Starting PCA loadings computation: {n_components} components from {imp_std.shape[1]} standardized importance features (samples: {imp_std.shape[0]})"
    )

    pca = PCA(n_components=n_components)
    pca.fit_transform(imp_std)

    loading_matrix = pd.DataFrame(
        pca.components_.T,
        index=imp_std.columns,
        columns=[primary_component_col(i+1) for i in range(n_components)]
    )

    logger.debug(
        f"Loadings matrix computed: shape {loading_matrix.shape} "
        f"({loading_matrix.shape[0]} outcomes x {loading_matrix.shape[1]} components)"
    )

    return loading_matrix


@dataclass
class ComputeFactorLoadings (Step):
    """
    Pipeline step to determine the loadings, this will tell us how much each
    importance value contributes to each primary component:
    """

    name:ClassVar[str] = "determine_loadings"
    
    def run(self, ctx:Context) -> Context:
        
        imp_std = ctx.require_table(Key.DERIVED_TABLE_IMPORTANCE_STD)
        n_components = ctx.require_state(Key.STATE_PARAM_N_COMPONENTS)

        loadings = _determine_loadings(imp_std, n_components)
        ctx.add_table(Key.DERIVED_TABLE_PCA_LOADINGS, loadings)

        return ctx