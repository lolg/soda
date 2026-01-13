"""High-level strategy assignment API."""

import asyncio
from typing import Callable

from llama_index.core.agent.workflow import AgentWorkflow
from llama_index.core.tools import FunctionTool
from llama_index.llms.anthropic import Anthropic

from soda.core.config import StrategyConfig
from soda.core.models import SegmentModelWithAssignments, Segment, StrategyAssignment


SYSTEM_PROMPT = """You are an expert in Outcome-Driven Innovation (ODI) and Jobs-to-be-Done (JTBD) methodology.

You help product teams assign strategies to market segments based on customer outcome data. You understand:
- Underserved outcomes indicate opportunity for differentiation (premium, better product)
- Overserved outcomes indicate potential for disruption (simpler, cheaper)
- Both underserved AND overserved is rare - dominant strategy requires breakthrough
- No clear opportunity means sustaining (incremental improvements)
"""

STRATEGY_PROMPT = """You assign strategies to market segments. Work through ALL segments needing a strategy.

IMPORTANT: You MUST ask viability questions - you cannot determine viability on your own.

For each segment:
1. Call get_segments_overview to see which need strategy assignment
2. Call get_segment_details to understand the segment
3. Call get_possible_strategies to see which could apply
4. For EACH possible strategy:
   - Call get_strategy_info to get its questions
   - Call ask_viability_question for EVERY question - DO NOT SKIP THIS
   - A strategy is only viable if ALL questions are answered "yes" by the user
5. After asking all questions:
   - None viable → record "sustaining" with warning
   - One viable → record it
   - Multiple viable → call choose_strategy
6. Call record_strategy with reasoning

You MUST call ask_viability_question for every question. The user's business context determines viability, not the data alone.

Continue until all segments have strategies assigned."""


