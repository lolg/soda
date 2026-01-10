"""Run synthesis workflow."""

import asyncio

from llama_index.core.workflow import HumanResponseEvent

from .state import SynthesisState
from .workflow import SynthesisWorkflow


async def _run_synthesis_async(state: SynthesisState) -> SynthesisState:
    """Run synthesis workflow with human-in-the-loop."""
    
    workflow = SynthesisWorkflow(state=state, timeout=300)
    
    handler = workflow.run()
    
    async for event in handler.stream_events():
        if hasattr(event, 'prefix'):
            suggestions = state.pending
            
            # CLI rendering here
            print(f"\n{suggestions.summary}\n")
            for i, opt in enumerate(suggestions.options, 1):
                print(f"  [{i}] {opt}")
            
            user_input = input("\n> ")
            handler.ctx.send_event(HumanResponseEvent(response=user_input))
    
    result = await handler
    return state


def run_synthesis(state: SynthesisState) -> SynthesisState:
    """Sync wrapper for CLI."""
    return asyncio.run(_run_synthesis_async(state))