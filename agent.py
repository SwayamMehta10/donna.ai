from __future__ import annotations
import requests
from pydantic import BaseModel
import os
import logging
from dotenv import load_dotenv
import json
import time
import asyncio
from datetime import datetime, timezone
from pathlib import Path
import uuid
from dataclasses import asdict
from livekit import api
from livekit.agents import cli, WorkerOptions, WorkerType, AutoSubscribe, JobContext, metrics, JobProcess
from livekit.agents.metrics import AgentMetrics, UsageCollector
from livekit.plugins import silero,  openai, noise_cancellation
from livekit.plugins.turn_detector.multilingual import MultilingualModel
from livekit.plugins.openai.realtime import RealtimeModel
from openai.types.beta.realtime.session import TurnDetection, InputAudioNoiseReduction
from livekit.agents import FunctionTool
import sys
from livekit.agents import ChatContext, ChatMessage, StopResponse
from livekit.plugins.openai import InputAudioNoiseReduction
from livekit.agents import (
    Agent,
    AgentSession,
    JobContext,
    JobProcess,
    RoomInputOptions,
    RoomOutputOptions,
    RunContext,
    WorkerOptions,
    cli,
    metrics,
    llm
)

from room_management import delete_lk_room
from livekit.agents import metrics, MetricsCollectedEvent
from livekit.agents.llm import function_tool
from livekit.agents.voice import MetricsCollectedEvent
from livekit.plugins.turn_detector.english import EnglishModel

import fastapi
load_dotenv()


class MyAgent(Agent):
    
    def __init__(self,use_rag, user_instructions: str, tools: list[FunctionTool], welcome_msg:str) -> None:

        self.use_rag= use_rag
        logging.info("Inside MyAgent --> Custome_Agent.py")
        self.welcome_msg = welcome_msg
        instructions = user_instructions
        logging.info(f"Instructions has been generated: {instructions} ")
        try:
            super().__init__(instructions=instructions, tools=tools)
            logging.info(f"Agent initialized with {len(tools)} tools")
            for t in self.tools:
                logging.info(f"[MyAgent] Loaded tool: {t}")
        except Exception as e:
            logging.error(f"Failed to initialize agent: {e}")
            raise Exception(e, sys)

def prewarm_process(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load(min_silence_duration=0.3)

# Entrypoint for agent worker
async def entrypoint(ctx: JobContext):
    """Entry point for the agent."""
    logging.info("Inside Entry Point Function")
    logging.info(f"Room Name: Agent Creation -> {ctx.room.name}")
    # USER_ID = ctx.room.name

    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)  

    metadata= json.loads(ctx.job.metadata)
    if ctx.room is None:
        logging.info("ERROR: ctx.room is None. The agent cannot start.")

    logging.info(f"CTX.Agent.Name: {ctx.job.agent_name}")
    logging.info(f"Agent Creation: Metadata obtained =  {metadata}")

    user_instructions = metadata.get("instructions")
    unique_code = metadata.get("project_id")

    avatar_name= metadata.get("bot_name")
    customer_name=metadata.get("customer_name")
    temperature = 0.7

    outbound_details= metadata.get("outbound_details")
    logging.info(f"outbound_details: {outbound_details}")

