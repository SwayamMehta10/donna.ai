"""
Telephony Server - Handles phone call setup via Twilio/LiveKit
Port: 8021
"""
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
import os
import asyncio
import sys
import json
from typing import Optional

from src.telephony.room_management import manage_room
from src.telephony.telephony import (
    setup_twilio_inbound_call,
    setup_twilio_outbound_call,
    create_livekit_inbound_trunk,
    create_livekit_outbound_trunk,
    create_outbound_call
)

import logging
load_dotenv()
from src.utils.mylogger import logging

# Initialize FastAPI app
app = FastAPI(title="Donna.ai - Telephony Server")

# Set up CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Define request model
class ItemRequest(BaseModel):
    unique_code: str
    bot_name: str
    call_id:  Optional[int] = None
    callee_number: Optional[str] = None
    name: Optional[str] = None
    call_context: Optional[str] = None
    meeting_id: Optional[str] = None
    meeting_password: Optional[str] = None
    reservation_context: Optional[str] = None


async def start_agent(agent_name):
    """Start agent worker as background task"""
    try:
        print(f"Starting agent: {agent_name}")
        logging.info(f"Starting agent: {agent_name}")
        process = await asyncio.create_subprocess_exec(
            sys.executable,
            "src/agents/agent.py",
            "dev",
            "--no-watch",
            env={**os.environ, "AGENT_NAME": agent_name},
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=os.getcwd()
        )

        stdout, stderr = await process.communicate()
        stdout = stdout.decode().strip()
        stderr = stderr.decode().strip()

        if process.returncode != 0:
            logging.error(f"Agent creation failed: {stderr}")
        else:
            logging.info(f"Agent started successfully: {stdout}")
        
        return stdout

    except Exception as e:
        logging.error(f"Exception in start_agent: {e}", exc_info=True)


