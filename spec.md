Soda (Segment Outcome Data Analysis): Outcome-Driven Innovation (ODI) Engine

Version: 0.0.1
Status: Technical Specification
Primary Model: claude-sonnet-4-20250514

# 1 Product Overview
Soda is a technical analysis tool that automates the Outcome-Driven Innovation (ODI) methodology. It bridges the gap between raw survey data and strategic product roadmaps by using a deterministic quantitative pipeline followed by an agentic reasoning layer.

Small and medium businesses (SMBs) often struggle to translate raw customer survey data into actionable product roadmaps. Soda automates the Outcome-Driven Innovation (ODI) methodology, moving from raw satisfaction/importance ratings to prioritized market segments and AI-reasoned growth strategies.

## 1.1 Scope & Prerequisites

Data Cleaning: This pipeline does not perform data cleaning or imputation. It assumes the input data is "Golden"—pre-processed, deduplicated, and handled for missing values.

Methodology: Strict adherence to Tony Ulwick's JTBD/ODI framework.

# 2. Data Architecture

## 2.1 Injestion Schema (JSONL)

The core data set consists of respondent ratings. All inputs are validated via Pydantic before processing. This is referred to as responses.jsonl

```
{"respondentId": 1, "outcomeId": 1, "importance": 4, "satisfaction": 4}
```

importance and satisfaction scores are in the range 1-5

## 2.2 Metadata & Taxonomy (JSON)

To provide demographic information for each segment and additional context for later steps, Soda requires an outcome map and a categorical codebook.

### Outcomes

Describes the ODI-style (see ODI guidelines on functional outcome statements) outcome statements for the outcome ids contained in the responses.jsonl. This is referred to as outcomes.json 

```
{"id": 2, "text": "Minimize the likelihood of missing relevant products when searching"},
```

### Demographics

The demographics are provided with 2 files:

- respondents.json and
- codebook.json

Respondents.json has form:

```
{"respondentId":20,"D1":1,"D2":4,"D3":1}
```

this maps the respondent id to categorial questions and their respective answers as described in codebook.json.

```
[
{
	"id": "D1",
	"name": "gender",
	"text": "How do you describe yourself?",
	"options": {"1": "Female", "2": "Male", "3": "Other", "4": "Prefer not to disclose", "5": "No Response"},
	"missing_codes": ["4","5"]
},
```

## Quantitive Analysis

The quantitive pipeline is designed to ingest the responses.jsonl and build a segment model. It uses a orchestration/grid search. The pipeline depends on the aforementioned resources.json; and a soda-rules.yaml configuration file as follows:


```
metadata:
	version: "1.1.0"
	description: "SODA rules"

orchestration:
	parameters:
		num_segments: [2, 3, 4]
		max_cross_loading: [0.36, 0.40, 0.42, 0.46]
		min_primary_loading: [0.40, 0.44, 0.48, 0.50]
		random_state: [3, 6, 10, 12]
		
	constraints:
		- type: "less_than"
			left: "max_cross_loading"
			right: "min_primary_loading"
			rationale: "Prevents outcomes from loading heavily on multiple factors"
			
selection_rules:
	min_segment_size_percent: 8.0
	min_silhouette: 0.15
	silhouette_weight: 0.6
	balance_weight: 0.4

zone_classification:
	opportunity_threshold: 10.0  
	importance_threshold: 60.0    
	satisfaction_threshold: 50.0
```

### Segmentation

This is a pipeline - sequence of steps. The pipeline runs for each combination of parameters as defined in the orchestration parameters. The orchestrator runs all configs and then selects the one with the highest score based on the selection rules. 

The pipeline steps are:

1. Standardize Importance - Expresses each rating in terms of how far it is from the average.
2. Compute PCA component - identifies underlying correlated "themes", removing redundancy from the data. This is done on the importance (outcome importance) values only (not satisfaction) This number of components is used as an input to the next step. Supports "kaiser" and "variance threshold" options for determining the number of components.
3. Compute Factor Loadings - This shows us how each importance (outcome importance) value contributes to each component.
4. Select Key Outcomes - This selects the outcomes that best represent each component. It avoids outcomes that load strongly on multiple components (cross-loading). Inputs are max_outcomes_per_component (default 2) maximum_cross_loading and minimal_primary_loading. Returns a list of outcome importances e.g. OutcomeImportance_20, OutcomeImportance_11, OutcomeImportance_3
5. ComputeOpportunityProfiles() - this filters the original responses to include just the importance and their corresponding satisfaction values. It uses the opportunity scoring formula:

