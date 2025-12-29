# Segment Analysis Task

You are provided with customer segment data and business context to analyze using ODI methodology.

## Business Context
The following JSON contains your business constraints and priorities:
```json
{{context_json}}
```

This includes budget, timeline, team size, constraints, and strategic priorities.

## Customer Segment Data
The following JSON contains enriched customer segments with ODI zone analysis:
```json
{{segments_json}}
```

This data includes:
- **Segments**: Customer groups with size percentages and demographics
- **Zones**: ODI classification (underserved, overserved, table_stakes, appropriate) 
- **Outcomes**: Specific customer outcomes with importance, satisfaction, and opportunity scores
- **Demographics**: Age, gender, location breakdowns per segment

## Analysis Structure

### 1. Segment Overview
- Total segments and their relative sizes (cite percentages)
- Primary job-to-be-done for each segment
- Key demographic insights that affect strategy

### 2. Opportunity Landscape  
- Highest opportunity outcomes per segment (cite scores)
- Cross-segment opportunity comparison
- Strategic urgency assessment based on opportunity math

### 3. Zone Distribution Analysis
For each segment:
- **Underserved outcomes**: Innovation opportunities with opportunity scores
- **Overserved outcomes**: Cost reduction candidates  
- **Table stakes outcomes**: Critical maintenance items
- **Strategic classification**: Disruptive/Differentiated/Dominant/Sustaining

### 4. Resource Allocation Insights
- Priority segments based on size × opportunity
- Solution types needed (premium vs basic vs cost reduction)
- Implementation risks and business constraints
- Demographic considerations for targeting

## Key Requirements
- Be specific with numbers (opportunity scores, percentages)
- Use ODI terminology precisely
- Focus on actionable insights
- Consider business context constraints