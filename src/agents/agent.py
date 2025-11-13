from __future__ import annotations
import requests
from pydantic import BaseModel
import os
import sys
import logging
from dotenv import load_dotenv
import json
import time
import asyncio
from datetime import datetime, timezone
from pathlib import Path
import uuid
from dataclasses import asdict

# Add parent directory to path so we can import src modules
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from livekit import api
from livekit.agents import cli, WorkerOptions, WorkerType, AutoSubscribe, JobContext, metrics, JobProcess
from livekit.agents.metrics import AgentMetrics, UsageCollector
from livekit.plugins import silero, turn_detector, groq, noise_cancellation
from livekit.agents import ChatContext, ChatMessage, StopResponse
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

from src.agents.functions import fetch_emails, draft_reply, draft_new_email, create_calendar_event, view_calendar
from livekit.agents import metrics, MetricsCollectedEvent

from livekit.agents.llm import function_tool
from livekit.agents.voice import MetricsCollectedEvent
from livekit.plugins import groq, silero, cartesia

# local import
from src.utils.mylogger import logging
from src.telephony.room_management import delete_lk_room
from src.agents.custom_agent import MyAgent
load_dotenv()


def prewarm_process(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load(min_silence_duration=2)  # Increased from 0.3 to reduce interruptions

# Entrypoint for agent worker
async def entrypoint(ctx: JobContext):
    """Entry point for the agent."""
    print("\n" + "="*60)
    print("AGENT ENTRYPOINT CALLED")
    print("="*60)
    print(f"Room Name: {ctx.room.name}")
    print(f"Agent Name: {ctx.job.agent_name}")
    print(f"Participants in room: {len(ctx.room.remote_participants)}")
    
    logging.info("=== AGENT ENTRYPOINT CALLED ===")
    logging.info(f"Room Name: {ctx.room.name}")
    logging.info(f"Agent Name: {ctx.job.agent_name}")
    logging.info(f"Participants in room: {len(ctx.room.remote_participants)}")

    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)  
    print("Connected to LiveKit room")
    logging.info("Connected to LiveKit room")

    metadata= json.loads(ctx.job.metadata)
    if ctx.room is None:
        print("ERROR: ctx.room is None. The agent cannot start.")
        logging.error("ERROR: ctx.room is None. The agent cannot start.")
        return

    print(f"Metadata keys: {list(metadata.keys())}")
    print("STARTING AGENT SETUP...")
    logging.info(f"Metadata: {metadata}")
    logging.info("=== STARTING AGENT SETUP ===")

    user_instructions = metadata.get("instructions")
    unique_code = metadata.get("project_id")

    avatar_name= metadata.get("bot_name")
    customer_name=metadata.get("customer_name")
    temperature = 0.7

    outbound_details= metadata.get("outbound_details")
    outbound_call_context = outbound_details.get("outbound_call_context")
    if outbound_call_context is not None:
        user_instructions += f" {outbound_call_context}. So talk to the user accordingly and do what is needed."
    logging.info(f"User Instructions: {user_instructions}")
    logging.info(f"outbound_details: {outbound_details}")

