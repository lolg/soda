"""Command-line interface for Soda segmentation analysis."""

import argparse
import json
import logging
import sys
from pathlib import Path

from api import enrich, segment
from soda.core.config import RulesConfig
from soda.core.encoders.compact_encoder import CompactArrayEncoder
from soda.core.loaders.codebook_loader import CodebookLoader
from soda.core.loaders.outcomes_loader import OutcomesLoader
from soda.core.loaders.respondents_loader import RespondentsLoader
from soda.core.loaders.responses_loader import ResponsesLoader
from soda.core.models import SegmentModelWithAssignments

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
    
    # Segment commands
    segment_parser = subparsers.add_parser('segment', help='Run ODI segmentation analysis')
    segment_parser.add_argument('responses', type=str, help='Path to responses.jsonl file')
    segment_parser.add_argument('--rules', type=str, default=None, help='Path to business rules YAML file')
    segment_parser.add_argument('-o', '--output', type=str, default='./output', help='Output directory (default: ./output)')

    # Enrich commands
    enrich_parser = subparsers.add_parser('enrich', help='Enrich segments with additional data')
    enrich_parser.add_argument('segments_file', help='Path to segments.json file')
    enrich_parser.add_argument('--outcomes', type=str, help='Path to outcomes.json file')
    enrich_parser.add_argument('--demographics', help='Path to respondents.jsonl file')  
    enrich_parser.add_argument('--codebook', help='Path to codebook.json file (required with --demographics)') 
    enrich_parser.add_argument('--output', '-o', help='Output file (default: overwrite input)') 
    enrich_parser.set_defaults(func=cmd_enrich)

    
    return parser.parse_args()


def cmd_segment(args):
    """Handle 'segment' command - full ODI segmentation pipeline."""
    
    # 1. Load data and rules
    logger.info(f"Loading responses from {args.responses}")
    loader = ResponsesLoader(args.responses)
    responses_df = loader.load()
    logger.info(f"Loaded {len(responses_df)} respondents")
    
    if args.rules:
        logger.info(f"Loading rules from {args.rules}")
        rules = RulesConfig.from_file(args.rules)
    else:
        logger.info("Using default rules")
        rules = RulesConfig.default()

    segments = segment(responses_df, rules, None)

    # Output the full segment model as JSON
    output_path = Path(args.output)
    with open(output_path, 'w') as f:
        data = segments.model_dump()
        json_data = CompactArrayEncoder().encode(data)
        f.write(json_data)
    
    logger.info(f"Wrote final model: {output_path}")
    logger.info("Done")

def cmd_enrich(args):
    """Enrich segments with outcome descriptions and/or demographics."""
    
    # Load segments - try SegmentModelWithAssignments first (for enriched files)
    with open(args.segments_file, 'r') as f:
        data = json.load(f)
    
    # Check if it has segment_assignments (full model) or not (basic model)
    if "segment_assignments" in data:
        segment_model = SegmentModelWithAssignments.model_validate(data)
    else:
        raise ValueError("Segment assignments missing from segment model")
    
    outcomes = None
    respondents_df = None
    codebook = None

    # Enrich with outcomes if provided
    if args.outcomes:
        outcomes_loader = OutcomesLoader(args.outcomes)
        outcomes = outcomes_loader.load()
        
    # Enrich with demographics if provided
    if args.demographics:
        if not args.codebook:
            raise ValueError("--codebook required when using --respondents")

         # Load data
        respondents_loader = RespondentsLoader(args.demographics)
        respondents_df = respondents_loader.load()
        
        codebook_loader = CodebookLoader(args.codebook)
        codebook = codebook_loader.load()

    segment_model = enrich(segment_model, outcomes, respondents_df, codebook)
    
    # Save enriched segments
    output_file = args.output or args.segments_file
    with open(output_file, 'w') as f:
        data = segment_model.model_dump()
        json_data = CompactArrayEncoder().encode(data)
        f.write(json_data)
    
    print(f"Enriched segments saved to {output_file}")


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