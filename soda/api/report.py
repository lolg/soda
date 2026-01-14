"""High-level report generation API."""

import asyncio
from pathlib import Path

from llama_index.core.tools import FunctionTool
from llama_index.llms.anthropic import Anthropic
from llama_index.core.agent import FunctionAgent
from soda.core.models import SegmentModelWithAssignments


SYSTEM_PROMPT = """You are an expert in Outcome-Driven Innovation (ODI) and Jobs-to-be-Done (JTBD) methodology.

You create clear, actionable strategic reports from segmentation analysis data. You understand:
- How to translate quantitative data into business insights
- How to write for executive audiences - concise, strategic, action-oriented
- ODI concepts: underserved = opportunity, overserved = cost reduction potential
- Strategy implications: differentiated, disruptive, dominant, sustaining
"""

REPORT_PROMPT = """Generate a strategic ODI segmentation report.

This is a TWO STEP process:
1. Call get_report_data ONCE to get all segment information

Report structure:
# ODI Segmentation Analysis Report
## Executive Summary
## Market Overview (include table: segment | size % | strategy)
## Segment Profiles (one subsection per segment with demographics, needs, strategy, actions)
## Cross-Segment Insights
## Next Steps

There is no need to call get_report_data multiple times.
"""


def create_report_tools(
    segment_model: SegmentModelWithAssignments,
    output_path: Path
) -> list[FunctionTool]:
    """Tools for report generation."""
    
    report_content: dict = {"markdown": None}
    
    def get_report_data() -> dict:
        """Get all segment data needed for the report."""
        print("[TOOL] get_report_data called")
        segments_data = []
        
        for seg in segment_model.segments:
            segments_data.append({
                "segment_id": seg.segment_id,
                "name": seg.name,
                "size_pct": seg.size_pct,
                "demographics": seg.demographics or {},
                "strategy": {
                    "name": seg.strategy.name if seg.strategy else None,
                    "reasoning": seg.strategy.reasoning if seg.strategy else None,
                    "viability_answers": seg.strategy.viability_answers if seg.strategy else {},
                    "warning": seg.strategy.warning if seg.strategy else None,
                } if seg.strategy else None,
                "zones": {
                    "underserved": {
                        "pct": seg.zones.underserved.pct,
                        "outcomes": [
                            {
                                "description": o.description,
                                "opportunity": o.opportunity,
                                "importance": o.imp_tb,
                                "satisfaction": o.sat_tb
                            }
                            for o in seg.zones.underserved.outcomes
                        ]
                    },
                    "overserved": {
                        "pct": seg.zones.overserved.pct,
                        "outcomes": [
                            {
                                "description": o.description,
                                "opportunity": o.opportunity,
                                "importance": o.imp_tb,
                                "satisfaction": o.sat_tb
                            }
                            for o in seg.zones.overserved.outcomes
                        ]
                    },
                    "table_stakes": {
                        "pct": seg.zones.table_stakes.pct,
                        "outcomes": [
                            {
                                "description": o.description,
                                "opportunity": o.opportunity
                            }
                            for o in seg.zones.table_stakes.outcomes
                        ]
                    },
                    "appropriate": {
                        "pct": seg.zones.appropriate.pct,
                        "outcomes": [
                            {
                                "description": o.description,
                                "opportunity": o.opportunity
                            }
                            for o in seg.zones.appropriate.outcomes
                        ]
                    }
                }
            })
        
        return {
            "total_segments": len(segment_model.segments),
            "segments": segments_data
        }
    
    def save_report(markdown: str) -> str:
        """Save the markdown report to file."""
        print(f"[TOOL] save_report called, length: {len(markdown)}")
        report_content["markdown"] = markdown
        
        with open(output_path, 'w') as f:
            f.write(markdown)
        
        return f"Report saved to {output_path}"
    
    return [
        FunctionTool.from_defaults(
            fn=get_report_data,
            name="get_report_data",
            description="Get all segment data needed for the report including demographics, zones, outcomes, and strategies"
        )
    ]


async def _report_async(
    segment_model: SegmentModelWithAssignments,
    output_path: Path
) -> Path:
    """Generate ODI segmentation report."""
    
    # Validate segments have required data
    for seg in segment_model.segments:
        if not seg.name:
            raise ValueError(f"Segment {seg.segment_id} has no name. Run 'soda name' first.")
        if not seg.strategy:
            raise ValueError(f"Segment {seg.segment_id} has no strategy. Run 'soda strategy' first.")
    
    print(f"Generating report for {len(segment_model.segments)} segments...")
    
    llm = Anthropic(model="claude-sonnet-4-20250514", max_tokens=8192)
    tools = create_report_tools(segment_model, output_path)
    
    agent = FunctionAgent(
        tools=tools,
        llm=llm,
        system_prompt=SYSTEM_PROMPT + "\n\n" + REPORT_PROMPT,
        verbose=True
    )
    
    response = await agent.run(
         user_msg="Generate the ODI segmentation report",
        max_iterations=5
    )

    if not output_path.exists():
        with open(output_path, 'w') as f:
            f.write(str(response))
    
    print(f"\nAgent: {response}")
    
    return output_path


def report(
    segment_model: SegmentModelWithAssignments,
    output_path: Path
) -> Path:
    """Generate ODI segmentation report. Sync wrapper."""
    return asyncio.run(_report_async(segment_model, output_path))