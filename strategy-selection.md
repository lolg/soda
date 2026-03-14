# ODI Strategy Selection: Specification for Segment Strategy Reports

## What This Produces

For each segment, the output is a strategy report that answers three questions:

1. **Where to focus** — which outcomes to prioritise, and in what order
2. **Why** — what the zone data says about customer need, and what that implies about the value of acting on it
3. **What the feature and cost strategy looks like** — which outcomes to build toward, which to reduce or cut, and what pricing direction the data supports

The strategy label (dominant, differentiated, disruptive, sustaining) is internal scaffolding. It may be surfaced in the report as a shorthand, but it is not the output. A report that says "you have a differentiated strategy" without answering the three questions above has failed. A report that answers all three questions without assigning a label has succeeded.

### What the label actually does

Most real product situations are messy. Segments have mixed signals, resources are constrained, and you have leverage on some outcomes but not others. In these situations the useful output is the allocation map — not a label.

The labels earn their keep at the extremes, when the signal is unambiguous. In those cases the label is doing two things simultaneously.

**Externally**, it is a market positioning and pricing commitment. "Differentiated" means: commit to a premium price and deliver meaningfully better outcomes. "Disruptive" means: commit to a lower price point and accept lower performance.

**Internally**, it is an organisational focusing and deprioritisation instruction. When the signal is strong enough to justify a label, hedging is the wrong answer. A team with a clearly dominant signal that keeps investing in incremental features and holding price is leaving the strategy on the table. The label says: the data is unambiguous — commit to this direction and deprioritise everything that doesn't serve it.

Each label implies a specific stop-doing instruction:
- **Differentiated** — stop competing on price; stop adding features that don't address the top underserved outcomes
- **Disruptive** — stop improving; resist the feature instinct; focus entirely on making it cheaper
- **Dominant** — you must get better and cheaper simultaneously; stop anything that doesn't serve one of those two levers directly
- **Sustaining** — stop searching for a breakthrough; protect the floor and move incrementally

In the messy middle, hedging is the right answer — allocate across zones proportionally because no single direction dominates. But when the signal is strong, the label is what aligns the organisation around a single commitment and makes the allocation map executable.

**Use the label where it is genuinely clear. In all other cases, go straight to the allocation map.**

### What good output looks like

**Example A — strong underserved signal:**
> Segment 1 has 14 outcomes where customers report high importance and low satisfaction. The highest-scoring are X, Y, and Z, each with opportunity scores above 15. This segment is underserved and has no meaningful overserved outcomes. The focus should be on building toward these unmet outcomes. If you can address them materially — Ulwick's threshold is 20% better than existing solutions — this segment will support a premium price. Do not invest in cost reduction here; there is no overserved fat to strip. Table stakes A and B must be maintained at a competitive level; they are not differentiators but losing on them would disqualify the product.

**Example B — strong overserved signal:**
> Segment 2 has 8 outcomes where customers are already well satisfied at levels above what they consider important. Investment in these outcomes is not generating value. The focus should be on cost reduction: stripping or reducing these outcomes frees resource without meaningfully degrading the customer experience. There is insufficient underserved signal to justify investing in improvement. The pricing direction is downward — customers in this segment are paying for more than they need and would switch to a cheaper solution that does the job adequately.

**Example C — mixed signal, underserved weight dominates:**
> Segment 3 has both underserved and overserved outcomes, but the underserved signal is substantially stronger: the top three unmet outcomes have opportunity scores of 16–18, while the overserved outcomes are weak (scores of 3–5). The primary focus is improvement. Reducing investment in the overserved outcomes is worthwhile but secondary — the cost saving is modest. The Cornerstone analogy applies here: a strong cluster of unmet needs in a market where existing solutions fall short is the basis for a better product at a higher price, not a cheaper one.

**Example D — messy middle:**
> Segment 4 has mixed signals with no dominant zone. There is no clear basis for a single strategic commitment. The recommendation is allocation-based: invest in outcomes X and Y (highest opportunity scores, currently underserved), maintain outcomes A, B, C at minimum viable cost (table stakes), reduce investment in outcomes P and Q (overserved, modest scores), and deprioritise the remaining outcomes entirely. No pricing direction is strongly indicated; hold current positioning and revisit when signal strengthens.

