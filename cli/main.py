"""Command-line interface for Soda segmentation analysis."""

import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from soda.core.config import OrchestrationConfig, RulesConfig
from soda.core.encoders.compact_encoder import CompactArrayEncoder
from soda.core.loaders.codebook_loader import CodebookLoader
from soda.core.loaders.outcomes_loader import OutcomesLoader
from soda.core.loaders.respondents_loader import RespondentsLoader
from soda.core.loaders.responses_loader import ResponsesLoader
from soda.core.models import Codebook, Outcomes, SegmentModel, SegmentModelWithAssignments
from soda.core.orchestrator import Orchestrator
from soda.core.schema import DataKey
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
        # Convert basic model to full model (no assignments, but compatible)
        basic_model = SegmentModel.model_validate(data)
        segment_model = SegmentModelWithAssignments(
            segments=basic_model.segments,
            segment_assignments=None
        )
    
    # Enrich with outcomes if provided
    if args.outcomes:
        outcomes_loader = OutcomesLoader(args.outcomes)
        outcomes = outcomes_loader.load()
        segment_model = _enrich_with_outcomes(segment_model, outcomes)
    
    # Enrich with demographics if provided
    if args.demographics:
        if not args.codebook:
            raise ValueError("--codebook required when using --respondents")
        segment_model = _enrich_with_demographics(segment_model, args.demographics, args.codebook)
    
    # Save enriched segments
    output_file = args.output or args.segments_file
    with open(output_file, 'w') as f:
        data = segment_model.model_dump()
        json_data = CompactArrayEncoder().encode(data)
        f.write(json_data)
    
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

def _enrich_with_demographics(segment_model: SegmentModelWithAssignments, respondents_path: str, codebook_path: str) -> SegmentModelWithAssignments:
    """Add demographic distributions to segments."""
    
    # Load data using existing loaders
    respondents_loader = RespondentsLoader(path=respondents_path)
    respondents_df = respondents_loader.load()  # Returns pd.DataFrame
    
    codebook_loader = CodebookLoader(path=codebook_path)
    codebook = codebook_loader.load()  # Returns Codebook model
    
    # Ensure we have segment assignments
    if not segment_model.segment_assignments:
        raise ValueError("Segment assignments required for demographics enrichment")
    
    # Process each segment
    for segment in segment_model.segments:
        # Get respondent IDs for this segment from assignments
        respondent_ids = segment_model.segment_assignments.get_respondents(segment.segment_id)
        
        if not respondent_ids:
            print(f"Warning: No respondent IDs for segment {segment.segment_id}")
            segment.demographics = {}
            continue
        
        # Filter respondents DataFrame to this segment's respondents
        segment_respondents = respondents_df[
            respondents_df[DataKey.RESPONDENT_ID].isin(respondent_ids)
        ]
        
        if len(segment_respondents) == 0:
            print(f"Warning: No respondent data found for segment {segment.segment_id}")
            segment.demographics = {}
            continue
            
        # Calculate demographics for this segment
        demographics = _calculate_segment_demographics(segment_respondents, codebook)
        segment.demographics = demographics
    
    return segment_model


def _calculate_segment_demographics(segment_df: pd.DataFrame, codebook: Codebook) -> dict:
    """Calculate demographic distributions for a segment."""
    
    demographics = {}
    
    # Process only categorical dimensions
    for dimension in codebook.get_categorical_dimensions():
        # Check if dimension exists in respondents data
        if dimension.name not in segment_df.columns:
            print(f"Warning: Dimension {dimension.name} not found in respondents data")
            continue
            
        column_data = segment_df[dimension.name]
        
        # Convert numeric values to strings for codebook lookup
        string_data = column_data.astype(str)
        
        # Filter out missing codes if they exist
        if dimension.missing_codes:
            valid_data = string_data[~string_data.isin(dimension.missing_codes)]
        else:
            valid_data = string_data
        
        # Skip if no valid data
        if len(valid_data) == 0:
            print(f"Warning: No valid data for dimension {dimension.name} in segment")
            demographics[dimension.name] = {}
            continue
        
        # Calculate value counts and percentages
        value_counts = valid_data.value_counts()
        total = len(valid_data)
        
        # Map codes to labels and calculate percentages
        percentages = {}
        for code, count in value_counts.items():
            # Look up label in codebook options
            if dimension.options and code in dimension.options:
                label = dimension.options[code]
            else:
                label = f"Unknown ({code})"
                print(f"Warning: Code {code} not found in {dimension.name} options")
            
            percentage = round((count / total) * 100, 1)
            percentages[label] = percentage
        
        # Sort by percentage (highest first) for better readability
        sorted_percentages = dict(sorted(percentages.items(), key=lambda x: x[1], reverse=True))
        demographics[dimension.name] = sorted_percentages
    
    return demographics

def _enrich_with_demographics(segment_model: SegmentModelWithAssignments, respondents_path: str, codebook_path: str) -> SegmentModelWithAssignments:
    """Add demographic distributions to segments."""
    
    # Load data
    respondents_loader = RespondentsLoader(respondents_path)
    respondents_df = respondents_loader.load()
    
    codebook_loader = CodebookLoader(codebook_path)
    codebook = codebook_loader.load()
    
    # Check we have segment assignments
    if not segment_model.segment_assignments:
        raise ValueError("No segment assignments found - cannot enrich demographics")
    
    # For each segment
    for segment in segment_model.segments:
        print(f"Processing segment {segment.segment_id}")
        
        # Step 1: Get respondents in this segment
        respondent_ids = segment_model.segment_assignments.get_respondents(segment.segment_id)
        if not respondent_ids:
            print(f"  No respondents in segment {segment.segment_id}")
            segment.demographics = {}
            continue
        
        # Filter respondents to only those in this segment
        segment_respondents = respondents_df[respondents_df['respondentId'].isin(respondent_ids)]
        print(f"  Found {len(segment_respondents)} respondents")
        
        segment.demographics = {}
        
        # Step 2: For each categorical dimension, calculate percentages
        for dimension in codebook.dimensions:
            if dimension.type != "categorical":
                continue  # Skip text dimensions like D4
            
            print(f"    Processing {dimension.name} ({dimension.id})")
            
            # Get data for this dimension (e.g., D1, D2, D3)
            if dimension.id not in segment_respondents.columns:
                print(f"    Warning: {dimension.id} not found in data")
                continue
            
            dimension_data = segment_respondents[dimension.id]
            
            # Remove missing codes (e.g., "No Response")
            if dimension.missing_codes:
                # Convert missing codes to int for comparison
                missing_codes_int = [int(code) for code in dimension.missing_codes]
                valid_data = dimension_data[~dimension_data.isin(missing_codes_int)]
            else:
                valid_data = dimension_data
            
            if len(valid_data) == 0:
                segment.demographics[dimension.name] = {}
                continue
            
            # Step 3: Count values and convert to percentages
            value_counts = valid_data.value_counts()
            total = len(valid_data)
            
            # Step 4: Map codes to labels and calculate percentages
            percentages = {}
            for value, count in value_counts.items():
                # Look up the label for this value (e.g., 1 -> "Female")
                value_str = str(value)
                if dimension.options and value_str in dimension.options:
                    label = dimension.options[value_str]
                else:
                    label = f"Unknown ({value})"
                
                percentage = round((count / total) * 100, 1)
                percentages[label] = percentage
                print(f"      {label}: {percentage}%")
            
            # Sort by percentage (highest first)
            sorted_percentages = dict(sorted(percentages.items(), key=lambda x: x[1], reverse=True))
            segment.demographics[dimension.name] = sorted_percentages
    
    return segment_model

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