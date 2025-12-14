# Juno

Open-source ODI (Outcome-Driven Innovation) segmentation tool for product teams. Discovers outcome-based market segments from survey data.

## What it does

Juno takes survey responses (importance + satisfaction ratings on outcomes) and:

1. Runs PCA to identify key differentiating outcomes
2. Clusters respondents into segments
3. Calculates satisfaction, importance and opportunity scores for each outcome for each segment (Importance + max(Importance - Satisfaction, 0))
4. Runs multiple configurations to determine the best segment solution
5. Outputs the best segment solution for each segment count (2, 3, 4, etc.) based on silhouette score

## Why use it

- Discover outcome-based segments with different unmet needs
- Build opportunity landscapes showing underserved, overserved, table stakes, and appropriate outcomes
- Determine optimal strategy type for each segment (Differentiated, Disruptive, Dominant, etc.)
- Prioritize the biggest opportunities in the largest segments
- Match products to segments where they'll win
- Make evidence-based strategy decisions, not assumptions

## Installation
```bash
git clone https://github.com/lolg/juno.git
cd juno
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -e .
```


## Usage
```bash
juno responses.jsonl -o ./output
```

**Options:**
- `-c, --config` — Path to orchestration config JSON (optional)
- `-o, --output` — Output directory (default: ./output)
- `-v, --verbose` — Enable verbose logging

## Input Format

`responses.jsonl` — One JSON object per line:
```jsonl
{"respondentId": 1, "outcomeId": 1, "importance": 4, "satisfaction": 3}
{"respondentId": 1, "outcomeId": 2, "importance": 5, "satisfaction": 2}
{"respondentId": 2, "outcomeId": 1, "importance": 3, "satisfaction": 4}
```

**Fields:**
- `respondentId`: Integer identifier for respondent
- `outcomeId`: Integer identifier for outcome
- `importance`: Rating 1-5
- `satisfaction`: Rating 1-5

**Minimum:** ~30 respondents, 5+ outcomes  
**Recommended:** 60+ respondents per expected segment

## Output
```
output/
├── summary.json      # Comparison across all solutions
├── segments_2.json   # Best 2-segment model
├── segments_3.json   # Best 3-segment model
└── segments_4.json   # Best 4-segment model
```

**Example `summary.json`:**
```json
{
  "generated_at": "2025-01-27T14:30:00Z",
  "input_file": "responses.jsonl",
  "solutions": [
    {
      "num_segments": 2,
      "silhouette_score": 0.42,
      "segment_sizes": [58.5, 41.5],
      "combined_score": 0.68,
      "output_file": "segments_2.json"
    }
  ],
  "recommended": 3
}
```

**Example `segments_2.json`:**
```json
{
  "segments": [
    {
      "segment_id": 0,
      "size_pct": 58.5,
      "outcomes": [
        {
          "outcome_id": 1,
          "sat_tb": 72.2,
          "imp_tb": 85.7,
          "opportunity": 9.92
        }
      ]
    },
    {
      "segment_id": 1,
      "size_pct": 41.5,
      "outcomes": [
        {
          "outcome_id": 1,
          "sat_tb": 76.7,
          "imp_tb": 77.3,
          "opportunity": 7.79
        }
      ]
    }
  ]
}
```

## Configuration

Default parameters work for most cases. To customize, create a config JSON:
```json
{
  "parameters": {
    "num_segments": [2, 3, 4],
    "max_cross_loading": [0.36, 0.40],
    "min_primary_loading": [0.40, 0.44],
    "random_state": [3, 6, 10, 12]
  },
  "constraints": [
    {"type": "less_than", "left": "max_cross_loading", "right": "min_primary_loading"}
  ],
  "scoring": {
    "silhouette_weight": 0.6,
    "balance_weight": 0.4
  }
}
```

## Run with example data
```bash
juno data/real/mdi/responses.jsonl
```

See data/real/mdi/README.md for more information about this dataset. 


## Background

Based on Tony Ulwick's Outcome-Driven Innovation methodology. For more on ODI, see [Strategyn](https://strategyn.com/).

## License

MIT
