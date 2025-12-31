from datetime import datetime
from typing import List

from soda.synthesis.agents.data_analyst import DataAnalystAgent
from soda.synthesis.agents.devils_advocate import DevilsAdvocateAgent
from soda.synthesis.clients.base_client import create_message
from soda.synthesis.models import AgentInput, AgentOutput


class ConversationOrchestrator:
    """Manages conversation between DataAnalyst and DevilsAdvocate."""
    
    def __init__(self, analyst: DataAnalystAgent, advocate: DevilsAdvocateAgent):
        self.analyst = analyst
        self.advocate = advocate
    
    async def run_debate(self, agent_input: AgentInput, max_turns: int = 4) -> List[AgentOutput]:
        """Run a structured debate between analyst and advocate."""
        
        outputs = []
        
        # Turn 1: Analyst provides initial analysis
        print("🔍 DataAnalyst: Providing initial analysis...")
        analyst_output = await self.analyst.process(agent_input)
        outputs.append(analyst_output)
        
        # Start conversation history
        conversation = [
            create_message("system", self.advocate.system_prompt),
            create_message("user", f"Challenge this analysis:\n\n{analyst_output.content}")
        ]
        
        for turn in range(max_turns - 1):  # -1 because analyst already went first
            if turn % 2 == 0:  # Advocate's turn
                print(f"⚔️  DevilsAdvocate: Turn {turn//2 + 1}")
                advocate_output = await self.advocate.challenge_via_chat(conversation)
                outputs.append(advocate_output)
                
                # Add advocate response to conversation
                conversation.append(create_message("assistant", advocate_output.content))
                
                # If not final turn, prepare for analyst response
                if turn < max_turns - 2:
                    conversation.append(create_message("user", "Please respond to this challenge:"))
                    
            else:  # Analyst's turn to respond
                print(f"🔍 DataAnalyst: Response {turn//2 + 1}")
                
                # Switch to analyst's system prompt for their response
                analyst_conversation = [
                    create_message("system", self.analyst.system_prompt),
                    create_message("user", f"Original analysis:\n{analyst_output.content}"),
                    create_message("assistant", "I provided this analysis."),
                    create_message("user", f"Challenge received:\n{outputs[-1].content}\n\nPlease respond to this challenge:")
                ]
                
                response = await self.analyst.client.chat(
                    messages=analyst_conversation,
                    max_tokens=self.analyst.llm_config.max_tokens,
                    temperature=self.analyst.llm_config.temperature
                )
                
                analyst_response = AgentOutput(
                    agent_name=self.analyst.name,
                    content=response.content,
                    confidence=0.0,
                    timestamp=datetime.now()
                )
                outputs.append(analyst_response)
                
                # Update conversation for next advocate turn
                conversation[-1] = create_message("user", f"Analyst responds:\n{analyst_response.content}\n\nWhat is your next challenge?")
        
        return outputs