def create_strategy_tools(
    segment_model: SegmentModelWithAssignments,
    strategy_config: StrategyConfig,
    on_question: Callable[[str, Segment], bool],
    on_choice: Callable[[list[str], Segment], str]
) -> list[FunctionTool]:
    """Tools for strategy assignment."""
    
    # Track viability answers per segment for recording
    viability_answers: dict[int, dict[str, bool]] = {}
    
    def get_segments_overview() -> dict:
        """Get overview of all segments - which need strategy assignment."""
        return {
            "total_segments": len(segment_model.segments),
            "segments": [
                {
                    "id": s.segment_id,
                    "name": s.name,
                    "size_pct": s.size_pct,
                    "has_strategy": s.strategy is not None,
                    "needs_strategy": s.strategy is None
                }
                for s in segment_model.segments
            ]
        }
    
    def get_segment_details(segment_id: int) -> dict:
        """Get detailed info about a segment including zones and demographics."""
        seg = next(s for s in segment_model.segments if s.segment_id == segment_id)
        return {
            "segment_id": segment_id,
            "name": seg.name,
            "size_pct": seg.size_pct,
            "demographics": seg.demographics or {},
            "has_underserved": len(seg.zones.underserved.outcomes) > 0,
            "has_overserved": len(seg.zones.overserved.outcomes) > 0,
            "underserved_count": len(seg.zones.underserved.outcomes),
            "overserved_count": len(seg.zones.overserved.outcomes),
            "underserved_outcomes": [
                {"id": o.outcome_id, "description": o.description, "opportunity": o.opportunity}
                for o in seg.zones.underserved.outcomes[:5]
            ],
            "overserved_outcomes": [
                {"id": o.outcome_id, "description": o.description}
                for o in seg.zones.overserved.outcomes[:5]
            ],
        }
    
    def get_possible_strategies(segment_id: int) -> dict:
        """Get strategies whose conditions are met for this segment."""
        seg = next(s for s in segment_model.segments if s.segment_id == segment_id)
        has_underserved = len(seg.zones.underserved.outcomes) > 0
        has_overserved = len(seg.zones.overserved.outcomes) > 0
        
        possible = strategy_config.get_possible(has_underserved, has_overserved)
        
        return {
            "segment_id": segment_id,
            "has_underserved": has_underserved,
            "has_overserved": has_overserved,
            "possible_strategies": possible
        }
    
    def get_strategy_info(strategy_name: str) -> dict:
        """Get description and questions for a strategy."""
        if strategy_name not in strategy_config.strategies:
            return {"error": f"Unknown strategy: {strategy_name}"}
        
        defn = strategy_config.strategies[strategy_name]
        return {
            "name": strategy_name,
            "description": defn.description,
            "questions": [{"id": q.id, "text": q.text} for q in defn.questions]
        }
    
    def ask_viability_question(segment_id: int, strategy_name: str, question_id: str, question_text: str) -> dict:
        """Ask user a viability question. Returns their answer."""
        print(f"  [DEBUG] Asking: {question_id}")
        seg = next(s for s in segment_model.segments if s.segment_id == segment_id)
        
        answer = on_question(question_text, seg)
        
        # Track answer
        if segment_id not in viability_answers:
            viability_answers[segment_id] = {}
        viability_answers[segment_id][question_id] = answer
        
        return {
            "segment_id": segment_id,
            "strategy": strategy_name,
            "question_id": question_id,
            "answer": answer
        }
    
    def choose_strategy(segment_id: int, viable_strategies: list[str]) -> str:
        """When multiple strategies are viable, ask user to choose."""
        seg = next(s for s in segment_model.segments if s.segment_id == segment_id)
        return on_choice(viable_strategies, seg)
    
    def record_strategy(segment_id: int, strategy_name: str, reasoning: str, warning: str = None, viable_options: list[str] = None) -> str:
        """Record the strategy assignment for a segment."""
        seg = next(s for s in segment_model.segments if s.segment_id == segment_id)
        
        # Enforce that questions were asked (unless sustaining with no possible strategies)
        answers = viability_answers.get(segment_id, {})
        if strategy_name != "sustaining" and not answers:
            return f"ERROR: Cannot record strategy '{strategy_name}' - no viability questions were asked. You MUST call ask_viability_question first."
        
        seg.strategy = StrategyAssignment(
            name=strategy_name,
            viable_options=viable_options or [],
            viability_answers=answers,
            reasoning=reasoning,
            warning=warning
        )
        
        return f"Recorded strategy '{strategy_name}' for segment {segment_id} ({seg.name})"
    
    return [
        FunctionTool.from_defaults(
            fn=get_segments_overview,
            name="get_segments_overview",
            description="Get overview of all segments showing which need strategy assignment"
        ),
        FunctionTool.from_defaults(
            fn=get_segment_details,
            name="get_segment_details",
            description="Get detailed info about a segment including outcome zones and demographics"
        ),
        FunctionTool.from_defaults(
            fn=get_possible_strategies,
            name="get_possible_strategies",
            description="Get strategies whose conditions are met based on segment's underserved/overserved outcomes"
        ),
        FunctionTool.from_defaults(
            fn=get_strategy_info,
            name="get_strategy_info",
            description="Get description and viability questions for a specific strategy"
        ),
        FunctionTool.from_defaults(
            fn=ask_viability_question,
            name="ask_viability_question",
            description="REQUIRED: Ask user a viability question. Args: segment_id, strategy_name, question_id, question_text. Returns the user's yes/no answer."
        ),
        FunctionTool.from_defaults(
            fn=choose_strategy,
            name="choose_strategy",
            description="When multiple strategies are viable, ask user to choose. Args: segment_id, viable_strategies (list). Returns chosen strategy name."
        ),
        FunctionTool.from_defaults(
            fn=record_strategy,
            name="record_strategy",
            description="Record final strategy assignment. Will FAIL if ask_viability_question was not called first. Args: segment_id, strategy_name, reasoning, warning (optional), viable_options (optional list)"
        )
    ]


async def _strategy_async(
    segment_model: SegmentModelWithAssignments,
    strategy_config: StrategyConfig,
    on_question: Callable[[str, Segment], bool],
    on_choice: Callable[[list[str], Segment], str]
) -> SegmentModelWithAssignments:
    """Assign strategies to all segments - agent controls the loop."""
    
    # Check if any need strategy
    needs_strategy = [s for s in segment_model.segments if s.strategy is None]
    if not needs_strategy:
        print("All segments already have strategies. Nothing to do.")
        return segment_model
    
    print(f"{len(needs_strategy)} segment(s) need strategy assignment...")
    
    llm = Anthropic(model="claude-sonnet-4-20250514")
    tools = create_strategy_tools(segment_model, strategy_config, on_question, on_choice)
    
    agent = AgentWorkflow.from_tools_or_functions(
        tools_or_functions=tools,
        llm=llm,
        system_prompt=SYSTEM_PROMPT + "\n\n" + STRATEGY_PROMPT,
    )
    
    response = await agent.run(user_msg="Assign strategies to all segments that need them", max_iterations=50)
    print(f"\nAgent: {response}")
    
    return segment_model


def strategy(
    segment_model: SegmentModelWithAssignments,
    strategy_config: StrategyConfig,
    on_question: Callable[[str, Segment], bool],
    on_choice: Callable[[list[str], Segment], str]
) -> SegmentModelWithAssignments:
    """Assign strategies to segments. Sync wrapper."""
    return asyncio.run(_strategy_async(segment_model, strategy_config, on_question, on_choice))