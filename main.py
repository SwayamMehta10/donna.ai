from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
import os
import asyncio
import sys
import json
from typing import Optional

from room_management import manage_room
# from agent_creation import entrypoint
from telephony import (setup_twilio_inbound_call,
                             setup_twilio_outbound_call,
                             create_livekit_inbound_trunk,
                             create_livekit_outbound_trunk,
                             create_outbound_call) 

import logging
# Load environment variables
load_dotenv()
from mylogger import logging
# Initialize FastAPI app
app = FastAPI()

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


async def start_agent(agent_name):
    try:
        print(os.getenv("LIVEKIT_URL"))
        process = await asyncio.create_subprocess_exec(sys.executable,
                                                       "agent.py", 
                                                       "dev",
                                                       "--no-watch",
                                                       env={**os.environ,
                                                            "AGENT_NAME": agent_name},
                                                 stdout=asyncio.subprocess.PIPE,
                                                 stderr=asyncio.subprocess.PIPE,
                                                 cwd=os.getcwd())
        
        stdout, stderr = await process.communicate()

        stdout = stdout.decode().strip()
        stderr = stderr.decode().strip()

        if process.returncode != 0:
            logging.error(f"Agent creation failed: {stderr}")
            
        
        logging.info(f"Agent started successfully: {stdout}")
        return stdout  

    except Exception as e:
        logging.error(f"Exception in start_agent: {e}", exc_info=True)

# Defining a POST route
@app.post("/get_room_token")
async def process_item(request: ItemRequest, background_task: BackgroundTasks):

    try:
        unique_code = request.unique_code
        bot_name= "Donna"
        name=request.name
        if not unique_code:
            raise HTTPException(status_code=400, detail="Unique code not received")
    except Exception as e:
        logging.info("Unique code Not received !!!!")
        response = {
                "status": 400,
                "message": "Unique code not received",                
            }        
        return response

    try:            
        outbound_details={
            "outbound_call_id": request.call_id,
            "outbound_name": request.name,
            "outbound_number": request.callee_number,
            "outbound_call_context": request.call_context,
        }
        user_instructions= f"""
        You are {bot_name} a personal assistant of {name}. Your task is to assist the user with their queries and provide relevant information.

        Persona: 
        - Archetype: Elite executive assistant / chief-of-staff at a high-stakes law firm.
        - Core traits: Unflappable, surgical clarity, anticipates needs, rules the calendar, exquisitely discreet, playful wit used sparingly, impeccably polite but firm.
        - Anticipate the user's needs; suggest next best actions without waiting to be asked.

        Interaction Style Rubric (what “good” sounds like)

        - Openers: Crisp, situationally aware.

        - “Morning. You’ve got 14 minutes before your stand-up. Want me to push the vendor call to 2:30?”

        - Clarifying Qs: One breath, bullet-precise.

        - “Is the venue confirmed, 40 guests, and vegetarian catering?”

        - Decisions: Recommend, then act.

        - “Recommendation: move the debrief to Friday 11:30 to keep the morning clear for revisions. Shall I reschedule and notify?”

        “Done. Calendar updated, invites sent. I’ll ping you 10 minutes prior.”
        Your task is to assist the user with their queries and provide relevant information.
        """
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
        # Agent name
        agent_name = f"{unique_code}_agent"

        # TELEPHONY SETUP        

        twilio_number = "+17623375502"
        logging.info(f"User Twilio num: {twilio_number}")
        twilio_acc_sid = "AC18b9d297d6c1858eaef305607ecae287" 
        twilio_auth_token = "0644c5eae71262f68c51c9cca2f8c342"
            
        room_name= f"{unique_code}_inbound"
        full_user_config["room_name"] = room_name    
        twilio_inbound_sip_details = await setup_twilio_inbound_call(twilio_sid=twilio_acc_sid,
                                                                        twilio_auth=twilio_auth_token,
                                                                        twilio_number=twilio_number,
                                                                        unique_code=unique_code)
        
        livekit_inbound_sip_details = await create_livekit_inbound_trunk(twilio_number=twilio_number,
                                                                            unique_code=unique_code,
                                                                            agent_name=agent_name,
                                                                            metadata=json.dumps(full_user_config))
    
            
        room_name=f"outbound_{unique_code}_{request.callee_number}"
        logging.info(f"Room Name for Outbound Call: {room_name}")
        full_user_config["room_name"] = room_name
        logging.info(f"full_user_config: {full_user_config}")
    
        twilio_outbound_sip_details = await setup_twilio_outbound_call(twilio_number=twilio_number,
                                                                        twilio_sid=twilio_acc_sid,
                                                                        twilio_auth=twilio_auth_token,
                                                                        unique_code=unique_code,
                                                                        outbound_trunk_sid=None)
        
        sip_username = twilio_outbound_sip_details.get("sip_username")
        sip_password = twilio_outbound_sip_details.get("sip_password")
        termination_uri = twilio_outbound_sip_details.get("termination_uri")
        
        livekit_outbound_sip_details = await create_livekit_outbound_trunk(twilio_number=twilio_number,
                                                                            sip_username=sip_username,
                                                                            sip_password=sip_password,
                                                                            unique_code=unique_code,
                                                                            termination_uri=termination_uri)
        
        outbound_sip_trunk_id= livekit_outbound_sip_details.get("outbound_sip_trunk_id")
        outbound_call= await create_outbound_call(outbound_sip_trunk_id, twilio_number,request.callee_number, room_name, request.meeting_id,request.meeting_password)


        # WEB BASED SETUP
                
        room_token = await manage_room(full_user_config, agent_name)
        
        logging.info(f"Room Tokens: {room_token}")

        background_task.add_task(start_agent, agent_name)        

        response = {
                "status": 1,
                "message": "Room access token generated sucessfully!!!",
                "data": {
                    "room_token": room_token
                }
            }
        
        return response
    
    except Exception as e:
        logging.info(f"Exception Hit On API side: Error: {e}")
        response = {
                "status": 0,
                "message": "Exception Triggered during execution",                
            }
        
        return response

# Run the application 
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8020)


    





