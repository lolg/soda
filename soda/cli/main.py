"""Command-line interface for Soda segmentation analysis."""

import argparse
import json
import logging
import sys
from pathlib import Path

from soda.api import enrich, segment
from soda.core.config import RulesConfig
from soda.core.models import Segment
from soda.core.encoders.compact_encoder import CompactArrayEncoder
from soda.core.loaders.codebook_loader import CodebookLoader
from soda.core.loaders.outcomes_loader import OutcomesLoader
from soda.core.loaders.respondents_loader import RespondentsLoader
from soda.core.loaders.responses_loader import ResponsesLoader
from soda.core.models import SegmentModelWithAssignments
from soda.api.name import name, NameSuggestions
from soda.api.strategy import strategy
from soda.api.report import report

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
    segment_parser = subparsers.add_parser('segment', help='Run ODI segmentation analysis')
    segment_parser.add_argument('responses', type=str, help='Path to responses.jsonl file')
    segment_parser.add_argument('--rules', type=str, default=None, help='Path to business rules YAML file')
    segment_parser.add_argument('-o', '--output', type=str, default='./output', help='Output directory (default: ./output)')

    # Enrich command
    enrich_parser = subparsers.add_parser('enrich', help='Enrich segments with additional data')
    enrich_parser.add_argument('segments_file', help='Path to segments.json file')
    enrich_parser.add_argument('--outcomes', type=str, help='Path to outcomes.json file')
    enrich_parser.add_argument('--demographics', help='Path to respondents.jsonl file')  
    enrich_parser.add_argument('--codebook', help='Path to codebook.json file (required with --demographics)') 
    enrich_parser.add_argument('--output', '-o', help='Output file (default: overwrite input)')
    enrich_parser.set_defaults(func=cmd_enrich)

    # Naming command
    name_parser = subparsers.add_parser('name', help='LLM-guided segment naming assignment')
    name_parser.add_argument('segments_file', help='Path to segments.json file that includes segments, outcome names, demographics')
    name_parser.add_argument('--rules', type=str, default=None, help='Path to business rules YAML')
    name_parser.add_argument('-o', '--output', type=str, default='synthesis.json', help='Output file')

    # Strategy command
    strategy_parser = subparsers.add_parser('strategy', help='Assign strategies to segments')
    strategy_parser.add_argument('segments_file', help='Path to segments.json with named segments')
    strategy_parser.add_argument('--rules', type=str, default='soda-rules.yaml', help='Path to rules YAML')
    strategy_parser.add_argument('-o', '--output', type=str, help='Output file (default: overwrite input)')

    # Report
    report_parser = subparsers.add_parser('report', help='Generate ODI segmentation report')
    report_parser.add_argument('segments_file', help='Path to segments.json with names and strategies')
    report_parser.add_argument('-o', '--output', type=str, default='report.md', help='Output file (default: report.md)')

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
        data = segments.model_dump(exclude_none=True)
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
        data = segment_model.model_dump(exclude_none=True)
        json_data = CompactArrayEncoder().encode(data)
        f.write(json_data)
    
    print(f"Enriched segments saved to {output_file}")

def cmd_name(args):
    """Name segments interactively."""
    with open(args.segments_file, 'r') as f:
        data = json.load(f)
    
    segment_model = SegmentModelWithAssignments.model_validate(data)
    
    def on_input(suggestions: NameSuggestions, segment) -> str:
        """CLI callback - display options, get user input."""
        print(f"\n{'='*50}")
        print(f"Segment {segment.segment_id} ({segment.size_pct:.1f}%)")
        print(f"{'='*50}")
        print(f"\n{suggestions.summary}\n")
        for i, opt in enumerate(suggestions.options, 1):
            print(f"  [{i}] {opt}")
        return input("\n> ").strip()
    
    segment_model = name(segment_model, on_input)
    
    # Save
    output = args.output or args.segments_file
    with open(output, 'w') as f:
        f.write(CompactArrayEncoder().encode(segment_model.model_dump(exclude_none=True)))
    
    print(f"\nSaved to {output}")

def cmd_strategy(args):
    """Assign strategies to segments interactively."""
    with open(args.segments_file, 'r') as f:
        data = json.load(f)
    
    segment_model = SegmentModelWithAssignments.model_validate(data)

    if args.rules:
        logger.info(f"Loading rules from {args.rules}")
        rules = RulesConfig.from_file(args.rules)
    else:
        raise ValueError("Rules must be provided for strategy analysis.")
    
    def on_question(text: str, segment: Segment) -> bool:
        """CLI callback - ask viability question."""
        print(f"\n[{segment.name}]")
        print(f"  {text}")
        answer = input("  (y/n) > ").strip().lower()
        return answer in ('y', 'yes')
    
    def on_choice(viable: list[str], segment: Segment) -> str:
        """CLI callback - choose between viable strategies."""
        print(f"\n[{segment.name}] Multiple strategies are viable:")
        for i, s in enumerate(viable, 1):
            print(f"  [{i}] {s}")
        choice = input("\n> ").strip()
        if choice.isdigit() and 1 <= int(choice) <= len(viable):
            return viable[int(choice) - 1]
        return choice
    
    segment_model = strategy(segment_model, rules.strategies, on_question, on_choice)
    
    # Save
    output = args.output or args.segments_file
    with open(output, 'w') as f:
        f.write(CompactArrayEncoder().encode(segment_model.model_dump(exclude_none=True)))
    
    print(f"\nSaved to {output}")

def cmd_report(args):
    """Generate ODI segmentation report."""
    with open(args.segments_file, 'r') as f:
        data = json.load(f)
    
    segment_model = SegmentModelWithAssignments.model_validate(data)
    
    output_path = Path(args.output)
    report(segment_model, output_path)
    
    print(f"\nReport saved to {output_path}")

def main():
    args = parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Route to command handlers
    if args.command == 'segment':
        cmd_segment(args)
    elif args.command == 'enrich':
        cmd_enrich(args) 
    elif args.command == 'name':
        cmd_name(args) 
    elif args.command == 'strategy':
        cmd_strategy(args)
    elif args.command == 'report':
        cmd_report(args)     
    else:
        logger.error(f"Unknown command: {args.command}")
        sys.exit(1)


if __name__ == '__main__':
    main()