importance + np.maximum(importance - satisfaction, 0)

It also adds the opportunity scores to dataset:

```
| RespondentID | ... | Opportunity_10 | Opportunity_11 | ... | SegmentID |
|--------------|-----|----------------|----------------|-----|-----------|
```

6. AssignSegments - Uses k-means to identify segments for the opportunity columns. The inputs include the number of segments to identify and a random state. The return value is:

```
| RespondentID | OutcomeImp_1 | OutcomeImp_N |...| OutcomeSat_1 | OutcomeSat_N |...| Opp_12 | Opp_23 |...| SegmentID |
|--------------|--------------|--------------|...|--------------|--------------|...|--------|--------|...|-----------|
```

7. CharacterizeSegments -Here we select all respondents in that cluster, look across all outcomes, count how many respondents rated an outcome as 4 or 5 (on a 1-5 scale) and then compute the percentage of such respondents within that cluster. We also compute the aggregate opportunity using the opportunity formula.

This gives us:

```
| SegmentID | OutcomeID | Sat_T2B | Imp_T2B | OPP_TB |
------------|---------------------|---------|--------|
| 0         | 12        | 72.2    | 85.7    | 9.92   |
| ...       | ...       | ...     | ...     |				 |
| 1         | 7         | 72.6    | 38.7    | 3.87   |
| ...       | ...       | ...     | ...     |				 |
| 2         | 23        | 70.0    | 53.9    | 5.39   | 
```

It also returns the segment sizes:

```
| SegmentID | Percentage |
|-----------|------------|
| 0         | 32.0       |
| 1         | 68.0       |
```

The pipeline is run for each configuration by the SegmentBuilder class. For each run the results are formatteed into a segments.json. In addition, it uses a zone classifier which is configured in the soda-rules.yaml to determine which outcomes are underserved, overserved, table_stakes and appropriate served. The final segments.json (shown here with only 1 outcome per zone for brevity) is then:

```
{
	"segments": [
		{
			"segment_id": 0,
			"size_pct": 58.5,
			"zones": {
				"underserved": {
					"pct": 13.6,
					"outcomes": [
						{
							"outcome_id": 5,
							"description": null,
							"sat_tb": 24.3,
							"imp_tb": 99.6,
							"opportunity": 17.49
						},
					]
				},
				"overserved": {
					"pct": 36.4,
					"outcomes": [
						{
							"outcome_id": 2,
							"description": null,
							"sat_tb": 72.6,
							"imp_tb": 38.7,
							"opportunity": 3.87
						}
					]
				},
				"table_stakes": {
					"pct": 40.9,
					"outcomes": [
						{
							"outcome_id": 1,
							"description": null,
							"sat_tb": 72.2,
							"imp_tb": 85.7,
							"opportunity": 9.92
						}
					]
				},
				"appropriate": {
					"pct": 9.1,
					"outcomes": [
						{
							"outcome_id": 14,
							"description": null,
							"sat_tb": 43.0,
							"imp_tb": 44.3,
							"opportunity": 4.56
						},
						{
							"outcome_id": 19,
							"description": null,
							"sat_tb": 33.0,
							"imp_tb": 33.0,
							"opportunity": 3.3
						}
					]
				}
			},
			"demographics": null
		},
		{
			"segment_id": 1,
			"size_pct": 41.5,
			"zones": {
				"underserved": {
					"pct": 0.0,
					"outcomes": []
				},
				"overserved": {
					"pct": 50.0,
					"outcomes": [
						{
							"outcome_id": 2,
							"description": null,
							"sat_tb": 67.5,
							"imp_tb": 36.8,
							"opportunity": 3.68
						}
					]
				},
				"table_stakes": {
					"pct": 31.8,
					"outcomes": [
						{
							"outcome_id": 1,
							"description": null,
							"sat_tb": 76.7,
							"imp_tb": 77.3,
							"opportunity": 7.79
						}
					]
				},
				"appropriate": {
					"pct": 18.2,
					"outcomes": [
						{
							"outcome_id": 9,
							"description": null,
							"sat_tb": 46.6,
							"imp_tb": 58.9,
							"opportunity": 7.12
						}
					]
				}
			},
			"demographics": null
		}
	],
	"segment_assignments": {
		"assignments": {
			"0": [
				6, 7, 8, 10, 11, 12, 13, 14, 15, 16
			],
			"1": [
				1, 2, 3, 4, 5, 9, 17, 18, 22, 28
			]
		}
	}
}
```