#####################TOOLS######################
    ###############Prebuilt Tools##########

    async def mute_unmute(context: RunContext):
        """
            Called when user asks you to mute or unmute yourself or wants you not to speak until the users says so.
            Toggle microphone mute status in Zoom meetings. Use this when:
            - User explicitly requests mute/unmute actions ("mute yourself", "unmute now")
            - User implies audio control needs ("stop speaking", "be quiet during this")
            - Temporary speech restrictions are needed ("don't speak until I say")
        """
        bot=ctx.room.local_participant
        await  bot.publish_dtmf(code=10, digit='*')
        await  bot.publish_dtmf(code=6, digit='6')

        return "ok"
    
    async def voicemail(context: RunContext):
        """
            Called when you are informed that the call is being forwarded to voicemail
            Hang up call if it is being forwarded to vaoicemail.
        """
        logging.info(f"Called end_call due to voicemail")
        room_name = ctx.room.name
        logging.info(f"Ending call by deleting room {room_name}")
        
        try:
            await delete_lk_room(room_name)
            logging.info(f"Successfully deleted room {room_name}")
            return None, "Call ended successfully."
            
        except Exception as e:
            logging.error(f"Error ending call: {e}")
            return None, f"Failed to end call: {e}"        

    if outbound_details.get("outbound_number") is not None:
        ob_call_id=outbound_details.get("outbound_call_id")
        ob_callee_number= outbound_details.get("outbound_number")
        ob_name= outbound_details.get("outbound_name")
        ob_call_context= outbound_details.get("outbound_call_context")

        tool= function_tool(
            voicemail,
            name= "voicemail",
            description= """
                Called when you are informed that the call is being forwarded to voicemail
                Hang up call if it is being forwarded to vaoicemail.
            """
        )

        logging.info("############### Outbound Details ###############")
        logging.info(f"ob_callee_number {ob_callee_number}")
        logging.info(f"ob_name {ob_name}")
        logging.info(f"ob_call_context {ob_call_context}")
        logging.info(f"###############################################")

    tools=[]


    tool=function_tool(
        check_delivery,
        name= function.get("function_name"),
        description=function.get("callable_description"),
    )
    tools.append(tool)



    if outbound_details.get("meeting_id") is not None:
        tool= function_tool(
            mute_unmute,
            name= "mute_unmute",
            description= """
                Called when user asks you to mute or unmute yourself or wants you not to speak until the users says so.
                Toggle microphone mute status in Zoom meetings. Use this when:
                - User explicitly requests mute/unmute actions ("mute yourself", "unmute now")
                - User implies audio control needs ("stop speaking", "be quiet during this")
                - Temporary speech restrictions are needed ("don't speak until I say")
            """
        )
        tools.append(tool)

        session = AgentSession(
            vad=ctx.proc.userdata["vad"],
            stt= openai.STT(model="gpt-4o-mini-transcribe"),
            llm=openai.realtime.RealtimeModel(
                api_key=os.getenv("OPENAI_API_KEY"),
                model= "gpt-4o-mini-realtime-preview",
                voice= "coral",
                temperature=temperature,
                input_audio_noise_reduction= InputAudioNoiseReduction(type="far_field")  
            ),
            tts=openai.TTS(model= "gpt-4o-mini-tts", voice= "coral", speed=1, instructions= "be expressive"),
            turn_detection=EnglishModel(),
            allow_interruptions=True,
        )

    agent = MyAgent(user_instructions=user_instructions, tools=tools)


    usage_collector = metrics.UsageCollector()
    @session.on("metrics_collected")
    def _on_metrics_collected(ev: MetricsCollectedEvent):
        metrics.log_metrics(ev.metrics)

    async def log_usage():
        summary = usage_collector.get_summary()
        logging.info(f"Usage: {summary}")

    def write_transcript():
        transcript_dir = Path.cwd() / "temp"
        transcript_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        uniq      = uuid.uuid4().hex[:4]
        filename  = transcript_dir / f"transcript_{ctx.room.name}_{timestamp}_{uniq}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(session.history.to_dict(), f, indent=2)
        logging.info(f"Transcript saved to {filename}")
        return filename

    await ctx.wait_for_participant()

    start_time_utc = datetime.now(timezone.utc)

    @ctx.room.on("participant_disconnected")
    def on_participant_disconnected():
        summary = usage_collector.get_summary()
        summary_dict = asdict(summary)
        logging.info(f"usage: {summary_dict}")
        filename= write_transcript()
        
        running_tasks = asyncio.all_tasks()
        logging.info(f"Currently Running Tasks = {len(running_tasks)}")

        agent_tasks = []
        for task in running_tasks:
            if task is not asyncio.current_task() and any(name in str(task.get_coro()).lower() for name in ["agent", "stt", "openai", "realtime"])  :
                
                logging.info(f"Cancelling Task: {str(task.get_coro())} -> Status: {task._state}")
                agent_tasks.append(task)
        
        logging.info(f"Cancelling {len(agent_tasks)} agent-related tasks")
        for task in agent_tasks:
            task.cancel()

    ctx.add_shutdown_callback(log_usage)
    await session.start(
        agent=agent,
        room=ctx.room,
        room_output_options=RoomOutputOptions(transcription_enabled=True),
        room_input_options=RoomInputOptions(
            noise_cancellation=noise_cancellation.BVC()
        ),       
    )

if __name__ == "__main__":

    agent_name = os.environ["AGENT_NAME"]
    logging.info(f"Agent_Name in creation: {agent_name}, Type: {type(agent_name)}")
    opts = WorkerOptions(
        entrypoint_fnc=entrypoint,
        prewarm_fnc=prewarm_process,
        worker_type=WorkerType.ROOM,
        agent_name=agent_name
    )    
    
    cli.run_app(opts)
