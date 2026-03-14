"""High-level persona building API."""

import asyncio
from datetime import datetime, timezone
from typing import Callable

from llama_index.core.agent.workflow import AgentWorkflow
from llama_index.core.tools import FunctionTool
from llama_index.llms.anthropic import Anthropic

from soda.core.models import SegmentModelWithAssignments, Segment, SegmentPersona


SYSTEM_PROMPT = """You are an expert in Outcome-Driven Innovation (ODI) and Jobs-to-be-Done (JTBD) methodology.

You build data-driven personas for market segments using quantitative outcome data. You follow
the Ulwick ODI methodology strictly:

- A persona describes the UNIQUE needs-based characteristics of a segment: why it exists,
  why it differs from others.
- Every claim must be DIRECTLY SUBSTANTIATED by the data. Do not infer motivations, attitudes,
  or behaviours beyond what the outcome scores and demographics show.
  BAD: "They view parks as spaces for their pets" (inference)
  GOOD: "Underserved on dog exercise area (17.5) and off-leash dog exercise (16.4)" (data)
- Underserved outcomes = unmet needs = differentiation opportunity
- Overserved outcomes = disruption / cost-reduction opportunity

NAMING RULES:
- Context-based: describe the outcome gap (e.g. "unhealthy gums, large filling",
  "underserved: dog facilities & infrastructure")
- Or needs-based: describe the segment's position (e.g. "the underserved segment",
  "overserved, no unmet needs")
- Names MUST be substantiable — every word must trace to a data point
- NEVER use demographic labels as names (e.g. "suburban women", "active seniors")
- NEVER use person names (e.g. "Brenda", "Fred")
- NEVER infer user types (e.g. "dog owners", "fitness enthusiasts") — the data shows
  outcome scores, not who people are
"""

PERSONA_PROMPT = """You build ODI personas for market segments. Work through ALL segments needing personas.

LANGUAGE RULES — apply to ALL persona fields:
- State only what the data shows. Use outcome descriptions and scores directly.
- Do not infer motivations ("they want...", "they value...", "they view...").
  Instead: "underserved on X (opp: 17.5)" or "overserved on Y, indicating low priority".
- Do not assign identity labels ("dog owners", "fitness enthusiasts", "families").
  Instead: describe the outcome pattern ("high unmet need for dog exercise facilities").
- Reference opportunity scores and zone percentages as evidence.

PERSONA STRUCTURE:
1. SIZE: Segment size as percentage and relative rank (largest/smallest).
2. UNMET NEEDS: List the uniquely underserved outcomes with opportunity scores.
   If no underserved outcomes: state this explicitly and describe the overserved pattern.
3. OVERSERVED: List uniquely overserved outcomes — what this segment does not prioritise.
4. DEMOGRAPHICS: Factual summary of demographic skews vs the overall population.
5. NARRATIVE: 2-4 sentences explaining why this segment is distinct, referencing
   only the outcome patterns and demographic data. No inferences.
6. NAME: A short label derived directly from the outcome pattern.
   - For segments WITH underserved outcomes: "underserved: [top outcome themes]"
     e.g. "underserved: dog facilities & infrastructure"
   - For segments WITHOUT underserved outcomes: describe what they ARE overserved on.
     e.g. "overserved: playgrounds & sporting amenities", "satisfied: all recreation needs met"
   - The name must be SPECIFIC to this segment's data — never use a generic label.
   - BAD: "overserved, no unmet needs" (generic, says nothing about the segment)
   - GOOD: "overserved: children's play & sports facilities" (specific to the data)

For each segment:
1. Call get_segments_overview to see which need personas
2. Call get_segment_details for the segment's full outcome and demographic data
3. Call get_cross_segment_comparison to understand what is UNIQUE to this segment
4. Draft the persona following the structure and language rules above
5. Call present_persona_draft — REQUIRED to get user approval
6. Call record_persona with the final persona (using the user's name if they provided one)

You MUST call present_persona_draft before record_persona. The user must review every persona.

Continue until all segments have personas."""


