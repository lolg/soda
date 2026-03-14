"""Strategy assignment via code-driven decision tree with LLM-contextualised questions."""

import asyncio
import json
from typing import Callable

from llama_index.llms.anthropic import Anthropic

from soda.core.config import StrategyConfig, StrategyQuestion
from soda.core.models import SegmentModelWithAssignments, Segment, StrategyAssignment


CONTEXTUALISE_PROMPT = """You contextualise viability questions for ODI strategy assignment.

Given a question template, its strategic importance, and segment data, rewrite the
question so it references specific data from this segment. The user cannot see the
segment data — your question is their only window into what the data shows.

Rules:
- Reference specific outcomes, scores, and percentages from the segment data
- Include the strategic "why" naturally — help the user understand what hangs on their answer
- Keep it to 2-3 sentences max
- End with a clear yes/no question
- Do NOT answer the question yourself — just frame it

Strategy being evaluated: {strategy_name}
Question template: {question_text}
Why this matters: {why}
Segment data:
{segment_context}
Business context:
{business_context}

Write the contextualised question:"""


def build_segment_context(seg: Segment) -> dict:
    """Extract segment data for LLM contextualisation."""
    underserved = sorted(
        seg.zones.underserved.outcomes, key=lambda o: o.opportunity, reverse=True
    )
    overserved = sorted(
        seg.zones.overserved.outcomes, key=lambda o: o.opportunity, reverse=True
    )

    return {
        "segment_name": seg.name or f"Segment {seg.segment_id}",
        "size_pct": seg.size_pct,
        "underserved_pct": seg.zones.underserved.pct,
        "overserved_pct": seg.zones.overserved.pct,
        "table_stakes_pct": seg.zones.table_stakes.pct,
        "appropriate_pct": seg.zones.appropriate.pct,
        "underserved_count": len(underserved),
        "overserved_count": len(overserved),
        "top_underserved": [
            {"description": o.description, "opportunity": o.opportunity}
            for o in underserved[:5]
        ],
        "top_overserved": [
            {"description": o.description, "opportunity": o.opportunity}
            for o in overserved[:5]
        ],
        "persona": {
            "name": seg.persona.name,
            "narrative": seg.persona.narrative,
            "demographics_summary": seg.persona.demographics_summary,
            "needs_summary": seg.persona.needs_summary,
            "overserved_summary": seg.persona.overserved_summary,
        } if seg.persona else None,
        "demographics": seg.demographics or {},
    }


async def contextualise_question(
    question: StrategyQuestion,
    strategy_name: str,
    segment_context: dict,
    business_context: dict[str, str],
    llm: Anthropic,
) -> str:
    """Use LLM to contextualise a viability question with segment data."""
    prompt = CONTEXTUALISE_PROMPT.format(
        strategy_name=strategy_name,
        question_text=question.text,
        why=question.why or "",
        segment_context=json.dumps(segment_context, indent=2),
        business_context=json.dumps(business_context, indent=2),
    )
    response = await llm.acomplete(prompt)
    return response.text.strip()


def gather_business_context(
    strategy_config: StrategyConfig,
    on_context: Callable[[str], str] | None = None,
) -> dict[str, str]:
    """Gather business context — uses pre-filled answers, asks interactively for the rest."""
    answers: dict[str, str] = {}
    for q in strategy_config.business_context:
        if q.answer:
            answers[q.id] = q.answer
        elif on_context:
            answers[q.id] = on_context(q.text)
    return answers


def evaluate_condition(check: str, segment: Segment) -> bool:
    """Evaluate a condition node against segment data."""
    if check == "has_underserved":
        return len(segment.zones.underserved.outcomes) > 0
    elif check == "has_overserved":
        return len(segment.zones.overserved.outcomes) > 0
    return False


async def walk_decision_tree(
    segment: Segment,
    strategy_config: StrategyConfig,
    on_question: Callable[[str, Segment], bool],
    business_context: dict[str, str],
    llm: Anthropic,
) -> StrategyAssignment:
    """Walk the decision tree for a single segment. Returns the assignment."""
    tree = strategy_config.decision_tree
    segment_context = build_segment_context(segment)
    all_answers: dict[str, bool] = {}

    current = "start"

    while current in tree:
        node = tree[current]

        if node.type == "condition":
            result = evaluate_condition(node.check, segment)
            current = node.on_yes if result else node.on_no

        elif node.type == "strategy":
            defn = strategy_config.strategies[node.strategy]
            viable = True

            print(f"\n  Evaluating: {node.strategy}")

            for question in defn.questions:
                contextualised = await contextualise_question(
                    question, node.strategy, segment_context, business_context, llm
                )

                answer = on_question(contextualised, segment)
                all_answers[question.id] = answer

                if not answer:
                    viable = False
                    break

            if viable:
                return StrategyAssignment(
                    name=node.strategy,
                    viable_options=[node.strategy],
                    viability_answers=all_answers,
                    business_context=business_context,
                )

            # Strategy failed — follow on_fail reference
            current = node.on_fail

    # Reached a terminal value (not a node ID) — it's the fallback strategy name
    fallback = current or "sustaining"
    return StrategyAssignment(
        name=fallback,
        viable_options=[],
        viability_answers=all_answers,
        warning="No strategy was viable based on viability answers" if all_answers else None,
        business_context=business_context,
    )


async def _strategy_async(
    segment_model: SegmentModelWithAssignments,
    strategy_config: StrategyConfig,
    on_question: Callable[[str, Segment], bool],
    on_context: Callable[[str], str] | None = None,
) -> SegmentModelWithAssignments:
    """Assign strategies to all segments using the decision tree."""

    needs_strategy = [s for s in segment_model.segments if s.strategy is None]
    if not needs_strategy:
        print("All segments already have strategies. Nothing to do.")
        return segment_model

    print(f"{len(needs_strategy)} segment(s) need strategy assignment...")

    # 1. Business context (once)
    business_context = gather_business_context(strategy_config, on_context)
    if business_context:
        print(f"Business context: {len(business_context)} answers loaded")

    # 2. LLM for question contextualisation
    llm = Anthropic(model="claude-sonnet-4-20250514")

    # 3. Walk tree for each segment
    for seg in segment_model.segments:
        if seg.strategy is not None:
            continue

        print(f"\n{'='*50}")
        print(f"  {seg.name} ({seg.size_pct:.1f}%)")
        print(f"{'='*50}")

        seg.strategy = await walk_decision_tree(
            seg, strategy_config, on_question, business_context, llm
        )

        print(f"\n  => Strategy: {seg.strategy.name}")

    return segment_model


def strategy(
    segment_model: SegmentModelWithAssignments,
    strategy_config: StrategyConfig,
    on_question: Callable[[str, Segment], bool],
    on_context: Callable[[str], str] | None = None,
) -> SegmentModelWithAssignments:
    """Assign strategies to segments. Sync wrapper."""
    return asyncio.run(
        _strategy_async(segment_model, strategy_config, on_question, on_context)
    )
