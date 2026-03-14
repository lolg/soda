import logging
 
from soda.core.models import (
    ClassificationLabel,
    Segment,
    SegmentClassification,
)
 
logger = logging.getLogger(__name__)
 
MAX_OPPORTUNITY_SCORE = 20.0  # Ulwick's opportunity score ceiling
 
def _compute_underserved_strength(pct: float, max_opp: float) -> float:
    """
    Composite 0-1 score combining:
      - breadth:    underserved_pct / 100
      - intensity:  max_underserved_opportunity / MAX_OPPORTUNITY_SCORE
    Averaged equally.
    """
    breadth   = pct / 100.0
    intensity = max_opp / MAX_OPPORTUNITY_SCORE
    return round((breadth + intensity) / 2.0, 4)
 
 
def _compute_overserved_strength(pct: float) -> float:
    """
    Breadth-only 0–1 score.
    Opportunity scoring is an unmet-need signal — less meaningful on the
    overserved side. Breadth (how many outcomes are over-delivered) is the
    more stable Ulwick-consistent signal here.
    """
    return round(pct / 100.0, 4)
 
 
def _strategy_candidates(label: ClassificationLabel, balance: float) -> list[str]:
    """
    Returns strategies sorted by viability — most viable first.
    Discrete excluded: it is a situational overlay, not a classification outcome.

    MIXED sort is balance-sensitive:
      - balance > +0.1 (underserved dominates): differentiated before disruptive
      - balance < -0.1 (overserved dominates):  disruptive before differentiated
      - balance ≈ 0 (balanced):                 differentiated before disruptive
        dominant stays first in all MIXED cases — only strategy addressing both sides.
    """
    if label == ClassificationLabel.MIXED:
        if balance < -0.1:
            # Overserved dominates — cost reduction is stronger lever
            return ["dominant", "disruptive", "differentiated", "sustaining"]
        else:
            # Underserved dominates or balanced — value creation is stronger lever
            return ["dominant", "differentiated", "disruptive", "sustaining"]

    if label == ClassificationLabel.UNDER_ONLY:
        return ["differentiated", "dominant", "disruptive", "sustaining"]

    if label == ClassificationLabel.OVER_ONLY:
        return ["disruptive", "sustaining"]

    # WELL_SERVED
    return ["sustaining"]
 
 
def classify_segment(
    segment: Segment,
    min_underserved_pct: float = 15.0,
    min_overserved_pct: float  = 20.0,
    min_opportunity: float     = 15.0,
    top_n: int                 = 3,
) -> SegmentClassification:
 
    zones = segment.zones
 
    # ── Raw values
    underserved_outcomes = zones.underserved.outcomes if zones.underserved else []
    overserved_outcomes  = zones.overserved.outcomes  if zones.overserved  else []
    underserved_pct      = zones.underserved.pct      if zones.underserved else 0.0
    overserved_pct       = zones.overserved.pct       if zones.overserved  else 0.0
 
    sorted_under = sorted(underserved_outcomes, key=lambda o: o.opportunity, reverse=True)
    sorted_over  = sorted(overserved_outcomes,  key=lambda o: o.opportunity)  # lowest opp = most overserved
 
    max_underserved_opp = sorted_under[0].opportunity if sorted_under else 0.0
 
    # ── Boolean gates
    underserved_by_breadth   = underserved_pct >= min_underserved_pct
    underserved_by_intensity = max_underserved_opp >= min_opportunity
    has_meaningful_underserved = underserved_by_breadth or underserved_by_intensity
    has_meaningful_overserved  = overserved_pct >= min_overserved_pct
 
    # ── Classification
    if has_meaningful_underserved and has_meaningful_overserved:
        label = ClassificationLabel.MIXED
    elif has_meaningful_underserved:
        label = ClassificationLabel.UNDER_ONLY
    elif has_meaningful_overserved:
        label = ClassificationLabel.OVER_ONLY
    else:
        label = ClassificationLabel.WELL_SERVED
 
    # ── Strength + balance
    u_strength = _compute_underserved_strength(underserved_pct, max_underserved_opp)
    o_strength = _compute_overserved_strength(overserved_pct)
    balance    = round(u_strength - o_strength, 4)
 
    # ── Reasons (plain language for LLM context)
    reasons = []
    if underserved_by_breadth:
        reasons.append(
            f"underserved by breadth: {underserved_pct:.1f}% of outcomes "
            f">= {min_underserved_pct}% threshold"
        )
    if underserved_by_intensity:
        top_name = sorted_under[0].description if sorted_under else "n/a"
        reasons.append(
            f"underserved by intensity: max opportunity score {max_underserved_opp:.2f} "
            f">= {min_opportunity} threshold — '{top_name}'"
        )
    if not has_meaningful_underserved:
        reasons.append(
            f"not underserved: breadth {underserved_pct:.1f}% < {min_underserved_pct}% "
            f"and max opportunity {max_underserved_opp:.2f} < {min_opportunity}"
        )
    if has_meaningful_overserved:
        reasons.append(
            f"overserved by breadth: {overserved_pct:.1f}% of outcomes "
            f">= {min_overserved_pct}% threshold ({len(overserved_outcomes)} outcomes)"
        )
    else:
        reasons.append(
            f"not overserved: breadth {overserved_pct:.1f}% < {min_overserved_pct}%"
        )
 
    return SegmentClassification(
        classification=label,
        underserved_strength=u_strength,
        overserved_strength=o_strength,
        under_over_balance=balance,
        strategy_candidates=_strategy_candidates(label, balance),
        classification_reasons=reasons,
    )