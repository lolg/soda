"""Strategy assignment via decision graph walk with LLM-contextualised questions.

The graph walker is code-controlled. The LLM's only job is to turn
abstract gate intents into contextual, answerable questions grounded
in the segment data and business context.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from pydantic_ai import Agent

from soda.core.models import Segment, SegmentModelWithAssignments
from soda.core.strategy_models import (
    Answer,
    AskNode,
    BusinessContext,
    DecisionGraph,
    SegmentSignals,
    StepRecord,
    StrategyNode,
    StrategyResult,
)

CONTEXTUALISE_INSTRUCTIONS = """\
You contextualise strategy questions for market segments.

You receive a gate intent, its strategic purpose, segment data, and business context.
Your job: produce a brief context line and a single focused question.

Output format — always use this exact structure:

CONTEXT: [1-2 sentences. Facts only: scores, percentages, counts, constraints.
Must NOT contain: underserved, overserved, over-only, under-only, mixed,
table stakes, opportunity score, zone weight, classification.
Do not express any number as a "zone weight" — use plain descriptions like
"8 outcomes with a combined score of 34.0" if needed.]

QUESTION: [One yes/no/uncertain question. Ask one thing only.
Must NOT infer motivations, reasons, preferences, or consequences
beyond what the data shows. Do not add clauses like "if it meant..."
or "in order to..." — just ask the core question.]

