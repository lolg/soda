"""Command-line interface for Soda segmentation analysis."""

import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

from soda.core.config import OrchestrationConfig, RulesConfig
from soda.core.encoders.compact_encoder import CompactArrayEncoder
from soda.core.loaders.outcomes_loader import OutcomesLoader
from soda.core.loaders.responses_loader import ResponsesLoader
from soda.core.models import Outcomes, SegmentModel, SegmentModelWithAssignments
from soda.core.orchestrator import Orchestrator
from soda.core.segment_builder import SegmentBuilder
from soda.core.selection import SegmentationSelector

logging.basicConfig(
    level=logging.INFO,
    format='%(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog='soda',
        description='ODI segmentation analysis - discover outcome-based market segments'
    )
    
    # Add global options
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    
    # Create subcommands
    subparsers = parser.add_subparsers(
        dest='command',
        help='Available commands',
        required=True
    )
    
    # Segment command
    segment_parser = subparsers.add_parser(
        'segment',
        help='Run ODI segmentation analysis'
    )
    
    segment_parser.add_argument('responses', type=str, help='Path to responses.jsonl file')
    segment_parser.add_argument('--rules', type=str, default=None, help='Path to business rules YAML file')
    segment_parser.add_argument('-o', '--output', type=str, default='./output', help='Output directory (default: ./output)')

    enrich_parser = subparsers.add_parser('enrich', help='Enrich segments with additional data')
    enrich_parser.add_argument('segments_file', help='Path to segments.json file')
    enrich_parser.add_argument('--outcomes', type=str, help='Path to outcomes.json file')
    enrich_parser.add_argument('--respondents', help='Path to respondents.jsonl file')  
    enrich_parser.add_argument('--codebook', help='Path to codebook.json file (required with --respondents)')
    enrich_parser.add_argument('-o', '--output', type=str, default='./output', help='Output directory (default: ./output)')
    enrich_parser.set_defaults(func=cmd_enrich)
    
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


def cmd_segment(args):
    """Handle 'segment' command - full ODI segmentation pipeline."""
    
    # 1. Load data and rules
    logger.info(f"Loading responses from {args.responses}")
    responses_df = load_responses(args.responses)
    logger.info(f"Loaded {len(responses_df)} respondents")
    
    if args.rules:
        logger.info(f"Loading rules from {args.rules}")
        rules = RulesConfig.from_file(args.rules)
    else:
        logger.info("Using default rules")
        rules = RulesConfig.default()
    
    # 2. Orchestration (lightweight - config + metrics only)
    orchestrator = Orchestrator(rules.orchestration)
    all_results = orchestrator.run_all(responses_df)
    logger.info(f"Generated {len(all_results)} candidate solutions")
    
    # 3. Select the best solution based on the rules
    selector = SegmentationSelector(rules.selection_rules)
    recommended = selector.select_best(all_results)

    logger.info(f"Recommended configuration: {recommended['config'].num_segments} segments")

    # 4. Build final model and output JSON
    logger.info("Building final model for recommended configuration...")
    winning_config = recommended['config']
    segmenter = SegmentBuilder(winning_config)
    segmenter.fit(responses_df)
    
    # Output the full segment model as JSON
    
    output_path = Path(args.output)
    with open(output_path, 'w') as f:
        data = segmenter.model_with_assignments.model_dump()
        json = CompactArrayEncoder().encode(data)
        f.write(json)
    
    logger.info(f"Wrote final model: {output_path}")
    logger.info("Done")

def cmd_enrich(args):
    """Enrich segments with outcome descriptions and/or demographics."""
    
    # Load segments.json
    with open(args.segments_file, 'r') as f:
        segment_model = SegmentModelWithAssignments.model_validate_json(f.read())
    
    # Enrich with outcomes if provided
    if args.outcomes:
        outcomes_loader = OutcomesLoader(args.outcomes)
        outcomes = outcomes_loader.load()
        segment_model = _enrich_with_outcomes(segment_model, outcomes)
    
    # Enrich with demographics if provided
    if args.respondents:
        if not args.codebook:
            raise ValueError("--codebook required when using --demographics")
        segment_model = _enrich_with_demographics(segment_model, args.demographics, args.codebook)
    
    # Save enriched segments
    output_file = args.output or args.segments_file
    with open(output_file, 'w') as f:
        data = segment_model.model_dump()
        json = CompactArrayEncoder().encode(data)
        f.write(json)
    
    print(f"Enriched segments saved to {output_file}")

def _enrich_with_outcomes(segment_model: SegmentModelWithAssignments, outcomes: Outcomes) -> SegmentModel:
    """Add outcome descriptions to all zone outcomes."""
    
    for segment in segment_model.segments:
        for zone_name, zone_category in segment.zones.__dict__.items():
            for outcome in zone_category.outcomes:
                try:
                    outcome.description = outcomes.get_text(outcome.outcome_id)
                except ValueError:
                    print(f"Warning: No description found for outcome {outcome.outcome_id}")
                    outcome.description = f"Outcome {outcome.outcome_id} (description missing)"
    
    return segment_model

def _enrich_with_demographics(segment_model:SegmentModel, responses, codebook):
    raise NotImplementedError()

def main():
    args = parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Route to command handlers
    if args.command == 'segment':
        cmd_segment(args)
    elif args.command == 'enrich':
        cmd_enrich(args)     
    else:
        logger.error(f"Unknown command: {args.command}")
        sys.exit(1)


if __name__ == '__main__':
    main()