---

## The Zone Structure

Each segment contains four zones. Zone data is the input to everything that follows.

| Zone | Meaning | Report implication |
|---|---|---|
| **Underserved** | High importance, low satisfaction | Outcomes to invest in; basis for improvement and potentially premium pricing |
| **Overserved** | Low importance, high satisfaction | Outcomes to reduce or cut; basis for cost reduction and potentially lower pricing |
| **Table stakes** | High importance, high satisfaction | Must be maintained at minimum viable competitive level; not a differentiator |
| **Appropriately served** | Low importance, low satisfaction | Do not prioritise; deprioritise or cut in cost-sensitive situations |

---

## Reading Zone Signals: Breadth, Intensity, and Weight

Three signals are computed for each zone:

- **Breadth** — percentage of outcomes in this zone
- **Intensity** — highest opportunity score among outcomes in this zone
- **Weight** — sum of opportunity scores across all outcomes in this zone: `weight = Σ opportunity_score for all outcomes in zone`

Weight captures both breadth and intensity in a single number. A zone with many low-scoring outcomes and a zone with few high-scoring outcomes can produce comparable weights — this is intentional. It means the 3:1 override heuristic (below) is testable against a concrete value, not a judgement call on whether "a few high scores outweigh many low ones."

Breadth alone is insufficient. A zone with 20% of outcomes but all at low opportunity scores carries less strategic significance than a zone with 12% of outcomes but two at scores of 17+.

**Thresholds (Ulwick):**
- Meaningful underserved: breadth ≥15%, OR intensity ≥15
- Meaningful overserved: breadth ≥20%

**Weight override (implementation heuristic, not ODI doctrine):** when one zone's aggregate weight exceeds the other's by approximately 3:1 or more, treat the segment as effectively single-zone for reporting emphasis and candidate ordering, unless breadth clearly contradicts that read. Apply with judgement.

---

## Segment Classification

Classification determines the shape of the report — which focus areas to lead with, which cost logic to apply.

| Classification | Condition | Report shape |
|---|---|---|
| **MIXED** | Meaningful underserved AND overserved, broadly comparable weight | Both improvement and cost-reduction recommendations; relative weight determines emphasis |
| **UNDER_ONLY** | Meaningful underserved, not overserved — or underserved weight strongly dominates | Improvement focus; cost reduction only through efficiency, not stripping |
| **OVER_ONLY** | Meaningful overserved, not underserved — or overserved weight strongly dominates | Cost-reduction focus; no improvement investment recommended |
| **WELL_SERVED** | Neither signal | No zone-derived growth strategy; sustaining default unless a discrete condition is separately established |

WELL_SERVED is a segment-level classification, not a synonym for the appropriately served zone. A WELL_SERVED segment may still contain outcomes spread across all four zones — it simply means that neither the underserved nor overserved signal is meaningful enough at the segment level to drive a growth strategy.

### WTP as a classification-level input

Willingness to pay (WTP) is not a qualification detail — it is a classification input that determines the shape of the report for any segment with meaningful underserved signal.

WTP status is one of: **confirmed**, **denied**, or **unknown**.

- **UNDER_ONLY + WTP confirmed** → the report leads with improvement and premium pricing. Differentiated is the candidate label.
- **UNDER_ONLY + WTP denied** → the report leads with improvement but the pricing direction is downward or neutral. The team must find a way to deliver better outcomes without charging more. Dominant is the candidate label, and the cost-reduction mechanism must come from operational efficiency or business model innovation rather than stripping overserved outcomes (since none exist).
- **UNDER_ONLY + WTP unknown** → the classification is provisional. The report should present both paths explicitly and flag that WTP data is required to resolve the strategy. Do not default to either Differentiated or Dominant — present the fork.
- **MIXED + WTP confirmed** → Differentiated is viable; overserved outcomes can be stripped for margin improvement rather than price reduction.
- **MIXED + WTP denied** → Dominant is the natural candidate; overserved stripping funds the improvement.
- **MIXED + WTP unknown** → present both paths; flag the dependency.

WTP is typically established through pricing research, conjoint analysis, or direct survey questions about price sensitivity. It cannot be inferred from opportunity scores or zone data.

