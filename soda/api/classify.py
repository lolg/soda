"""Classify segments for strategy selection. Deterministic, no LLM.

Computes zone signals (breadth, intensity, weight) and assigns a
classification (MIXED, UNDER_ONLY, OVER_ONLY, WELL_SERVED) to each
segment. Run this before the strategy step.
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
    """Compute zone signals and classify a segment.

    Covers phases 1 (classification) and 2 (weight override) of the
    strategy decision graph. The graph walker starts after this returns.
    """
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
    """Classify all segments. Idempotent — skips segments that already have signals."""

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
