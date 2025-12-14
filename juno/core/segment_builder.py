"""
Tools and logic for running segmentation analysis pipelines on
survey respondent data.
"""

import numpy as np
import pandas as pd
from sklearn.metrics import silhouette_samples, silhouette_score

from juno.core.models import (
    Segment,
    SegmentAssignments,
    SegmentationMetrics,
    SegmentModel,
    SegmentOutcome,
)
from juno.core.schema import DataKey, Prefix
from juno.pipeline.context import Context
from juno.pipeline.keys import Key
from juno.pipeline.runner import run_pipeline
from juno.pipeline.step import Step
from juno.pipeline.steps.assign_segments import AssignSegments
from juno.pipeline.steps.characterize_segments import CharacterizeSegments
from juno.pipeline.steps.compute_factor_loadings import ComputeFactorLoadings
from juno.pipeline.steps.compute_opportunity_profiles import ComputeOpportunityProfiles
from juno.pipeline.steps.compute_pca_components import ComputePCAComponents
from juno.pipeline.steps.select_key_outcomes import SelectKeyOutcomes
from juno.pipeline.steps.standardize_importance import StandardizeImportance
from juno.pipeline.steps.validate_preflight import ValidatePreflight


class SegmentBuilder:
    """
    Segmenter orchestrates the segmentation pipeline and provides access to
    segment outputs.
    """
    def __init__(
        self,
        num_segments: int = 3,
        segment_method: str = "kmeans",
        pca_method: str = 'kaiser',
        random_state: int = 10,
        max_outcomes_per_component: int = 1,
        max_cross_loading: float = 0.30,
        min_primary_loading: float = 0.35,
        top_box_threshold: int = 4):

            if segment_method != "kmeans":
                raise ValueError(f"Only 'kmeans' supported, got '{segment_method}'")

            self.num_segments = num_segments
            self.segment_method = segment_method
            self.pca_method = pca_method
            self.random_state = random_state
            self.max_outcomes_per_component = max_outcomes_per_component
            self.max_cross_loading = max_cross_loading
            self.min_primary_loading = min_primary_loading
            self.top_box_threshold = top_box_threshold
            
            self._context = None
            self._fitted = False

    def fit(self, responses: pd.DataFrame):

        self._validate_responses(responses)

        self._context = Context()
        self._context.set_primary(responses)

        self._fitted = False

        try:

            steps:list = self._build_pipeline()
            run_pipeline(self._context, steps)
            self._fitted = True
        except Exception as e:
             raise RuntimeError(f"Segmentation failed: {e}") from e

    def _validate_responses(self, df: pd.DataFrame):
        """Validate input data format."""
        if not isinstance(df, pd.DataFrame):
            raise ValueError(f"responses_df must be DataFrame, got {type(df)}")
    
        if df.empty:
            raise ValueError("responses_df cannot be empty")
        
        # Check for required columns (satisfaction/importance)
        sat_cols = [c for c in df.columns if c.startswith(Prefix.SATISFACTION_PREFIX)]
        imp_cols = [c for c in df.columns if c.startswith(Prefix.IMPORTANCE_PREFIX)]
        
        if not sat_cols:
            raise ValueError("No satisfaction columns found")
        
        if not imp_cols:
            raise ValueError("No importance columns found")
        
        if len(sat_cols) != len(imp_cols):
            raise ValueError(
                f"Mismatch: {len(sat_cols)} satisfaction vs "
                f"{len(imp_cols)} importance columns"
            )
        
        if len(df) < self.num_segments:
            raise ValueError(
                f"Need at least {self.num_segments} respondents for "
                f"{self.num_segments} segments, "
                f"got {len(df)}"
            )

    @property
    def model(self) -> SegmentModel:
        self._check_fitted()

        df_segs = self._context.require_table(Key.GEN_TABLE_SEGMENT_OUTCOME_T2B)
        df_sizes = self._context.require_table(Key.GEN_TABLE_SEGMENT_SIZES)

        segments = []
    
        for _, size_row in df_sizes.iterrows():
            seg_id = int(size_row[DataKey.SEGMENT_ID])
        
            # Get outcomes for this segment
            segment_outcomes_df = df_segs[df_segs[DataKey.SEGMENT_ID] == seg_id]
        
            # Build outcome objects directly
            outcomes = [
                SegmentOutcome(
                    outcome_id=int(row[DataKey.OUTCOME_ID]),
                    sat_tb=round(float(row[DataKey.SAT_TB]), 1),
                    imp_tb=round(float(row[DataKey.IMP_TB]), 1),
                    opportunity=round(float(row[DataKey.OPP_TB]), 2)
                )
                for _, row in segment_outcomes_df.iterrows()
            ]
        
            # Build segment object directly
            segments.append(
                Segment(
                    segment_id=seg_id,
                    size_pct=float(size_row[DataKey.SIZE_PCT]),
                    outcomes=outcomes
                )
            )
    
        # Build model directly
        return SegmentModel(segments=segments)

    @property
    def metrics(self) -> SegmentationMetrics:
        self._check_fitted()

        with_opp_seg = self._context.require_table(Key.DERIVED_TABLE_RESPONSES_OPP)

        feat_cols = [c for c in with_opp_seg.columns if c.startswith(
            Prefix.OPPORTUNITY_PREFIX)]

        if not feat_cols:
            raise ValueError(
                "No Opportunity_* columns found to compute segmentation metrics.")

        X = with_opp_seg[feat_cols].to_numpy()
        y = with_opp_seg[DataKey.SEGMENT_ID].to_numpy()
        n = len(y)

        # silhouette (overall + per-cluster)
        if self.num_segments > 1 and n > self.num_segments:
            sil_overall = float(silhouette_score(X, y))
            sil_samples = silhouette_samples(X, y)
            sil_by_cluster = [
                float(np.mean(sil_samples[y == c])) if np.any(y == c) else float("nan")
                for c in range(self.num_segments)
            ]
        else:
            sil_overall = float("nan")
            sil_by_cluster = [float("nan")] * self.num_segments

        # cluster sizes
        counts = np.array([(y == c).sum() for c in range(self.num_segments)], dtype=float)
        sizes_pct = (counts / n * 100.0).tolist()
        min_cluster_pct = float(np.min(counts) / n * 100.0) if n > 0 else float("nan")

        return SegmentationMetrics(
            method=self.segment_method,
            k=self.num_segments,
            random_state=self.random_state,
            silhouette_mean=sil_overall,
            silhouette_by_cluster=sil_by_cluster,
            cluster_sizes_pct=sizes_pct,
            min_cluster_pct=min_cluster_pct
            )   

    @property
    def assignments(self) -> SegmentAssignments:
        self._check_fitted()

        with_opp_seg = self._context.require_table(Key.DERIVED_TABLE_RESPONSES_OPP)

        assignments_dict = dict(zip(
            with_opp_seg[DataKey.RESPONDENT_ID],
            with_opp_seg[DataKey.SEGMENT_ID]
        ))
        
        return SegmentAssignments(assignments=assignments_dict)

    def _check_fitted(self):
        if not self._fitted:
            raise ValueError("SegmentAnalyzer not fitted. Call fit() first.")

    def _build_pipeline(self) -> list[Step]:
        steps = []

        # Validation
        steps.append(ValidatePreflight(self.num_segments))

        # Feature engineering
        steps.append(StandardizeImportance())
        steps.append(ComputePCAComponents(self.pca_method))
        steps.append(ComputeFactorLoadings())
        steps.append(SelectKeyOutcomes(
            max_outcomes_per_component=self.max_outcomes_per_component,
            maximum_cross_loading=self.max_cross_loading,
            minimal_primary_loading=self.min_primary_loading))

        # Segmentation
        steps.append(ComputeOpportunityProfiles())
        steps.append(AssignSegments(
            num_segments=self.num_segments,
            random_state=self.random_state))

        steps.append(CharacterizeSegments(
            top_box_threshold=self.top_box_threshold))

        return steps
