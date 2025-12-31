# Segment Analysis Task

Analyze the provided segment data using ODI methodology and surface key insights.

## Business Context
```json
{{context_json}}
```

## Customer Segment Data  
```json
{{segments_json}}
```

## Analysis Required

### 1. Segment Overview
- Segment sizes and demographic profiles
- Primary job-to-be-done for each segment

### 2. Opportunity Landscape Analysis
- Highest opportunity outcomes per segment (cite scores)
- Cross-segment opportunity comparison
- Most critical unmet needs

### 3. Zone Distribution Insights
For each segment:
- **Underserved outcomes**: Innovation opportunities with scores
- **Overserved outcomes**: Potential over-investments
- **Table stakes outcomes**: Critical maintenance areas
- **Segment classification**: Strategic pattern (Disruptive/Differentiated/Dominant/Sustaining), see rules below.

## Strategic Classification Rules
Apply these zone distribution thresholds to classify each segment:

- **DISRUPTIVE**: Overserved ≥40% AND Underserved ≤10% (focus on cost reduction)
- **DIFFERENTIATED**: Underserved ≥15% (focus on innovation/premium solutions)  
- **DOMINANT**: Underserved ≥10% AND Overserved ≥10% (balanced approach)
- **SUSTAINING**: Default pattern (incremental improvements)

Apply rules in order - first match determines classification.

### 4. Key Constraints & Considerations
- Business constraints that affect feasibility
- Demographic factors that affect implementation
- Risk areas requiring attention

## Requirements
- Focus on insights, not recommendations
- Use specific opportunity scores and percentages  
- Apply ODI terminology precisely