This is missing the outcome description and demographics information which are added in the (next) enrichment step. Even without the demographics and outcome descriptions, its possible to derive insights from this analysis.

### Enrichment

In this step, the outcome information and demographics are added to the segments.json, using the segment assignments stored in the json to determine the percentages for the demographics. The following is inserted for each segment in segments.json:

```
	"demographics": {
		"gender": {
			"Female": 66.4,
			"Male": 33.2,
			"Other": 0.4
		},
		"age_group": {
			"45-54": 29.5,
			"65+": 25.1,
			"55-64": 22.5,
			"35-44": 11.0,
			"25-34": 6.2,
			"18-24": 5.7
		},
		"residence_group": {
			"Surrounding Suburbs (<5 km)": 80.4,
			"Other Metropolitan Suburbs": 15.2,
			"Other Australian States": 1.7,
			"International": 1.3,
			"Regional Western Australia": 1.3
		}
	}
```

## Qualitative/Agent Analysis

The next steps involve agents that enrich segment model.

### Naming

Here an agent is given a set of tools:

- Get overview of all segments showing which need naming
- Get detailed info about a segment including demographics and outcomes
- Present naming options to user and get their choice (multiple choice). Returns the chosen name
- Record the final chosen name for a segment

And for each segment, the user is asked by the agent to pick from 1 of 3 options - it is the agent's responsibility to define the names and the user's responsibility to pick a name.  The LLM is instructed to generate suitable name suggestions based on the segment information contained (coming from segments.json).

The name picked by the user are stored back in segments.json as follows:

```

"segment_id": 0,
"name": "On the move, family oriented shoppers ", <- Inserted here
"size_pct": 58.5
```

### Strategy

Here the agent uses a set of rules,  contained in the soda-rules.yaml:

```
strategies:
differentiated:
	description: "Premium product addressing underserved needs"
	conditions:
		- has_underserved
	questions:
		- id: premium_pricing
			text: "Can you charge a premium price in this market?"
		- id: deliver_improvement
			text: "Can you deliver meaningful improvement (20%+) on underserved outcomes?"

disruptive:
	description: "Simpler/cheaper product sacrificing overserved features"
	conditions:
		- has_overserved
	questions:
		- id: lower_price
			text: "Can you offer a lower price point?"
		- id: simpler_solution
			text: "Can you deliver a simpler solution that sacrifices overserved outcomes?"

dominant:
	description: "Better AND cheaper - rare breakthrough opportunity"
	conditions:
		- has_underserved
		- has_overserved
	questions:
		- id: breakthrough
			text: "Do you have a breakthrough that enables both premium value AND lower cost?"

sustaining:
	description: "Incremental improvements - default when no clear opportunity"
	conditions: []
	questions: []
	default: true
```
	
Accessed, among other things, with the following tools:

- Get overview of all segments showing which need strategy assignment
- Get detailed info about a segment including outcome zones and demographics
- Get strategies whose conditions are met based on segment's underserved/overserved outcomes
- Get description and viability questions for a specific strategy
- Ask user a viability question. Args: segment_id, strategy_name, question_id, question_text. Returns the user's yes/no answer
- When multiple strategies are viable, ask user to choose. Returns chosen strategy name
- Record final strategy assignment.

Once complete a strategy section for each segment into segments.json as follows:

