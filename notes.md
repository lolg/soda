# TODO

## Segment Selection

Segment selection should be a combination of: 
- Find the best result for a segment count (using different params)
- Generate 2-5 segment.json files that are the best example in each case
- Summarize the results and get the user to pick which one

## Strategy Selection

The segment model + persona tells you what the market looks like. Segment 0 has 15 underserved outcomes around dog facilities and park infrastructure. Segment 1 has zero underserved outcomes and is overserved on everything. That's the landscape. It's objective — it comes from the data.

The strategy answers a different question: what should YOUR company do about each segment?

And the critical insight in Ulwick's framework is that the same segment data can lead to different strategies depending on who you are.

Take Segment 0 with its underserved dog facility outcomes:

A well-funded council with land → differentiated strategy. Build premium dog parks. You can deliver 20%+ improvement and the segment is big enough to justify it.
A cash-strapped council → disruptive strategy on Segment 1 instead. Strip out the overserved features (fancy playgrounds nobody values), redirect that budget. Cheaper, simpler, better aligned.
A private company with a patented modular park system → dominant strategy. Better dog facilities AND cheaper to install than traditional parks. Rare, but possible.
A small niche operator → discrete strategy. Target just the dog exercise niche within Segment 0, ignore the rest.
The data doesn't change. The persona doesn't change. But the strategy changes based on what this company can actually do. That's why the strategy step asks viability questions — "Can you charge a premium?", "Can you deliver 20%+ improvement?" — because those answers depend on the business, not the data.

So the pipeline logic is:

Segment → here are the distinct groups in your market (data)
Persona → here's what each group looks like and why it's different (data, described)
Strategy → given what YOU can do, here's the play for each segment (data + business context → decision)

The strategy step produces something like: "For Segment 0 ('underserved: dog facilities & infrastructure'), pursue a differentiated strategy because you answered yes to premium pricing and yes to delivering meaningful improvement. For Segment 1 ('overserved, no unmet needs'), pursue sustaining — no unmet needs to exploit, just maintain current service levels."