"""Tests for the Orchestrator and segmentation scoring logic."""

import pandas as pd

from juno.core.config import Constraint, OrchestrationConfig
from juno.core.models import SegmentationMetrics
from juno.core.orchestrator import Orchestrator, score_config
from juno.core.schema import DataKey, importance_col, satisfaction_col


def make_responses(n_respondents=30, n_outcomes=5):
    """Generate test response data."""
    data = {DataKey.RESPONDENT_ID: list(range(1, n_respondents + 1))}
    
    sat_pattern = [3, 4, 5, 2, 4]
    imp_pattern = [4, 5, 3, 5, 4]
    
    for i in range(1, n_outcomes + 1):
        sat_values = (sat_pattern * (n_respondents // len(sat_pattern) + 1))[:n_respondents]
        imp_values = (imp_pattern * (n_respondents // len(imp_pattern) + 1))[:n_respondents]
        
        data[satisfaction_col(i)] = sat_values
        data[importance_col(i)] = imp_values
    
    return pd.DataFrame(data)


def make_simple_config():
    """Create simple orchestration config."""
    return OrchestrationConfig(
        parameters={
            'num_segments': [2, 3],
            'random_state': [42, 43],
        },
        constraints=[],
        scoring={
            'silhouette_weight': 0.6,
            'balance_weight': 0.4
        }
    )


def make_constrained_config():
    """Create config with constraints."""
    return OrchestrationConfig(
        parameters={
            'num_segments': [2, 3, 4],
            'top_box_threshold': [3, 4],
        },
        constraints=[
            Constraint(
                type='less_than',
                left='top_box_threshold',
                right='num_segments'
            )
        ],
        scoring={
            'silhouette_weight': 0.7,
            'balance_weight': 0.3
        }
    )


def test_orchestrator_count_configs():
    """Test configuration counting."""
    config = make_simple_config()
    orchestrator = Orchestrator(config)
    
    # 2 num_segments × 2 random_state = 4 total
    assert orchestrator.count_configs() == 4


def test_orchestrator_count_with_constraints():
    """Test that count_configs returns total before filtering."""
    config = make_constrained_config()
    orchestrator = Orchestrator(config)
    
    # 3 num_segments × 2 thresholds = 6 total (before filtering)
    assert orchestrator.count_configs() == 6


def test_orchestrator_valid_config_count():
    """Test valid config count after filtering."""
    config = make_constrained_config()
    orchestrator = Orchestrator(config)
    
    # Only (4, 3) is valid: threshold=3 < num_segments=4
    assert orchestrator.get_valid_config_count() == 1


def test_orchestrator_constraint_validation():
    """Test constraint checking."""
    config = make_constrained_config()
    orchestrator = Orchestrator(config)
    
    # Valid: threshold < num_segments
    assert orchestrator._is_valid_config({
        'num_segments': 4,
        'top_box_threshold': 3
    }) is True
    
    # Invalid: threshold >= num_segments
    assert orchestrator._is_valid_config({
        'num_segments': 3,
        'top_box_threshold': 3
    }) is False
    
    assert orchestrator._is_valid_config({
        'num_segments': 2,
        'top_box_threshold': 4
    }) is False


def test_orchestrator_run_generator():
    """Test that run() yields results one at a time."""
    config = make_simple_config()
    orchestrator = Orchestrator(config)
    responses = make_responses(n_respondents=30, n_outcomes=5)
    
    # Consume generator
    results = []
    for result in orchestrator.run(responses):
        assert 'params' in result
        assert 'analyzer' in result
        assert 'metrics' in result
        assert 'score' in result
        results.append(result)
    
    # Should have 4 results (2×2 combinations)
    assert len(results) == 4


def test_orchestrator_run_all():
    """Test run_all returns sorted results."""
    config = make_simple_config()
    orchestrator = Orchestrator(config)
    responses = make_responses(n_respondents=30, n_outcomes=5)
    
    results = orchestrator.run_all(responses)
    
    # Should have 4 results (2×2 combinations)
    assert len(results) == 4
    
    # Each result should have required keys
    for result in results:
        assert 'params' in result
        assert 'analyzer' in result
        assert 'metrics' in result
        assert 'score' in result
        
        # Check params match expected values
        assert result['params']['num_segments'] in [2, 3]
        assert result['params']['random_state'] in [42, 43]
        
        # Check score is reasonable
        assert 0 <= result['score'] <= 1
    
    # Check results are sorted (descending)
    scores = [r['score'] for r in results]
    assert scores == sorted(scores, reverse=True)


def test_orchestrator_run_with_constraints():
    """Test that invalid configs are filtered out."""
    config = make_constrained_config()
    orchestrator = Orchestrator(config)
    responses = make_responses(n_respondents=30, n_outcomes=5)
    
    results = orchestrator.run_all(responses)
    
    # Only 1 valid config: (4, 3) where 3 < 4
    assert len(results) == 1
    
    # Result should satisfy constraint
    params = results[0]['params']
    assert params['top_box_threshold'] < params['num_segments']
    assert params['num_segments'] == 4
    assert params['top_box_threshold'] == 3


def test_orchestrator_get_best():
    """Test get_best returns highest scoring config."""
    config = make_simple_config()
    orchestrator = Orchestrator(config)
    responses = make_responses(n_respondents=30, n_outcomes=5)
    
    best = orchestrator.get_best(responses)
    
    # Should have all required keys
    assert 'params' in best
    assert 'analyzer' in best
    assert 'metrics' in best
    assert 'score' in best
    
    # Run all to compare
    all_results = orchestrator.run_all(responses)
    
    # Best should match highest score
    assert best['score'] == all_results[0]['score']
    assert best['params'] == all_results[0]['params']


def test_orchestrator_preserves_analyzer():
    """Test that orchestrator stores working analyzers."""
    config = make_simple_config()
    orchestrator = Orchestrator(config)
    responses = make_responses(n_respondents=30, n_outcomes=5)
    
    results = orchestrator.run_all(responses)
    
    # Each result should have a fitted analyzer
    for result in results:
        analyzer = result['analyzer']
        
        # Analyzer should be fitted and have model
        model = analyzer.model
        assert model is not None
        assert len(model.segments) == result['params']['num_segments']


def test_score_config_basic():
    """Test scoring function."""
    metrics = SegmentationMetrics(
        method='kmeans',
        k=3,
        random_state=42,
        silhouette_mean=0.4,  # 0.4 / 0.5 = 0.8
        silhouette_by_cluster=[0.35, 0.42, 0.43],
        cluster_sizes_pct=[30.0, 35.0, 35.0],  # Well balanced
        min_cluster_pct=30.0
    )
    
    weights = {'silhouette_weight': 0.6, 'balance_weight': 0.4}
    
    score = score_config(metrics, weights)
    
    # Silhouette component: 0.8 × 0.6 = 0.48
    # Balance component: 1.0 - (35-30)/100 = 0.95 × 0.4 = 0.38
    # Total: ~0.86
    assert 0.8 < score < 0.9


def test_score_config_imbalanced():
    """Test scoring penalizes imbalanced segments."""
    balanced_metrics = SegmentationMetrics(
        method='kmeans',
        k=3,
        random_state=42,
        silhouette_mean=0.3,
        silhouette_by_cluster=[0.3, 0.3, 0.3],
        cluster_sizes_pct=[33.0, 33.0, 34.0],  # Balanced
        min_cluster_pct=33.0
    )
    
    imbalanced_metrics = SegmentationMetrics(
        method='kmeans',
        k=3,
        random_state=42,
        silhouette_mean=0.3,  # Same silhouette
        silhouette_by_cluster=[0.3, 0.3, 0.3],
        cluster_sizes_pct=[10.0, 20.0, 70.0],  # Very imbalanced
        min_cluster_pct=10.0
    )
    
    weights = {'silhouette_weight': 0.6, 'balance_weight': 0.4}
    
    balanced_score = score_config(balanced_metrics, weights)
    imbalanced_score = score_config(imbalanced_metrics, weights)
    
    # Balanced should score higher
    assert balanced_score > imbalanced_score


def test_score_config_excellent_silhouette():
    """Test that silhouette > 0.5 caps at 1.0."""
    metrics = SegmentationMetrics(
        method='kmeans',
        k=3,
        random_state=42,
        silhouette_mean=0.7,  # Excellent (> 0.5)
        silhouette_by_cluster=[0.7, 0.7, 0.7],
        cluster_sizes_pct=[33.0, 33.0, 34.0],
        min_cluster_pct=33.0
    )
    
    weights = {'silhouette_weight': 1.0, 'balance_weight': 0.0}
    
    score = score_config(metrics, weights)
    
    # Should cap at 1.0 (0.7 / 0.5 = 1.4, but min(1.4, 1.0) = 1.0)
    assert score == 1.0