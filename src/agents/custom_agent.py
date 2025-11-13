from src.utils.mylogger import logging

from datetime import datetime,timezone
from dotenv import load_dotenv

from livekit.agents import (
    Agent
)
from livekit.agents import FunctionTool
from livekit.agents.llm import ChatContext, ChatMessage
import sys

class MyAgent(Agent):

    def __init__(self, user_instructions: str, tools: list[FunctionTool]) -> None:

        logging.info("Inside MyAgent --> Custome_Agent.py")
        instructions = user_instructions
        logging.info(f"Instructions has been generated: {instructions} ")

        try:
            super().__init__(
                instructions=instructions, 
                tools=tools
            )
            logging.info(f"Agent initialized with {len(tools)} tools")
            for t in self.tools:
                logging.info(f"[MyAgent] Loaded tool: {t}")
        except Exception as e:
            logging.error(f"Failed to initialize agent: {e}")
            raise Exception(e, sys)
    
    async def before_generate_response(self, chat_ctx: ChatContext) -> ChatContext:
        """
        Prune conversation history to prevent Groq rate limit (12K TPM on free tier).
        Keep only system message + last 4 messages (2 exchanges) to stay under ~1000 tokens.
        """
        MAX_HISTORY_MESSAGES = 3  # System + 2 messages (1 user + 1 assistant) - ultra minimal for rate limits
        
        if len(chat_ctx.messages) > MAX_HISTORY_MESSAGES:
            # Keep system message + most recent messages
            system_msg = [msg for msg in chat_ctx.messages if msg.role == "system"]
            recent_msgs = [msg for msg in chat_ctx.messages if msg.role != "system"][-2:]
            
            # Clear and rebuild with pruned history
            chat_ctx.messages.clear()
            chat_ctx.messages.extend(system_msg + recent_msgs)
            
            logging.info(f"[PRUNED] Conversation history reduced to {len(chat_ctx.messages)} messages")
        
        return await super().before_generate_response(chat_ctx)