#####################TOOLS######################
    ###############Prebuilt Tools##########

    async def mute_unmute():
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
    
    async def voicemail(message: str = "Call forwarded to voicemail"):
        """
            Called when you are informed that the call is being forwarded to voicemail
            Hang up call if it is being forwarded to voicemail.
            
            Args:
                message: Optional message about the voicemail (default provided)
        """
        logging.info(f"Called end_call due to voicemail")
        room_name = ctx.room.name
        logging.info(f"Ending call by deleting room {room_name}")

        try:
            await delete_lk_room(room_name)
            logging.info(f"Successfully deleted room {room_name}")
            return "Call ended successfully."

        except Exception as e:
            logging.error(f"Error ending call: {e}")
            return f"Failed to end call: {e}"

    async def end_call(reason: str = "User requested to end the call"):
        """
            Called when the user wants to end the conversation.
            Use this when user says goodbye, thanks, that's all, or indicates they're done.
            
            Args:
                reason: Brief reason for ending the call (optional)
        """
        logging.info(f"User requested to end call: {reason}")
        room_name = ctx.room.name
        logging.info(f"Ending call by deleting room {room_name}")

        try:
            await delete_lk_room(room_name)
            logging.info(f"Successfully deleted room {room_name}")
            return "Goodbye! Have a great day."

        except Exception as e:
            logging.error(f"Error ending call: {e}")
            return f"Goodbye! Failed to end call: {e}"

    # Initialize tools list FIRST
    tools=[]

    if outbound_details.get("outbound_number") is not None:
        ob_call_id=outbound_details.get("outbound_call_id")
        ob_callee_number= outbound_details.get("outbound_number")
        ob_name= outbound_details.get("outbound_name")
        ob_call_context= outbound_details.get("outbound_call_context")

        # Add voicemail tool
        voicemail_tool = function_tool(
            voicemail,
            name="voicemail",
            description="Called when you are informed that the call is being forwarded to voicemail. Hang up the call."
        )
        tools.append(voicemail_tool)

        # Add fetch_emails tool - now enabled for on-demand use
        fetch_emails_tool = function_tool(
            fetch_emails,
            name="fetch_emails",
            description="""Fetch and display emails in batches of 5 when user requests them.
            
            WHEN TO USE:
            - User asks to check/read/show emails
            - User says "what emails do I have?" or "show me my emails"
            - User wants to see email details
            
            Returns emails in compact format (FROM + SUBJECT only) in batches of 5.
            After showing each batch, ask: "Would you like to respond to any of these, or see the next batch?"
            
            DO NOT call this automatically - only when user specifically requests emails."""
        )
        tools.append(fetch_emails_tool)
        
        # Add draft_reply tool
        draft_reply_tool = function_tool(
            draft_reply,
            name="draft_reply",
            description="""Create a professional draft reply using Gemini AI.
            
            WHEN TO USE:
            - User wants to reply to an existing email
            - User says "reply to [sender]" or "respond to that email"
            
            PARAMETERS:
            - email_identifier: Can be sender's email, name, or email ID
              Examples: "john@company.com", "John Smith", "19a6b5831a3b8e73"
            - reply_content: User's CASUAL intent (Gemini will make it professional)
              Example: "tell him I'll be there and bring the reports"
              
            IMPORTANT: 
            - Pass user's casual intent directly to Gemini
            - Gemini transforms it into professional business email
            - Do NOT try to formalize the content yourself
            
            EXAMPLES:
            - User: "Reply to John and tell him I'll send it tomorrow"
              → draft_reply(email_identifier="John", reply_content="tell him I'll send it tomorrow")
            - User: "Tell Sarah yes I can make the meeting"
              → draft_reply(email_identifier="Sarah", reply_content="yes I can make the meeting")"""
        )
        tools.append(draft_reply_tool)
        
        # Add draft_new_email tool
        draft_new_email_tool = function_tool(
            draft_new_email,
            name="draft_new_email",
            description="""Create a professional new email using Gemini AI ONLY after gathering ALL required information.
            
            CRITICAL: DO NOT call this function until you have BOTH recipient email AND email content from the user.
            
            WHEN TO USE:
            - User wants to compose/write/send a new email
            - User says "email [person]" or "send a message to [person]"
            
            REQUIRED INFORMATION - MUST ASK if not provided:
            1. to: Recipient's valid email address (must be name@domain.com format)
               - If user says "draft an email" or gives just a name, ASK: "Who should I send this to? I need their email address."
               - Do NOT accept invalid emails like "john.doe@example.com" - ask for real email
            2. subject: Email subject line
               - If not clear, ASK: "What should the subject line be?"
            3. body: User's CASUAL intent (Gemini will make it professional)
               - If user just says "email John", ASK: "What would you like to say to them?"
            
            OPTIONAL:
            - cc: CC recipients (comma-separated)
            
            CONVERSATION FLOW EXAMPLE:
            User: "Draft a new email"
            Agent: "Who should I send this to? I need their email address."
            User: "john.smith@company.com"
            Agent: "What should the subject line be?"
            User: "Project update"
            Agent: "What would you like to say to John?"
            User: "Ask about the budget status"
            Agent: [NOW calls draft_new_email with proper parameters]
            
            DO NOT make assumptions about recipients or content - always gather the required information first!"""
        )
        tools.append(draft_new_email_tool)
        
        # Add create_calendar_event tool
        create_calendar_event_tool = function_tool(
            create_calendar_event,
            name="create_calendar_event",
            description="""Create a new Google Calendar event ONLY after gathering ALL required information.
            
            CRITICAL: DO NOT call this function until you have BOTH title AND start_time from the user.
            
            WHEN TO USE:
            - User wants to schedule/create a meeting, appointment, or reminder
            - User says "schedule", "create event", "add to calendar", "remind me", "book"
            
            REQUIRED INFORMATION - MUST ASK if not provided:
            1. title: What is the event? (e.g., "Team meeting", "Doctor appointment")
               - If user just says "create an event", ASK: "What would you like to schedule?"
            2. start_time: When does it start? Accept natural language like:
               - "tomorrow at 2pm", "next Monday 10am", "December 15 at 3:30pm"
               - If not provided, ASK: "When should this be scheduled?"
            
            OPTIONAL INFORMATION:
            - duration_minutes: How long? (default: 60 minutes if not specified)
            - description: Any notes or details?
            - attendees: Who should attend? (comma-separated emails)
            
            CONVERSATION FLOW EXAMPLE:
            User: "Create a calendar event"
            Agent: "What would you like to schedule?"
            User: "Team meeting"
            Agent: "When should the team meeting be?"
            User: "Tomorrow at 10am"
            Agent: [NOW calls create_calendar_event with title="Team meeting", start_time="tomorrow at 10am"]
            
            DO NOT make assumptions - always gather the required information first!"""
        )
        tools.append(create_calendar_event_tool)
        
        # Add view_calendar tool
        view_calendar_tool = function_tool(
            view_calendar,
            name="view_calendar",
            description="View upcoming calendar events. Use when user asks about their schedule, upcoming meetings, or what's on their calendar."
        )
        tools.append(view_calendar_tool)

        # Add end_call tool
        end_call_tool = function_tool(
            end_call,
            name="end_call",
            description="End the conversation when user says goodbye, thanks, that's all I need, or indicates they want to end the call."
        )
        tools.append(end_call_tool)

        logging.info("############### Outbound Details ###############")
        logging.info(f"ob_callee_number {ob_callee_number}")
        logging.info(f"ob_name {ob_name}")
        logging.info(f"ob_call_context {ob_call_context}")
        logging.info(f"###############################################")

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
        stt=groq.STT(model="whisper-large-v3"),  # Add STT for speech recognition
        tts=cartesia.TTS(
            model="sonic-2-2025-03-07",  # Latest Cartesia model with speed control support
            voice="79a125e8-cd45-4c13-8a67-188112f4dd22",  # British Lady (female voice)
            speed=0.5,  # Slower speaking pace (0.8 = 80% speed)
            api_version="2024-11-13",  # Required API version for speed control
        ),
        llm=groq.LLM(
            api_key=os.getenv("GROQ_API_KEY"),
            model="meta-llama/llama-4-scout-17b-16e-instruct",  # Highest free TPM: 30K tokens/min
            temperature=temperature,
        ),
        # turn_detection=EnglishModel(),
        )

    # For outbound calls, agent should greet first
    is_outbound = outbound_details.get("outbound_number") is not None
    
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

    print("Waiting for participant to join...")
    logging.info("Waiting for participant to join...")
    await ctx.wait_for_participant()
    print("Participant joined! Starting session...")
    logging.info("Participant joined! Starting session...")

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
    
    # Start the session - session.start() doesn't return a handle, it returns None
    print("Starting agent session...")
    logging.info("Starting agent session...")
    await session.start(
        agent=agent,
        room=ctx.room,
        room_output_options=RoomOutputOptions(transcription_enabled=True),
        room_input_options=RoomInputOptions(
            noise_cancellation=noise_cancellation.BVC()
        )
    )
    print("Agent session started successfully!")
    logging.info("Agent session started successfully!")
    
    # For outbound calls, make agent speak first
    if is_outbound:
        print("This is an outbound call - agent will speak first")
        logging.info("This is an outbound call - agent will speak first")
        await session.say(
            "Good morning! This is Donna, your personal assistant. I can help you check your emails, draft replies, schedule calendar events, and manage your day. What would you like to know?",
            allow_interruptions=True
        )
        print("Agent spoke initial greeting")
        logging.info("Agent spoke initial greeting")
    else:
        print("This is an inbound call - waiting for user to speak first")
        logging.info("This is an inbound call - waiting for user to speak first")

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
