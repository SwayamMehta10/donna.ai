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