```
 "strategy": {
		"name": "differentiated",
		"viable_options": [],
		"viability_answers": {
			"premium_pricing": true,
			"deliver_improvement": true,
			"lower_price": false,
			"breakthrough": false
		},
		"reasoning": "This segment has strong underserved outcomes around dog exercise areas and high-quality infrastructure (opportunity scores of 17.49, 16.35, and 11.17). They can pay premium prices and meaningful improvements can be delivered on these underserved outcomes. The overserved outcomes (bird watching infrastructure, children's playgrounds, etc.) suggest they don't value certain amenities, but the differentiated strategy focuses on improving what they do value."
	}
}
```

### Report

In the final step, an agent generates a markdown report based on the segments.json. The agent is provided with a single tool:

- get_report_data, to get all segment data needed for the report including demographics, zones, outcomes, and strategies

And it generates a markdown report in the form of:

Report structure:

# ODI Segmentation Analysis Report
## Executive Summary
## Market Overview (include table: segment | size % | strategy)
## Segment Profiles (one subsection per segment with demographics, needs, strategy, actions)
## Cross-Segment Insights
## Next Steps


# Next Steps (Not Yet Implemented)

## Improve Orchestration

Add support for additional parameters that control segmentation quality.	

## Naming Judge Agent (in concert with the Naming Agent)

Judge reviews the naming agents suggestions.

Naming Agent                          Judge
|                                   |
|-- proposes name + summary ------->|
|                                   |-- sees: name, summary, key data
|                                   |-- scores: does name match?
|<-- accept/reject + feedback ------|

┌─────────────────────────────────────────────┐
│  Main Agent (proposer)                      │
│                                             │
│  Tools:                                     │
│    - get_data()                             │
│    - propose_X()  ──────┐                   │
│    - record_X()         │                   │
│                         ▼                   │
│              ┌──────────────────┐           │
│              │  Judge (tool)    │           │
│              │  - calls LLM     │           │
│              │  - returns pass/ │           │
│              │    fail + reason │           │
│              └──────────────────┘           │
└─────────────────────────────────────────────┘

### Example Code

