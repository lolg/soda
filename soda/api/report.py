"""Report generation via LLM agent with data tools."""

from dataclasses import dataclass
from pathlib import Path

from pydantic_ai import Agent, RunContext

from soda.core.models import SegmentModelWithAssignments
from soda.core.strategy_models import BusinessContext


@dataclass
class ReportDeps:
    segment_model: SegmentModelWithAssignments
    business_context: BusinessContext
    output_path: Path


INSTRUCTIONS = """\
You write concise, data-grounded strategy reports for market researchers,
product managers, and business managers.

Process:
1. Call get_overview to see the segments and business context.
2. Call get_segment_detail for each segment.
3. Call save_report with the complete markdown report.

Report structure — follow this exactly:

# Strategy Report

## Summary
2-3 sentences. How many segments, what the core job is, what the overall
strategic direction is. Reference segment sizes and strategy labels.

## [Segment name] ([size]%)
Strategy: [label] | Pricing: [direction]

### Invest
Bulleted list of high-need outcomes in priority order. Each line:
- **[Outcome name]** — [importance]% importance, [satisfaction]% satisfaction, [opportunity] opportunity

1 sentence after the list: why these are the priority.

### Reduce
Bulleted list of low-priority outcomes (top 4-5 if more than 5 in the zone). Each line:
- **[Outcome name]** — [importance]% importance, [satisfaction]% satisfaction

If more than 5, add: "Plus N additional low-priority outcomes."
1 sentence: why investment here exceeds what this segment values.

### Maintain
Bulleted list of essential outcomes by name. 1 sentence: these cannot be cut.

### Mandate
One sentence: what to do. Name the specific outcomes to invest in and
the specific outcomes to strip or reduce. This is the decision statement.

### Rationale
Trace the strategy decision path explicitly. Name each gate in sequence:
"[gate]: [answer] → [what this means]". Show how the strategy was
determined step by step.

[Repeat for each segment]

## Cross-segment patterns
If you notice outcomes that appear in the same zone across all segments
(e.g. low-priority in both), note them briefly. Keep to 2-3 sentences.

## Next steps
3-4 concrete actions derived from the strategies. Be specific — reference
outcomes and segments by name.

Rules:
- Do not use ODI jargon: underserved, overserved, table stakes, opportunity score.
  Use plain descriptions like "high-need", "low-priority", "essential".
- Do not assign identity labels to segments (e.g. "dog owners", "families").
  Describe what the data shows, not who the people are.
- When listing outcomes, use bulleted markdown lists with one outcome per line.
- When a zone has more than 5 outcomes, list the top 4-5 with scores and
  summarise the rest as "plus N additional low-priority outcomes."
- Next steps should state what to prioritise and why, not how or when to execute.
  "Prioritise dog exercise areas" is fine. "Immediately begin removing playgrounds" is not.
- The mandate must be exactly one sentence. Include the count of outcomes to
  invest in and reduce.

Data glossary:
- importance: % of the segment rating this outcome as very/extremely important
- satisfaction: % of the segment rating this outcome as very/extremely satisfied
- opportunity: importance + gap — higher means bigger unmet need
- Zones group outcomes by their importance/satisfaction pattern:
  - "underserved" = high importance, low satisfaction → invest here
  - "overserved" = low importance, high satisfaction → reduce here
  - "table_stakes" = high importance, high satisfaction → maintain, don't cut
  - "appropriate" = low importance, low satisfaction → ignore
- Strategy steps show the decisions that determined the strategy:
  each step has a gate (what was being decided), a purpose (why it
  matters), and an answer (yes/no/uncertain from the user)
- weight_override_applied: if true, the segment was reclassified because
  one zone's combined scores were 3x+ the other's
- The 20% improvement threshold is measured against: reducing time to
  complete the job, reducing likelihood of failure, or reducing waste/cost.
  "Better" means measurably better on these dimensions, not subjectively.
"""


report_agent = Agent(
    'anthropic:claude-sonnet-4-20250514',
    deps_type=ReportDeps,
    instructions=INSTRUCTIONS,
)


