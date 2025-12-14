"""Command-line interface for Juno segmentation analysis."""

import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

from juno.core.config import OrchestrationConfig
from juno.core.loaders.responses_loader import ResponsesLoader
from juno.core.orchestrator import Orchestrator

logging.basicConfig(
    level=logging.INFO,
    format='%(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog='juno',
        description='ODI segmentation analysis - discover outcome-based market segments'
    )
    
    parser.add_argument(
        'responses',
        type=str,
        help='Path to responses.jsonl file'
    )
    
    parser.add_argument(
        '-c', '--config',
        type=str,
        default=None,
        help='Path to orchestration config JSON (optional,'
         'uses defaults if not provided)'
    )
    
    parser.add_argument(
        '-o', '--output',
        type=str,
        default='./output',
        help='Output directory (default: ./output)'
    )
    
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    
    return parser.parse_args()


def load_responses(path: str):
    """Load responses from JSONL file."""
    loader = ResponsesLoader(path)
    return loader.load()


def load_config(path: str | None) -> OrchestrationConfig:
    """Load config from file or return defaults."""
    if path:
        logger.info(f"Loading config from {path}")
        return OrchestrationConfig.from_json(path)
    else:
        logger.info("Using default configuration")
        return OrchestrationConfig.default()


def write_outputs(output_dir: Path, results: dict[int, dict], responses_path: str):
    """Write segment models and summary to output directory."""
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Build summary
    summary = {
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'input_file': responses_path,
        'solutions': []
    }
    
    best_score = -1
    recommended_k = None
    
    # Write individual segment models and build summary
    for k in sorted(results.keys()):
        result = results[k]
        model = result['analyzer'].model
        metrics = result['metrics']
        score = result['score']
        
        # Write segment model
        model_path = output_dir / f'segments_{k}.json'
        with open(model_path, 'w') as f:
            f.write(model.model_dump_json(indent=2))
        
        logger.info(f"Wrote {model_path}")
        
        # Add to summary
        solution_info = {
            'num_segments': k,
            'silhouette_score': round(metrics.silhouette_mean, 4),
            'segment_sizes': [round(s, 1) for s in metrics.cluster_sizes_pct],
            'combined_score': round(score, 4),
            'output_file': f'segments_{k}.json'
        }
        summary['solutions'].append(solution_info)
        
        # Track best
        if score > best_score:
            best_score = score
            recommended_k = k
    
    summary['recommended'] = recommended_k
    
    # Write summary
    summary_path = output_dir / 'summary.json'
    with open(summary_path, 'w') as f:
        json.dump(summary, f, indent=2)
    
    logger.info(f"Wrote {summary_path}")


def main():
    args = parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Load inputs
    logger.info(f"Loading responses from {args.responses}")
    responses_df = load_responses(args.responses)
    logger.info(f"Loaded {len(responses_df)} respondents")
    
    config = load_config(args.config)
    
    # Run orchestration
    orchestrator = Orchestrator(config)
    total_configs = orchestrator.get_valid_config_count()
    logger.info(f"Running {total_configs} configurations...")
    
    results = orchestrator.get_best_per_segment_count(responses_df)
    
    logger.info(f"Found best solutions for {len(results)} segment counts")
    
    # Write outputs
    output_dir = Path(args.output)
    write_outputs(output_dir, results, args.responses)
    
    logger.info("Done")


if __name__ == '__main__':
    main()