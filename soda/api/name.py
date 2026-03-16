from dataclasses import dataclass
from typing import Callable

from pydantic import BaseModel
from pydantic_ai import Agent, ModelRetry, RunContext

from soda.core.models import SegmentModelWithAssignments, Segment


class NameSuggestions(BaseModel):
    summary: str
    options: list[str]


@dataclass
class NamingDeps:
    """Dependencies injected into the agent's tools."""
    segment_model: SegmentModelWithAssignments
    on_input: Callable[[NameSuggestions, Segment], str]


INSTRUCTIONS = """You are an expert in Outcome-Driven Innovation (ODI) and Jobs-to-be-Done (JTBD) methodology.

You help product teams analyze and name market segments based on customer outcome data. You understand:
- Underserved outcomes indicate opportunity for differentiation
- Overserved outcomes indicate potential for disruption or cost reduction
- Segment demographics help characterize who the customers are

Name all unnamed segments. For each:
1. Call get_segments_overview to see which need naming
2. Call get_segment_details for the segment
3. Call get_cross_segment_comparison to see what is UNIQUE to this segment
4. Call request_user_choice with your suggestions
5. Call record_segment_name with the returned name

Names should capture what is UNIQUE about each segment — what distinguishes
it from the others. Use the cross-segment comparison to identify the
distinguishing outcomes. A good name references the specific outcomes that
make this segment different, not generic descriptions like "excessive" or
"insufficient."

Continue until all segments are named.
"""


naming_agent = Agent(
    'anthropic:claude-sonnet-4-20250514',
    deps_type=NamingDeps,
    instructions=INSTRUCTIONS,
)


@naming_agent.tool
def get_segments_overview(ctx: RunContext[NamingDeps]) -> dict:
    """Get overview of all segments showing which need naming."""
    return {
        "total_segments": len(ctx.deps.segment_model.segments),
        "segments": [
            {
                "id": s.segment_id,
                "size_pct": s.size_pct,
                "name": s.name,
                "needs_naming": s.name is None,
            }
            for s in ctx.deps.segment_model.segments
        ],
    }

@naming_agent.tool
def get_cross_segment_comparison(ctx: RunContext[NamingDeps], segment_id: int) -> dict:
    """Get what makes this segment UNIQUE vs other segments."""
    target = next(s for s in ctx.deps.segment_model.segments if s.segment_id == segment_id)
    others = [s for s in ctx.deps.segment_model.segments if s.segment_id != segment_id]

    other_underserved_ids = set()
    for s in others:
        for o in s.zones.underserved.outcomes:
            other_underserved_ids.add(o.outcome_id)

    other_overserved_ids = set()
    for s in others:
        for o in s.zones.overserved.outcomes:
            other_overserved_ids.add(o.outcome_id)

    unique_underserved = [
        {"description": o.description, "opportunity": round(o.opportunity, 1)}
        for o in sorted(target.zones.underserved.outcomes, key=lambda o: o.opportunity, reverse=True)
        if o.outcome_id not in other_underserved_ids
    ]

    unique_overserved = [
        {"description": o.description}
        for o in target.zones.overserved.outcomes
        if o.outcome_id not in other_overserved_ids
    ]

    return {
        "segment_id": segment_id,
        "unique_underserved": unique_underserved,
        "unique_overserved": unique_overserved,
        "shared_underserved_count": len(target.zones.underserved.outcomes) - len(unique_underserved),
        "shared_overserved_count": len(target.zones.overserved.outcomes) - len(unique_overserved),
    }

@naming_agent.tool
def get_segment_details(ctx: RunContext[NamingDeps], segment_id: int) -> dict:
    """Get detailed info about a segment including demographics and outcomes."""
    seg = next(s for s in ctx.deps.segment_model.segments if s.segment_id == segment_id)
    return {
        "segment_id": segment_id,
        "size_pct": seg.size_pct,
        "demographics": seg.demographics or {},
        "underserved_outcomes": [
            {"id": o.outcome_id, "description": o.description, "opportunity": round(o.opportunity, 1)}
            for o in sorted(seg.zones.underserved.outcomes, key=lambda o: o.opportunity, reverse=True)[:5]
        ],
        "overserved_outcomes": [
            {"id": o.outcome_id, "description": o.description, "opportunity": round(o.opportunity, 1)}
            for o in sorted(seg.zones.overserved.outcomes, key=lambda o: o.opportunity, reverse=True)[:5]
        ],
    }


@naming_agent.tool(retries=2)
def request_user_choice(
    ctx: RunContext[NamingDeps],
    segment_id: int,
    summary: str,
    options: list[str],
) -> str:
    """Present naming options to user and get their choice.

        You MUST provide EXACTLY 3 options.

        Names must use SPECIFIC outcome names from the data, not generic adjectives.
        Use the format: '[specific outcome], [specific outcome]'

        Each name should pair one high-need outcome with one low-priority outcome
        to capture the segment's distinctive tension — what they need AND what
        they don't value. Do not pair two outcomes from the same zone.

        GOOD examples (specific outcomes):
        'poor dog exercise, excess playgrounds'
        'strong signal, poor battery'
        'fast onboarding, slow support'
        'unmet off-leash need, surplus sports facilities'

        BAD examples (generic adjectives):
        'inadequate facilities, overbuilt amenities'
        'poor infrastructure, excess services'
        'lacking exercise space, over-designed'

        Each name must reference at least one specific outcome from the
        cross-segment comparison that is UNIQUE to this segment.
        Do NOT use full sentences, need statements, or persona descriptions.
        NEVER use demographic-based names (gender, age, location).
        NEVER use personal names (e.g. 'Brenda', 'Fred').
        NEVER use terms like underserved, overserved.

    Args:
        ctx: Agent context with dependencies.
        segment_id: The segment to name.
        summary: Brief summary of what makes this segment distinctive.
        options: List of exactly 3 name suggestions.

    Returns:
        The chosen name.
    """
    if len(options) != 3:
        raise ModelRetry(
            f"You must provide exactly 3 options, you provided {len(options)}. Try again."
        )

    suggestions = NameSuggestions(summary=summary, options=options)
    segment = next(
        s for s in ctx.deps.segment_model.segments if s.segment_id == segment_id
    )
    choice = ctx.deps.on_input(suggestions, segment)

    if choice.isdigit() and 1 <= int(choice) <= len(options):
        return options[int(choice) - 1]
    return choice


@naming_agent.tool
def record_segment_name(ctx: RunContext[NamingDeps], segment_id: int, name: str) -> str:
    """Record the final chosen name for a segment."""
    seg = next(s for s in ctx.deps.segment_model.segments if s.segment_id == segment_id)
    seg.name = name
    return f"Recorded name '{name}' for segment {segment_id}"


def name_segments(
    segment_model: SegmentModelWithAssignments,
    on_input: Callable[[NameSuggestions, Segment], str],
) -> SegmentModelWithAssignments:
    """Name unnamed segments."""
    unnamed = [s for s in segment_model.segments if s.name is None]
    if not unnamed:
        print("All segments already named. Nothing to do.")
        return segment_model

    print(f"{len(unnamed)} segment(s) need naming...")

    deps = NamingDeps(segment_model=segment_model, on_input=on_input)
    result = naming_agent.run_sync("Name all unnamed segments", deps=deps)
    print(f"Agent response: {result.output}")

    return segment_model