---

## The Balance Signal

For MIXED segments, compare zone weights to determine emphasis:

- **Underserved weight dominates:** lead with improvement recommendations; treat cost reduction as secondary
- **Overserved weight dominates:** lead with cost-reduction recommendations; treat improvement as secondary
- **Broadly comparable:** present both with equal weight; note the tension explicitly in the report

The balance signal also informs pricing direction. Underserved-dominant segments point toward premium pricing if WTP is present. Overserved-dominant segments point toward reduced pricing. Balanced segments require qualification before a pricing direction can be stated.

---

## Strategy Labels

Where the signal is clear, a label may be assigned. The label is a compression of the three output questions — useful for internal alignment and external positioning, but not a substitute for the full recommendation.

### Differentiated
Better product, premium price. Applies when underserved signal is strong, customers are willing to pay more, and the team can address the top outcomes materially (≥20% better than incumbents). The report leads with which outcomes to improve and why premium pricing is justified.

### Dominant
Better product AND lower price. Requires both levers to be genuinely viable: improvement capability on underserved outcomes AND cost reduction capability on overserved ones. The hardest strategy to execute. The report must address both levers explicitly — a weak cost-reduction case does not qualify.

### Disruptive
Cheaper product, lower performance accepted. Applies when overserved customers or non-consumers would switch to a lower-cost solution. The report leads with which overserved outcomes to strip and what pricing reduction is implied. Non-consumption must be established independently — it cannot be inferred from zone data.

*Note: disruptive may appear as a candidate in UNDER_ONLY segments if non-consumption is separately confirmed. This is a conditional path, not a natural consequence of the underserved signal.*

### Discrete
Premium price, lower quality, captive context. Requires customers who are legally, physically, emotionally, or situationally restricted. Cannot be derived from zone data — must be assessed independently. Remains available as an overlay in any classification, including WELL_SERVED.

### Sustaining
Modest improvement or cost reduction to protect existing position. The correct label when the segment is WELL_SERVED, or when no higher strategy clearly qualifies. Also the honest description of most incremental product development. The report identifies which outcomes to incrementally improve and what competitive baseline must be maintained.

**If no label clearly qualifies, do not force one.** Produce the allocation map and the three-question output directly.

---

## Investment Allocation: The Core Output

Regardless of whether a label is assigned, every report must produce an allocation recommendation across all four zones.

### Underserved — invest
Rank by opportunity score. Report the top outcomes by name, their scores, and the implication: these are where customer need is highest and current solutions fall shortest. This is where product investment should concentrate.

### Overserved — reduce
Report which outcomes are overserved, their scores, and the implication: investment here exceeds what customers value. In cost-focused strategies, reducing or eliminating these outcomes is a direct cost lever. In improvement-focused strategies, any spend above minimum credibility is available for reallocation.

### Table stakes — maintain at minimum viable level
Report which outcomes customers consider essential and already well served. These define the competitive floor. The report should note: these cannot be cut without disqualifying the product, but over-investing in them crowds out investment in underserved outcomes. If competitors satisfy table stakes more efficiently, this is a structural cost disadvantage worth naming.

### Appropriately served — deprioritise
Do not invest further. In cost-sensitive strategies, eliminating these entirely is consistent with the value proposition. Otherwise, simply hold and reallocate any current spend elsewhere.

### Allocation summary table (per report)

| Zone | Outcomes | Action | Pricing implication |
|---|---|---|---|
| Underserved | [list by score] | Invest — priority order | Supports premium if WTP confirmed |
| Overserved | [list by score] | Reduce or eliminate | Supports lower price or margin recovery |
| Table stakes | [list] | Maintain minimum | Neutral — cost floor only |
| Appropriately served | [list] | Deprioritise | Neutral |

---

## Qualification Questions

Where a label is being considered, these questions ground the recommendation in organisational reality. They should be answered before a label is confirmed and their answers should appear in the report reasoning.

Critically, qualification answers are used not only to confirm or reject a label, but also to support or withhold specific claims in the report — about premium pricing viability, cost reduction feasibility, and strategic confidence — even when no label is assigned. A report that claims "this segment supports premium pricing" without a confirmed WTP answer, or that recommends cost reduction without a viable stripping mechanism, is overclaiming. Qualification is what prevents that.