def create_persona_tools(
    segment_model: SegmentModelWithAssignments,
    on_review: Callable[[SegmentPersona, Segment], str]
) -> list[FunctionTool]:
    """Tools for persona building phase."""

    # Enforce that present_persona_draft is called before record_persona
    _persona_presented: dict[int, bool] = {}

    def get_segments_overview() -> dict:
        """Get overview of all segments — which need personas."""
        return {
            "total_segments": len(segment_model.segments),
            "segments": [
                {
                    "id": s.segment_id,
                    "size_pct": s.size_pct,
                    "name": s.name,
                    "has_persona": s.persona is not None,
                    "needs_persona": s.persona is None
                }
                for s in segment_model.segments
            ]
        }

    def get_segment_details(segment_id: int) -> dict:
        """Get comprehensive data for persona building."""
        seg = next(s for s in segment_model.segments if s.segment_id == segment_id)

        # Relative size context
        sizes = sorted([s.size_pct for s in segment_model.segments], reverse=True)
        rank = sizes.index(seg.size_pct) + 1
        if rank == 1:
            size_context = "largest segment"
        elif rank == len(sizes):
            size_context = "smallest segment"
        else:
            size_context = f"#{rank} by size"

        # ALL outcomes sorted by opportunity (not limited to top 5)
        underserved = sorted(
            seg.zones.underserved.outcomes, key=lambda o: o.opportunity, reverse=True
        )
        overserved = sorted(
            seg.zones.overserved.outcomes, key=lambda o: o.opportunity, reverse=True
        )

        return {
            "segment_id": segment_id,
            "size_pct": seg.size_pct,
            "size_context": size_context,
            "zone_profile": {
                "underserved_pct": seg.zones.underserved.pct,
                "overserved_pct": seg.zones.overserved.pct,
                "table_stakes_pct": seg.zones.table_stakes.pct,
                "appropriate_pct": seg.zones.appropriate.pct,
            },
            "demographics": seg.demographics or {},
            "underserved_outcomes": [
                {"id": o.outcome_id, "description": o.description, "opportunity": o.opportunity}
                for o in underserved
            ],
            "overserved_outcomes": [
                {"id": o.outcome_id, "description": o.description, "opportunity": o.opportunity}
                for o in overserved
            ],
        }

    def get_cross_segment_comparison(segment_id: int) -> dict:
        """Get what makes this segment UNIQUE vs other segments."""
        target = next(s for s in segment_model.segments if s.segment_id == segment_id)
        others = [s for s in segment_model.segments if s.segment_id != segment_id]

        # Outcomes underserved ONLY in this segment
        other_underserved_ids = set()
        for s in others:
            for o in s.zones.underserved.outcomes:
                other_underserved_ids.add(o.outcome_id)

        unique_underserved = [
            {"id": o.outcome_id, "description": o.description, "opportunity": o.opportunity}
            for o in sorted(target.zones.underserved.outcomes, key=lambda o: o.opportunity, reverse=True)
            if o.outcome_id not in other_underserved_ids
        ]

        # Outcomes overserved ONLY in this segment
        other_overserved_ids = set()
        for s in others:
            for o in s.zones.overserved.outcomes:
                other_overserved_ids.add(o.outcome_id)

        unique_overserved = [
            {"id": o.outcome_id, "description": o.description, "opportunity": o.opportunity}
            for o in sorted(target.zones.overserved.outcomes, key=lambda o: o.opportunity, reverse=True)
            if o.outcome_id not in other_overserved_ids
        ]

        # Shared outcomes (underserved in both this and other segments)
        shared_underserved = [
            {"id": o.outcome_id, "description": o.description, "opportunity": o.opportunity}
            for o in sorted(target.zones.underserved.outcomes, key=lambda o: o.opportunity, reverse=True)
            if o.outcome_id in other_underserved_ids
        ]

        return {
            "segment_id": segment_id,
            "unique_underserved": unique_underserved,
            "unique_overserved": unique_overserved,
            "shared_underserved": shared_underserved,
            "total_underserved": len(target.zones.underserved.outcomes),
            "total_overserved": len(target.zones.overserved.outcomes),
            "unique_underserved_count": len(unique_underserved),
            "unique_overserved_count": len(unique_overserved),
        }

    def present_persona_draft(
        segment_id: int,
        name: str,
        size_summary: str,
        needs_summary: str,
        overserved_summary: str,
        demographics_summary: str,
        narrative: str,
    ) -> str:
        """Present the complete persona draft to the user for review. REQUIRED before recording."""
        seg = next(s for s in segment_model.segments if s.segment_id == segment_id)

        # Build a temporary SegmentPersona for the callback display
        draft = SegmentPersona(
            name=name,
            size_summary=size_summary,
            needs_summary=needs_summary,
            overserved_summary=overserved_summary if overserved_summary else None,
            demographics_summary=demographics_summary,
            narrative=narrative,
            created_at=datetime.now(timezone.utc).isoformat(),
            source="draft",
        )

        # Call the user review callback
        response = on_review(draft, seg)

        # Track that this segment had its persona presented
        _persona_presented[segment_id] = True

        if not response or response.lower() == "approve":
            return f"User APPROVED persona for segment {segment_id} with name '{name}'"
        else:
            return f"User provided alternative name for segment {segment_id}: '{response}'"

    def record_persona(
        segment_id: int,
        name: str,
        size_summary: str,
        needs_summary: str,
        overserved_summary: str,
        demographics_summary: str,
        narrative: str,
        user_approved: bool,
    ) -> str:
        """Record the final persona for a segment. Fails if present_persona_draft was not called first."""
        if not _persona_presented.get(segment_id):
            return f"ERROR: Cannot record persona for segment {segment_id} — present_persona_draft was not called first. You MUST present the draft to the user before recording."

        seg = next(s for s in segment_model.segments if s.segment_id == segment_id)

        seg.persona = SegmentPersona(
            name=name,
            size_summary=size_summary,
            needs_summary=needs_summary,
            overserved_summary=overserved_summary if overserved_summary else None,
            demographics_summary=demographics_summary,
            narrative=narrative,
            created_at=datetime.now(timezone.utc).isoformat(),
            source="human_approved" if user_approved else "human_edited",
        )

        # Set seg.name for backwards compatibility with strategy.py and report.py
        seg.name = name

        return f"Recorded persona for segment {segment_id} with name '{name}'"

    return [
        FunctionTool.from_defaults(
            fn=get_segments_overview,
            name="get_segments_overview",
            description="Get overview of all segments showing which need personas"
        ),
        FunctionTool.from_defaults(
            fn=get_segment_details,
            name="get_segment_details",
            description="Get comprehensive segment data for persona building: outcomes, demographics, zone profile, relative size"
        ),
        FunctionTool.from_defaults(
            fn=get_cross_segment_comparison,
            name="get_cross_segment_comparison",
            description="Get what makes this segment UNIQUE vs others: outcomes that are underserved/overserved ONLY in this segment"
        ),
        FunctionTool.from_defaults(
            fn=present_persona_draft,
            name="present_persona_draft",
            description="REQUIRED: Present complete persona draft to user for review. Args: segment_id, name, size_summary, needs_summary, overserved_summary, demographics_summary, narrative. Returns user response (approved or alternative name)."
        ),
        FunctionTool.from_defaults(
            fn=record_persona,
            name="record_persona",
            description="Record final persona. Will FAIL if present_persona_draft was not called first. Args: segment_id, name, size_summary, needs_summary, overserved_summary, demographics_summary, narrative, user_approved (bool)."
        ),
    ]


async def _build_personas_async(
    segment_model: SegmentModelWithAssignments,
    on_review: Callable[[SegmentPersona, Segment], str]
) -> SegmentModelWithAssignments:
    """Build personas for all segments — agent controls the loop."""

    needs_persona = [s for s in segment_model.segments if s.persona is None]
    if not needs_persona:
        print("All segments already have personas. Nothing to do.")
        return segment_model

    print(f"{len(needs_persona)} segment(s) need personas...")

    llm = Anthropic(model="claude-sonnet-4-20250514")
    tools = create_persona_tools(segment_model, on_review)

    agent = AgentWorkflow.from_tools_or_functions(
        tools_or_functions=tools,
        llm=llm,
        system_prompt=SYSTEM_PROMPT + "\n\n" + PERSONA_PROMPT,
    )

    response = await agent.run(
        user_msg="Build personas for all segments that need them",
        max_iterations=40,
    )
    print(f"\nAgent: {response}")

    return segment_model


def build_personas(
    segment_model: SegmentModelWithAssignments,
    on_review: Callable[[SegmentPersona, Segment], str]
) -> SegmentModelWithAssignments:
    """Build ODI personas for all segments. Sync wrapper."""
    return asyncio.run(_build_personas_async(segment_model, on_review))
