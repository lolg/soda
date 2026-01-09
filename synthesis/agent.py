"""Synthesis agent for segment naming and strategy assignment."""

import asyncio

from llama_index.core.agent.workflow import AgentWorkflow
from llama_index.llms.anthropic import Anthropic

from .state import SynthesisState
from .tools import create_tools

SYSTEM_PROMPT = """You are an ODI synthesis assistant helping users name market segments and assign strategies.

## Your workflow

1. Call get_synthesis_progress to see what needs to be done
2. Work through ONE segment at a time
3. For each segment:
   - First: propose 3 name options based on segment characteristics
   - Wait for user to choose
   - Record the name with record_segment_name
   - Then: move to strategy (not implemented yet)
4. When all segments complete, summarize the results

## Rules

- Always check progress first
- Only ask about one thing at a time
- Wait for user input before recording decisions
- Keep responses focused and concise
"""


async def _run_synthesis_async(state: SynthesisState) -> SynthesisState:
    """Run synthesis agent loop."""
    
    llm = Anthropic(model="claude-sonnet-4-20250514")
    tools = create_tools(state)
    
    agent = AgentWorkflow.from_tools_or_functions(
        tools_or_functions=tools,
        llm=llm,
        system_prompt=SYSTEM_PROMPT,
    )
    
    response = await agent.run(user_msg="Begin synthesis")
    print("\n" + "="*50)
    print(response)
    
    return state


def run_synthesis(state: SynthesisState) -> SynthesisState:
    """Sync wrapper for CLI."""
    return asyncio.run(_run_synthesis_async(state))