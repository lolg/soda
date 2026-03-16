"""Classify segments for strategy selection.

Looks at each segment's four zones and answers one question — 
which zones carry enough signal to drive a strategy? The output
is MIXED, UNDER_ONLY, OVER_ONLY, or WELL_SERVED.

For each zone, the following signals are assigned:

- breadth: (% of outcomes in the zone) answers: "is a significant
  proportion of the market's needs in this state?" The threshold is
  15% for underserved, 20% for overserved.

- intensity: the max opportunity score. Answers: "is there at
  least one very strong signal?" The threshold is
  15 based on Ulwick's published

- weight: Weight (sum of scores) is only used for one thing:
  the 3:1 ratio check on MIXED segments.

- count: The number of outcomes in the zone

and for the segment as a whole:

- classification (MIXED, UNDER_ONLY, OVER_ONLY, or WELL_SERVED)

Weight (sum of opportunity scores) alone can't distinguish
between two strategically different situations.

For example:

Segment 0's underserved zone: 3 outcomes, weight = 45.0
Segment 0's overserved zone: 8 outcomes, weight = 34.0

If we only looked at weight, you'd say "underserved is stronger."
Which is true. But consider a segment with 10 underserved outcomes
all scoring 4.5 — that's also weight = 45.0. Strategically those
are completely different situations. The first has two outcomes
above 16 (acute unmet need, strong differentiation signal). The
second has mild dissatisfaction spread across many outcomes
(no single target worth investing in).

The underserved zone counts as meaningful if either condition is
true:

    Breadth ≥ 15% — a significant share of outcomes are underserved
    Intensity ≥ 15 — at least one outcome has a very high opportunity
    score

The logic is: a small number of acute unmet needs is just as
strategically meaningful as a broad spread of moderate ones.

The purpose of this classification is to ensure zones that are
deserving enter the conversation and are considered downstream 
during strategy definition.

"""

from soda.core.config import RulesConfig
from soda.core.models import Segment, SegmentModelWithAssignments
from soda.core.strategy_models import (
    Classification,
    SegmentSignals,
    Thresholds,
    ZoneSignals,
)


def compute_zone_signals(segment: Segment, thresholds: Thresholds) -> SegmentSignals:
    """Compute zone signals and classify a segment."""
    zones = [
        segment.zones.underserved,
        segment.zones.overserved,
        segment.zones.table_stakes,
        segment.zones.appropriate,
    ]
    total_outcomes = sum(len(z.outcomes) for z in zones)

    def _signals(zone) -> ZoneSignals:
        scores = [o.opportunity for o in zone.outcomes]
        return ZoneSignals(
            breadth=(len(scores) / total_outcomes * 100) if total_outcomes else 0.0,
            intensity=max(scores) if scores else 0.0,
            weight=sum(scores),
            count=len(scores),
        )

    under = _signals(segment.zones.underserved)
    over = _signals(segment.zones.overserved)
    table = _signals(segment.zones.table_stakes)
    approp = _signals(segment.zones.appropriate)

    # Phase 1: Classification
    has_underserved = (
        under.breadth >= thresholds.meaningful_underserved_breadth
        or under.intensity >= thresholds.meaningful_underserved_intensity
    )
    has_overserved = over.breadth >= thresholds.meaningful_overserved_breadth

    if has_underserved and has_overserved:
        classification = Classification.MIXED
    elif has_underserved:
        classification = Classification.UNDER_ONLY
    elif has_overserved:
        classification = Classification.OVER_ONLY
    else:
        classification = Classification.WELL_SERVED

    # Phase 2: Weight override (MIXED only)
    weight_override = False
    if classification == Classification.MIXED and over.weight > 0:
        ratio = under.weight / over.weight
        if ratio >= thresholds.weight_dominance_ratio:
            classification = Classification.UNDER_ONLY
            weight_override = True
        elif (1.0 / ratio) >= thresholds.weight_dominance_ratio:
            classification = Classification.OVER_ONLY
            weight_override = True

    return SegmentSignals(
        underserved=under,
        overserved=over,
        table_stakes=table,
        appropriate=approp,
        classification=classification,
        weight_override_applied=weight_override,
    )

def classify_segments(
    segment_model: SegmentModelWithAssignments,
    rules: RulesConfig,
) -> SegmentModelWithAssignments:
    """Classify all segments.  Skips segments that already have signals."""

    thresholds = Thresholds.model_validate(
        rules.strategy_rules.model_dump()
    )

    for seg in segment_model.segments:
        if seg.signals is not None:
            continue

        seg.signals = compute_zone_signals(seg, thresholds)

        name = seg.name or f"Segment {seg.segment_id}"
        c = seg.signals.classification
        u = seg.signals.underserved
        o = seg.signals.overserved

        override = " [weight override]" if seg.signals.weight_override_applied else ""
        print(
            f"  {name} ({seg.size_pct:.1f}%): {c.value}{override}\n"
            f"    underserved: {u.count} outcomes, weight={u.weight:.1f}, "
            f"intensity={u.intensity:.1f}\n"
            f"    overserved:  {o.count} outcomes, weight={o.weight:.1f}, "
            f"intensity={o.intensity:.1f}"
        )

    return segment_model