@report_agent.tool
def get_overview(ctx: RunContext[ReportDeps]) -> dict:
    """Get high-level overview: business context and segment summary."""
    bc = ctx.deps.business_context
    return {
        "business_context": {
            "entity_type": bc.entity_type,
            "core_jtbd": bc.core_jtbd,
            "market_position": bc.market_position,
            "market_size": bc.market_size,
            "price_anchor": bc.price_anchor,
            "constraints": bc.constraints,
            "competitive_context": bc.competitive_context,
        },
        "segments": [
            {
                "segment_id": s.segment_id,
                "name": s.name,
                "size_pct": s.size_pct,
                "classification": s.signals.classification.value if s.signals else None,
                "strategy_label": s.strategy.strategy_label if s.strategy else None,
                "pricing_direction": s.strategy.pricing_direction if s.strategy else None,
            }
            for s in ctx.deps.segment_model.segments
        ],
    }


@report_agent.tool
def get_segment_detail(ctx: RunContext[ReportDeps], segment_id: int) -> dict:
    """Get full detail for one segment: outcomes, signals, strategy, demographics."""
    seg = next(
        s for s in ctx.deps.segment_model.segments if s.segment_id == segment_id
    )

    def _outcomes(zone) -> list[dict]:
        return sorted(
            [
                {
                    "description": o.description,
                    "importance": round(o.imp_tb, 1),
                    "satisfaction": round(o.sat_tb, 1),
                    "opportunity": round(o.opportunity, 1),
                }
                for o in zone.outcomes
            ],
            key=lambda o: o["opportunity"],
            reverse=True,
        )

    strategy_steps = []
    if seg.strategy and seg.strategy.steps:
        for step in seg.strategy.steps:
            if step.node_type == "ask":
                strategy_steps.append({
                    "gate": step.gate_intent,
                    "purpose": step.purpose,
                    "answer": step.answer.value if step.answer else None,
                })

    return {
        "segment_id": seg.segment_id,
        "name": seg.name,
        "size_pct": seg.size_pct,
        "demographics": seg.demographics or {},
        "classification": seg.signals.classification.value if seg.signals else None,
        "signals": {
            "underserved": {
                "count": seg.signals.underserved.count,
                "weight": round(seg.signals.underserved.weight, 1),
                "weight_override_applied": seg.signals.weight_override_applied,
            },
            "overserved": {
                "count": seg.signals.overserved.count,
                "weight": round(seg.signals.overserved.weight, 1),
            },
        } if seg.signals else None,
        "zones": {
            "underserved": _outcomes(seg.zones.underserved),
            "overserved": _outcomes(seg.zones.overserved),
            "table_stakes": _outcomes(seg.zones.table_stakes),
            "appropriate": _outcomes(seg.zones.appropriate),
        },
        "strategy": {
            "label": seg.strategy.strategy_label,
            "pricing_direction": seg.strategy.pricing_direction,
            "allocation": seg.strategy.allocation.model_dump() if seg.strategy.allocation else None,
            "addressable_population": seg.strategy.addressable_population,
            "stop_doing": seg.strategy.stop_doing,
            "note": seg.strategy.note,
            "trajectory": seg.strategy.trajectory,
            "open_dependencies": seg.strategy.open_dependencies,
            "steps": strategy_steps,
        } if seg.strategy else None,
    }


@report_agent.tool
def save_report(ctx: RunContext[ReportDeps], markdown: str) -> str:
    """Save the final report as a markdown file."""
    ctx.deps.output_path.parent.mkdir(parents=True, exist_ok=True)
    ctx.deps.output_path.write_text(markdown)
    return f"Report saved to {ctx.deps.output_path}"


def generate_report(
    segment_model: SegmentModelWithAssignments,
    business_context: BusinessContext,
    output_path: Path,
) -> Path:
    """Generate strategy report."""

    for seg in segment_model.segments:
        if seg.signals is None:
            raise ValueError(
                f"Segment {seg.segment_id} has no signals. Run classify first."
            )
        if seg.strategy is None:
            raise ValueError(
                f"Segment {seg.segment_id} has no strategy. Run strategy first."
            )

    print(f"Generating report for {len(segment_model.segments)} segments...")

    deps = ReportDeps(
        segment_model=segment_model,
        business_context=business_context,
        output_path=output_path,
    )
    result = report_agent.run_sync(
        "Generate the strategy report and save it.",
        deps=deps,
    )
    print(f"Agent: {result.output}")

    return output_path