def judge_name(
		proposed_name: str,
		summary: str,  # from naming agent
		segment_data: dict  # key facts
) -> dict:
		prompt = f"""Rate this segment name.
		
### Prompt Suggestion

Prompt: Name ODI Segments (Outcome-Based, Storytelling Style)

You are naming customer segments derived from Outcome-Driven Innovation (ODI). Segments are defined by patterns in underserved / overserved / table-stakes / appropriately-served outcomes, plus supporting demographics (demographics are explanatory, not defining).

For each segment, propose 3–5 candidate names that are creative, memorable, and useful for strategy + reporting, while staying accurate.

Naming rules
	•	Anchor on outcomes: Name the segment after its defining outcomes / unmet needs / value sought (not demographics, not solution features).
	•	Customer-centric framing: Express what the segment is trying to achieve or optimize (functional + emotional where relevant).
	•	Clarity first, creativity second: A smart stakeholder should “get it” instantly without ODI jargon.
	•	Short + distinct: 2–4 words max; avoid formulaic patterns that make names blend together.
	•	Memorable hooks: Use vivid verbs/nouns, light alliteration/metaphor if it fits (no cringe, no forced themes).
	•	No analysis labels: Don’t use “underserved/overserved/table-stakes” in the name; translate into plain language (e.g., “Simplifiers”, “Risk Reducers”, “Proof Seekers”).
	•	Positive and respectful: No insulting or stigmatizing labels.
	•	Strategy utility: Names should help teams reason about positioning, roadmap focus, and tradeoffs.

Output format (per segment)
	1.	Top pick: Name — one-sentence rationale tied to the segment’s top outcomes and unmet-need pattern.
	2.	Alternatives: 2–4 names — each with a short rationale.
	3.	Do-not-use list: 2 examples of names that would be misleading (and why).

Use the segment’s outcome list and unmet-need classifications as the primary evidence; use demographics only to refine tone/imagery.

### Strategy Judge Agent

Similar patterns as for the Naming Agent - not more details as of yet.

### Constrained Convergence Strategy Agent

The strategy agent is designed to reason its way to a decision, not to mechanically execute predefined rules.

Rather than following a fixed sequence encoded in YAML, the agent is given:
	•	A bounded strategy space (valid ODI strategies only),
	•	Grounded segment context (outcomes, zones, demographics),
	•	And a small set of constraint functions that limit what it can propose or commit to.

Within these boundaries, the agent uses its own expertise to:
	•	Form hypotheses about which strategies might fit a segment,
	•	Identify what uncertainty must be resolved to choose between them,
	•	Ask targeted questions that reduce that uncertainty,
	•	And iteratively converge on a single, defensible strategy.

Rules no longer dictate what to ask or what to choose.
They define what is allowed, what must be true, and what happens when no option is viable (fallback to sustaining).

Convergence is achieved through reasoning plus interaction, not orchestration.
The result is a system that is:
	•	More flexible than a rule engine,
	•	More grounded than free-form generation,
	•	And explainable through the recorded decision path.


### RAG Agent

- For use by the naming, strategy and judge agents.
- Uses a corpus of research papers, ODI course material and literature 


## Testing


is basically a state machine:
	1.	ask a set of questions
	2.	record normalized answers in the manifest
	3.	compute a strategy decision that must be consistent with those answers + ODI rules
	4.	output the decision in a strict, testable structure
	5.	write normal code tests like: given answers X, expect strategy type Y (and required fields Z)

The crucial move

Don’t just have the LLM write a free-form “strategy paragraph”.
Have it write a decision object with:
	•	strategy_type (enum)
	•	rationale (short text)
	•	rule_checks (rule_id + pass/fail + evidence)
	•	evidence (manifest pointers)
	•	next_steps (list)

Then your tests can be deterministic.

⸻

What “specific structure and values” should look like

Example schema (conceptual)
	•	strategy.type: one of:
	•	"sustaining"
	•	"adjacent"
	•	"disruptive_low_end"
	•	"disruptive_new_market"
	•	"differentiation"
	•	(whatever your ODI strategy set is)
	•	strategy.confidence: "low"|"medium"|"high" (optional)
	•	strategy.rationale_bullets: array of short strings
	•	strategy.evidence: array of manifest paths, e.g.
	•	"/strategy_answers/improve_underserved_20pct"
	•	"/segment/underserved_outcomes"
	•	"/constraints/budget"
	•	strategy.rule_checks: array of objects like
	•	{ "rule_id": "ODI-S1", "passed": true, "evidence": ["/strategy_answers/..."] }

This lets you test the decision, not the prose.

⸻

How tests work (exactly what you said)

You can absolutely write tests like:

If answer A = “no” and answer B = “yes”, then strategy.type must be “sustaining” (or whatever your mapping is).

Example mapping idea (illustrative)

Let’s name your questions:
	•	Q1: can_improve_underserved_20pct (yes/no/unsure)
	•	Q2: can_simplify_without_sacrificing_underserved (yes/no/unsure)
(your wording is “simpler solutions that sacrifice underserved outcomes” — so this is basically “can we go cheaper/simpler even if it worsens key underserved outcomes?” which usually points toward disruption / low-end logic)

Then rules might look like:
	•	If Q1=yes ⇒ you have capability to differentiate on underserved outcomes
	•	If Q1=no AND Q2=no ⇒ you can’t improve meaningfully and can’t simplify safely ⇒ sustaining
	•	If Q2=yes (and maybe the segment is overserved on some dimensions) ⇒ low-end or simplification play

Whether those exact mappings are “ODI-correct” depends on how you define your strategy taxonomy — but the mechanism is correct.

⸻

What’s important: test invariants in addition to “if X then Y”

Besides “mapping” tests, you also want invariants like:
	•	No strategy without required answers
	•	if any required question is unanswered ⇒ strategy.status != "final"
	•	Every strategy must be traceable
	•	strategy must include at least N evidence pointers
	•	Every hard rule must be present
	•	strategy must include rule_checks for all relevant rules
	•	Enums only
	•	no random strings for strategy.type

These are simple, reliable automated tests.

⸻

One subtlety: “unsure”

“unsure” is where people get stuck.

You handle it by defining policy up front, for example:
	•	if “unsure” on a gating question ⇒ default to sustaining or ask follow-up questions or set confidence="low" and output “needs discovery”.

That itself is testable.