Rules:
- CONTEXT states facts only. No interpretation, recommendations, persuasion, or loaded language.
- QUESTION must ask about exactly one decision, assumption, or trade-off.
- Do not combine alternatives in one question (for example: “pay higher fees or support increased rates”).
- Do not combine multiple actions, audiences, or funding mechanisms in one question.
- Reference specific outcomes, scores, percentages, and constraints in CONTEXT, not in QUESTION.
- Keep QUESTION short, concrete, and easy to answer with yes, no, or uncertain.
- Do NOT answer the question yourself.
- Do NOT invent numbers, percentages, estimates, or constraints not present in the input.
- Do NOT use ODI jargon.
- Do NOT use the terms: underserved, overserved, table stakes, appropriately served, opportunity score, zone weight.
- When the gate covers multiple outcomes in a zone, ask about the category as a whole, not a single outcome.
- Do not infer motivations or reasons beyond what the data shows.
- Keep the total output under 80 words.
"""


contextualise_agent = Agent(
    'anthropic:claude-sonnet-4-20250514',
    instructions=CONTEXTUALISE_INSTRUCTIONS
)


def build_segment_context(
    segment: Segment,
    signals: SegmentSignals,
    context_from: list[str],
    business_context: BusinessContext,
) -> str:
    """Build a focused context string for LLM question contextualisation.

    Only includes the data categories listed in context_from.
    """
    parts: list[str] = []

    parts.append(
        f"Segment: {segment.name or f'Segment {segment.segment_id}'} "
        f"({segment.size_pct:.1f}% of population)"
    )
    parts.append(f"Classification: {signals.classification.value}")

    if "underserved_outcomes" in context_from:
        outcomes = sorted(
            segment.zones.underserved.outcomes,
            key=lambda o: o.opportunity,
            reverse=True,
        )
        if outcomes:
            lines = [
                f"High-need outcomes (zone weight: {signals.underserved.weight:.1f}, "
                f"{signals.underserved.count} outcomes):"
            ]
            for o in outcomes[:5]:
                lines.append(
                    f"  - {o.description} (opportunity: {o.opportunity:.1f}, "
                    f"importance: {o.imp_tb:.0f}%, satisfaction: {o.sat_tb:.0f}%)"
                )
            parts.append("\n".join(lines))
        else:
            parts.append("No high-need (underserved) outcomes in this segment.")

    if "overserved_outcomes" in context_from:
        outcomes = sorted(
            segment.zones.overserved.outcomes,
            key=lambda o: o.opportunity,
            reverse=True,
        )
        if outcomes:
            lines = [
                f"Low-priority outcomes (zone weight: {signals.overserved.weight:.1f}, "
                f"{signals.overserved.count} outcomes):"
            ]
            for o in outcomes[:5]:
                lines.append(
                    f"  - {o.description} (opportunity: {o.opportunity:.1f}, "
                    f"importance: {o.imp_tb:.0f}%, satisfaction: {o.sat_tb:.0f}%)"
                )
            parts.append("\n".join(lines))
        else:
            parts.append("No low-priority (overserved) outcomes in this segment.")

    if "demographics" in context_from and segment.demographics:
        lines = ["Demographics:"]
        for dimension, values in segment.demographics.items():
            if isinstance(values, dict):
                top = sorted(values.items(), key=lambda x: x[1], reverse=True)[:3]
                formatted = ", ".join(f"{k}: {v:.0f}%" for k, v in top)
                lines.append(f"  - {dimension}: {formatted}")
        parts.append("\n".join(lines))

    if "company_metadata" in context_from:
        lines = ["Business context:"]
        lines.append(f"  - Entity: {business_context.entity_type}")
        lines.append(f"  - Core job: {business_context.core_jtbd}")
        if business_context.market_size:
            lines.append(f"  - Market size: {business_context.market_size:,}")
        if business_context.price_anchor:
            lines.append(f"  - Price/budget: {business_context.price_anchor}")
        if business_context.constraints:
            lines.append(f"  - Constraints: {business_context.constraints}")
        if business_context.competitive_context:
            lines.append(f"  - Competition: {business_context.competitive_context}")
        parts.append("\n".join(lines))

    return "\n\n".join(parts)


def contextualise_question(
    node: AskNode,
    segment_context: str,
    business_context: BusinessContext,
) -> str:
    """Use LLM to turn an abstract gate intent into a contextual question."""
    prompt = (
        f"Gate intent: {node.gate_intent}\n"
        f"Purpose: {node.purpose}\n\n"
        f"Segment data:\n{segment_context}\n\n"
        f"Write the contextualised question:"
    )
    result = contextualise_agent.run_sync(prompt)
    return result.output

def walk_graph(
    segment: Segment,
    signals: SegmentSignals,
    graph: DecisionGraph,
    business_context: BusinessContext,
    on_question: Callable[[str, Segment], str],
) -> StrategyResult:
    """Walk the decision graph for a single segment.

    Starts at the entry point for the segment's classification.
    At ask nodes: contextualises with LLM, presents to human, follows edge.
    At strategy nodes: returns the result.
    """
    entry_id = graph.entry_node_id(signals.classification)
    current_id = entry_id
    steps: list[StepRecord] = []

    while True:
        node = graph.nodes[current_id]

        if isinstance(node, StrategyNode):
            # Terminal — record and return
            steps.append(StepRecord(
                node_id=current_id,
                node_type="strategy",
            ))

            # Compute addressable market if data available
            addressable_pop = None
            if business_context.market_size:
                addressable_pop = (segment.size_pct / 100) * business_context.market_size

            return StrategyResult(
                strategy_label=node.label,
                allocation=node.allocation,
                pricing_direction=node.pricing_direction,
                stop_doing=node.stop_doing,
                note=node.note,
                trajectory=node.trajectory,
                open_dependencies=node.open_dependencies,
                addressable_population=addressable_pop,
                terminal_node_id=current_id,
                steps=steps,
            )

        elif isinstance(node, AskNode):
            # Build context, contextualise question, ask human
            segment_context = build_segment_context(
                segment, signals, node.context_from, business_context,
            )
            question = contextualise_question(node, segment_context, business_context)

            # Present to human
            raw_answer = on_question(question, segment)
            answer = Answer.from_input(raw_answer)

            # Determine next node
            next_id = node.follow(answer)

            # Record the step
            steps.append(StepRecord(
                node_id=current_id,
                node_type="ask",
                gate_intent=node.gate_intent,
                purpose=node.purpose,
                context_from=node.context_from,
                answer=answer,
                next_node_id=next_id,
            ))

            current_id = next_id

        else:
            raise ValueError(f"Unknown node type at '{current_id}'")

def define_strategy(
    segment: Segment,
    graph: DecisionGraph,
    business_context: BusinessContext,
    on_question: Callable[[str, Segment], str],
) -> StrategyResult:
    """Define strategy for a single segment.

    Requires seg.signals to be populated (run classify step first).
    """
    if segment.signals is None:
        raise ValueError(
            f"Segment {segment.segment_id} has no signals. "
            f"Run the classify step first."
        )

    return walk_graph(segment, segment.signals, graph, business_context, on_question)


def assign_strategies(
    segment_model: SegmentModelWithAssignments,
    graph_path: str | Path,
    context_path: str | Path,
    on_question: Callable[[str, Segment], str],
) -> SegmentModelWithAssignments:
    """Assign strategies to all segments. Orchestrator for the CLI.

    Loads the decision graph and business context, then walks the graph
    for each segment that doesn't already have a strategy.
    """
    graph = DecisionGraph.from_file(graph_path)
    business_context = BusinessContext.from_file(context_path)

    needs_strategy = [s for s in segment_model.segments if s.strategy is None]
    if not needs_strategy:
        print("All segments already have strategies.")
        return segment_model

    print(f"{len(needs_strategy)} segment(s) need strategy assignment...\n")

    if business_context.market_size:
        print(f"Market size: {business_context.market_size:,}")
    print(f"Core job: {business_context.core_jtbd}")
    print(f"Entity: {business_context.entity_type}\n")

    for seg in segment_model.segments:
        if seg.strategy is not None:
            continue

        name = seg.name or f"Segment {seg.segment_id}"
        classification = seg.signals.classification.value if seg.signals else "?"

        print(f"{'='*55}")
        print(f"  {name} ({seg.size_pct:.1f}%) — {classification}")
        print(f"{'='*55}")

        seg.strategy = define_strategy(seg, graph, business_context, on_question)

        label = seg.strategy.strategy_label or "unresolved"
        print(f"\n  → Strategy: {label}")
        if seg.strategy.pricing_direction:
            print(f"  → Pricing: {seg.strategy.pricing_direction}")
        if seg.strategy.addressable_population:
            print(f"  → Addressable: {seg.strategy.addressable_population:,.0f}")
        if seg.strategy.open_dependencies:
            print(f"  → Open: {', '.join(seg.strategy.open_dependencies)}")
        print()

    return segment_model