@app.post("/get_room_token")
async def process_item(request: ItemRequest, background_task: BackgroundTasks):
    """Main endpoint to set up telephony and initiate calls"""
    
    try:
        unique_code = request.unique_code
        bot_name = "Donna"
        name = request.name
        if not unique_code:
            raise HTTPException(status_code=400, detail="Unique code not received")
    except Exception as e:
        logging.error("Unique code Not received !!!!")
        response = {
            "status": 400,
            "message": "Unique code not received",                
        }        
        return response

    try:            
        user_instructions = f"""
        You are {bot_name}, personal assistant to {name}. Think Donna Paulsen from Suits - sharp, professional, efficient.

        ## CAPABILITIES - What You CAN Do:
        - Provide email and calendar summaries (already loaded in your context)
        - Fetch detailed email content when specifically requested (use fetch_emails tool)
        - Answer questions about your schedule and emails
        - End calls gracefully when asked (use end_call tool)

        ## LIMITATIONS - What You CANNOT Do:
        - Cannot send emails, draft responses, or reply to messages
        - Cannot create calendar events, set reminders, or update schedules
        - Cannot make calls, reschedule meetings, or notify people
        - Cannot access external websites or perform web searches

        ## Communication Style:
        - Direct and efficient - state information once, then pause for response
        - Sharp but warm - like Donna: confident, capable, with subtle wit
        - Crisp openings: "Morning. You've got 18 emails and a clear schedule."
        - Never repeat suggestions - if you've mentioned something once, wait for user direction
        - When conversation ends (goodbye, thanks, that's all), use the end_call tool immediately

        ## Response Pattern:
        1. State the facts briefly (1-2 sentences)
        2. Ask ONE clear question if needed
        3. STOP and wait for user response
        4. Never offer tasks you cannot perform (no "shall I draft a response" or "I'll update your calendar")

        ## Examples of GOOD Responses:
        - "You have 18 emails. The Neuralink intern match and Ford profile update stand out. What would you like to know?"
        - "Clear schedule today. Anything specific you need help with?"
        - "That email is from Ford's recruiting team about updating your profile. Want me to pull the full details?"

        ## Examples of BAD Responses (AVOID):
        - "Shall I draft a response?" (You can't send emails)
        - "I'll set a reminder for you." (You can't create reminders)
        - "Let me prioritize these..." then listing 10 suggestions (Too verbose, repetitive)
        - Asking the same question multiple times or offering repeated suggestions
        """

        if request.reservation_context is not None:
            request.call_context = request.reservation_context
            user_instructions = f"""You are making a outbound call to a store on behalf of {name} for"""
        
        outbound_details = {
            "outbound_call_id": request.call_id,
            "outbound_name": request.name,
            "outbound_number": request.callee_number,
            "outbound_call_context": request.call_context,
        }

        # Create one full user config
        full_user_config = {
            "instructions": user_instructions,
            "project_id": unique_code,
            "outbound_details": outbound_details,
            "room_name": None,
            "bot_name": bot_name,
            "name": name
        }
        logging.info(f"full_user_config: {full_user_config}")
        
        # Agent name - unique per user
        agent_name = f"{unique_code}_agent"

        # TELEPHONY SETUP
        twilio_number = os.getenv("TWILIO_PHONE_NUMBER")
        logging.info(f"User Twilio num: {twilio_number}")
        twilio_acc_sid = os.getenv("TWILIO_ACCOUNT_SID")
        twilio_auth_token = os.getenv("TWILIO_AUTH_TOKEN")

        if not all([twilio_number, twilio_acc_sid, twilio_auth_token]):
            raise HTTPException(status_code=500, detail="Twilio credentials not configured in environment")
            
        room_name = f"{unique_code}_inbound"
        full_user_config["room_name"] = room_name    
        twilio_inbound_sip_details = await setup_twilio_inbound_call(
            twilio_sid=twilio_acc_sid,
            twilio_auth=twilio_auth_token,
            twilio_number=twilio_number,
            unique_code=unique_code
        )
        
        livekit_inbound_sip_details = await create_livekit_inbound_trunk(
            twilio_number=twilio_number,
            unique_code=unique_code,
            agent_name=agent_name,
            metadata=json.dumps(full_user_config)
        )
    
        room_name = f"outbound_{unique_code}_{request.callee_number}"
        logging.info(f"Room Name for Outbound Call: {room_name}")
        full_user_config["room_name"] = room_name
        logging.info(f"full_user_config: {full_user_config}")
    
        print("Setting up Twilio outbound call...")
        logging.info("Setting up Twilio outbound call...")
        twilio_outbound_sip_details = await setup_twilio_outbound_call(
            twilio_number=twilio_number,
            twilio_sid=twilio_acc_sid,
            twilio_auth=twilio_auth_token,
            unique_code=unique_code,
            outbound_trunk_sid=None
        )
        
        print(f"Twilio outbound result: {twilio_outbound_sip_details}")
        logging.info(f"Twilio outbound result: {twilio_outbound_sip_details}")
        
        if not twilio_outbound_sip_details:
            print("Setup returned None - checking telephony.py exception")
            logging.error("Failed to setup Twilio outbound call")
            raise HTTPException(status_code=500, detail="Failed to setup Twilio outbound call")
        
        sip_username = twilio_outbound_sip_details.get("sip_username")
        sip_password = twilio_outbound_sip_details.get("sip_password")
        termination_uri = twilio_outbound_sip_details.get("termination_uri")
        
        livekit_outbound_sip_details = await create_livekit_outbound_trunk(
            twilio_number=twilio_number,
            sip_username=sip_username,
            sip_password=sip_password,
            unique_code=unique_code,
            termination_uri=termination_uri
        )
        
        outbound_sip_trunk_id = livekit_outbound_sip_details.get("outbound_sip_trunk_id")
        
        # WEB BASED SETUP - Create room and start agent FIRST
        room_token = await manage_room(full_user_config, agent_name)
        logging.info(f"Room Tokens: {room_token}")

        # Start agent worker as background task - agent needs to be ready before call
        background_task.add_task(start_agent, agent_name)
        
        # Wait a bit for agent to start and connect to room
        import asyncio
        await asyncio.sleep(2)  # Give agent 2 seconds to initialize
        
        # NOW initiate the outbound call - agent is ready and waiting
        outbound_call = await create_outbound_call(
            outbound_sip_trunk_id, 
            twilio_number,
            request.callee_number, 
            room_name, 
            request.meeting_id,
            request.meeting_password
        )

        response = {
            "status": 1,
            "message": "Room access token generated successfully!!!",
            "data": {
                "room_token": room_token
            }
        }
        
        return response
    
    except Exception as e:
        logging.error(f"Exception Hit On API side: Error: {e}", exc_info=True)
        print(f"\nPROCESS_ITEM EXCEPTION: {e}")
        import traceback
        traceback.print_exc()
        response = {
            "status": 0,
            "message": f"Exception: {str(e)}",                
        }
        
        return response


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "telephony_server"}


# Run the application 
if __name__ == "__main__":
    import uvicorn
    print("Starting Telephony Server on port 8021...")
    uvicorn.run(app, host="0.0.0.0", port=8021)
