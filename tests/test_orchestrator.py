"""Tests for the Orchestrator and segmentation scoring logic."""

import pandas as pd

from soda.core.schema import DataKey, importance_col, satisfaction_col
from soda.core.config import OrchestrationConfig, Constraint
from soda.core.orchestrator import Orchestrator


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

def test():
    pass


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
        assert 'config' in result
        assert 'params' in result
        assert 'metrics' in result
        '''
        'config': segment_config,      
        'params': orchestration_params,    
        'metrics': segmenter.metrics
        '''
        
        # Check params match expected values
        assert result['params']['num_segments'] in [2, 3]
        assert result['params']['random_state'] in [42, 43]


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