"""
Web Portal Server - Dashboard and Authentication
Port: 8020
"""
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
from starlette.middleware.sessions import SessionMiddleware
import os
import aiohttp

import logging
load_dotenv()
from src.utils.mylogger import logging

# Import auth router and user store
from src.api.auth import router as auth_router, get_current_user
from src.models.user_store import user_store

# Initialize FastAPI app
app = FastAPI(title="Donna.ai - Web Portal")

# Add session middleware for OAuth
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv('SECRET_KEY', 'your-secret-key-change-in-production')
)

# Set up CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="frontend"), name="static")

# Include auth router
app.include_router(auth_router)


# ============= REQUEST MODELS & HELPERS =============

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
        user_instructions= f"""
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
            request.call_context= request.reservation_context
            user_instructions = f"""You are making a outbound call to a store on behalf of {name} for"""
        outbound_details={
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
    
        print("Setting up Twilio outbound call...")
        logging.info("Setting up Twilio outbound call...")
        twilio_outbound_sip_details = await setup_twilio_outbound_call(twilio_number=twilio_number,
                                                                        twilio_sid=twilio_acc_sid,
                                                                        twilio_auth=twilio_auth_token,
                                                                        unique_code=unique_code,
                                                                        outbound_trunk_sid=None)
        
        print(f"Twilio outbound result: {twilio_outbound_sip_details}")
        logging.info(f"Twilio outbound result: {twilio_outbound_sip_details}")
        
        if not twilio_outbound_sip_details:
            print("Setup returned None - checking telephony.py exception")
            logging.error("Failed to setup Twilio outbound call - setup_twilio_outbound_call returned None")
            logging.error("This usually means there's an exception in the telephony.py function")
            raise HTTPException(status_code=500, detail="Failed to setup Twilio outbound call. Please check Twilio configuration and credentials.")
        
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

        # Start agent worker as background task
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
        logging.error(f"Exception Hit On API side: Error: {e}", exc_info=True)
        print(f"\nPROCESS_ITEM EXCEPTION: {e}")
        import traceback
        traceback.print_exc()
        response = {
                "status": 0,
                "message": f"Exception: {str(e)}",                
            }
        
        return response

# ============= WEB PORTAL ROUTES =============

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Serve login page"""
    user = await get_current_user(request)
    if user:
        return RedirectResponse(url="/dashboard")
    
    with open("frontend/login.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Serve dashboard page"""
    print("=== Dashboard route accessed ===")
    print(f"Session data: {request.session}")
    
    user = await get_current_user(request)
    print(f"User retrieved in dashboard: {bool(user)}")
    
    if not user:
        print("No user found, redirecting to login")
        return RedirectResponse(url="/")
    
    print(f"User {user.get('email')} accessing dashboard")
    with open("frontend/dashboard.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())


@app.post("/activate-agent")
async def activate_agent(request: Request, background_tasks: BackgroundTasks):
    """
    Activate Donna to call the user immediately with email and calendar summary
    Fetches context from src/main.py and initiates the call
    """
    print("\n" + "="*60)
    print("ACTIVATE-AGENT ENDPOINT CALLED")
    print("="*60)
    
    try:
        print("Step 1: Getting current user...")
        user = await get_current_user(request)
        print(f"User result: {user}")
        
        if not user:
            print("ERROR: No user found in session")
            raise HTTPException(status_code=401, detail="Not authenticated")
        
        print(f"Step 2: User authenticated - {user['email']}")
        
        # Check if user has phone number
        if not user.get('phone'):
            print(f"ERROR: User {user['email']} has no phone number")
            raise HTTPException(status_code=400, detail="Please add your phone number first")
        
        print(f"Step 3: User phone validated - {user['phone']}")
        
        # Step 4: Run src/main.py to fetch email and calendar context
        print("Step 4: Fetching email and calendar context from src/main.py...")
        import subprocess
        try:
            # Run src/main.py which will call the API on port 8020 (/get_room_token)
            # We'll pass the user's info through environment variables
            env = os.environ.copy()
            env["UNIQUE_CODE"] = user.get('user_id', 'user123')
            env["BOT_NAME"] = "Donna"
            env["USER_NAME"] = user.get('name', user.get('email').split('@')[0])
            env["USER_PHONE"] = user['phone']
            
            # Run src/main.py - it will fetch context and call back to /get_room_token
            proc = subprocess.Popen(
                [sys.executable, "src/main.py"],
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Wait for it to complete (should be quick as it just fetches and calls API)
            stdout, stderr = proc.communicate(timeout=30)
            
            print(f"src/main.py output:\n{stdout}")
            if stderr:
                print(f"src/main.py errors:\n{stderr}")
            
            if proc.returncode == 0:
                print(f"SUCCESS: Call initiated through src/main.py")
                return {
                    "message": "Agent activated! You should receive a call shortly.",
                    "phone": user['phone']
                }
            else:
                print(f"ERROR: src/main.py exited with code {proc.returncode}")
                raise HTTPException(
                    status_code=500, 
                    detail=f"Failed to activate agent: src/main.py error"
                )
                
        except subprocess.TimeoutExpired:
            print("ERROR: src/main.py timed out")
            proc.kill()
            raise HTTPException(status_code=500, detail="Timeout while fetching context")
        except Exception as e:
            print(f"ERROR running src/main.py: {e}")
            import traceback
            traceback.print_exc()
            raise HTTPException(status_code=500, detail=f"Failed to fetch context: {str(e)}")
            
    except HTTPException as http_ex:
        print(f"HTTPException caught: {http_ex.detail}")
        raise
    except Exception as e:
        print(f"UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


# Run the application 
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8020)