*Note: WTP has been elevated to a classification-level input (see Segment Classification above). The questions below address execution viability — whether the team can deliver on the strategy the data points toward.*

**Differentiated:** Can the team materially improve the top underserved outcomes (target: ≥20% better)? (WTP is resolved at classification; this question addresses delivery capability.)

**Dominant:** Can the team materially improve underserved outcomes AND reduce cost through overserved outcome stripping or operational efficiency? Are both levers genuinely viable?

**Disruptive:** Is there a confirmed population of overserved customers or non-consumers who would accept lower performance for significantly lower price? Is a lower-cost structure achievable?

**Discrete:** Are customers in this segment restricted in their alternatives? Does the organisation have privileged access to that context?

---

## Decision Flow

```
Segment zone data (breadth + intensity + weight per zone)
    │
    ▼
Classification → balance check → effective classification
    │
    ▼
WTP resolution (for UNDER_ONLY and MIXED):
  ├── WTP confirmed → pricing direction: premium viable
  ├── WTP denied → pricing direction: neutral or downward
  └── WTP unknown → flag dependency; present both paths
    │
    ▼
Is the signal strong enough to justify a label?
    │
    ├── Yes → qualification questions → label (if clearly defensible)
    │
    └── No → skip label
    │
    ▼
Report output:
  1. Where to focus (outcomes ranked by opportunity score)
  2. Why (zone reading + weight rationale)
  3. Feature strategy (what to build, what to cut, what to maintain)
  4. Cost and pricing direction (derived from zone balance + WTP + qualification)
  5. Label (if assigned) + reasoning
```

---

## Cross-Segment Portfolio Prioritisation

The preceding sections describe per-segment analysis. When multiple segments exist, the company also needs guidance on which segment to pursue first. This is a portfolio-level question that sits above individual segment reports.

### Segment priority signal

Compute a portfolio-level priority score for each segment:

`priority = segment_size_pct × underserved_zone_weight`

This biases toward segments where addressing unmet needs affects the largest customer population — the most efficient path to growth in Ulwick's framing. A segment with moderate opportunity scores but 60% of the market may outrank a smaller segment with stronger signal.

This score is a starting input, not a final answer. Company-specific factors override the quantitative ranking:

- **Existing product fit** — if the current product already performs well in a segment, that segment is the fastest path to growth regardless of priority score. Ulwick's guideline: target the segment where your product currently performs best, then expand.
- **Capability match** — if the team lacks the technical or operational capability to address a segment's top underserved outcomes, that segment drops in practical priority regardless of its score.
- **Strategic intent** — a company entering a new market may deliberately target a smaller underserved segment to establish a beachhead, even when the larger segment has a higher priority score.

### Reporting

Each segment report is self-contained. The portfolio prioritisation appears as a separate summary that references the individual reports and ranks segments by priority score, with notes on which company-specific factors might alter the ranking. The summary should make the trade-offs explicit — e.g., "Segment 0 has a higher priority score (larger population, meaningful underserved signal), but Segment 1 may be a faster win if the product already serves that population well."

---

## Key Constraints

- **The report is the output. The label is scaffolding.** A label without a concrete recommendation has failed. A recommendation without a label is fine.
- **Zone weight determines emphasis, not just zone presence.** Strong asymmetry shifts the effective classification regardless of breadth thresholds.
- **Dominant requires both levers.** Do not assign it unless cost reduction and improvement are both genuinely viable.
- **Discrete is always a situational overlay.** It cannot be derived from zone data in any classification, including WELL_SERVED.
- **Disruptive in an UNDER_ONLY segment requires confirmed non-consumption.** It does not follow from underserved zone data.
- **Table stakes are a cost floor, not a differentiator.** Name them, maintain them, do not invest beyond minimum.
- **Do not force a label in the messy middle.** Go straight to the allocation map and answer the three questions directly.
- **The 20% improvement threshold** (Ulwick) is the practical bar for winning customers from incumbents. If the team cannot credibly claim ≥20% improvement on the top underserved outcomes, differentiated and dominant should not be recommended.
