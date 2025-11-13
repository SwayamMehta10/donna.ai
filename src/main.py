"""
Context Fetcher Server - Fetches emails/calendar and initiates calls
Port: 8000
"""

import asyncio
import os
import sys
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import aiohttp
import json

# Fix Unicode encoding for Windows console
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

dotenv_path = Path(__file__).resolve().parent.parent / '.env'
load_dotenv(dotenv_path=str(dotenv_path), override=True)

# Add current directory to Python path to handle relative imports
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from llm.agent_runner import AIVoiceAgent

# Initialize FastAPI app
app = FastAPI(title="Donna.ai - Context Fetcher")

# Set up CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class CallRequest(BaseModel):
    unique_code: str
    name: str
    phone: str
    email: str


def format_summary_for_api(summary):
    """
    Format the email and calendar summary data for the API call_context parameter.
    Creates a structured conversational context for the calling agent.
    
    NEW APPROACH: No Gemini analysis, just list emails in batches of 5
    """
    sections = []
    
    # 1. GREETING - Ultra brief
    sections.append("Donna here.")
    
    # 2. CALENDAR - Ultra compact
    today_events = summary.get("today_events", 0)
    
    calendar_text = []
    if today_events > 0:
        calendar_text.append(f"{today_events} events today.")
        events_details = summary.get("today_events_details", [])
        for event in events_details[:1]:  # Max 1 event
            title = event.get("title", "Event")
            time = event.get("time", "")
            calendar_text.append(f"{title} at {time}")
    else:
        calendar_text.append("No events today.")
    
    sections.append("\n".join(calendar_text))
    
    # 3. EMAIL SECTION - ONLY MENTION COUNT, NOT DETAILS (to reduce tokens)
    email_count = summary.get("total_emails", 0)
    
    if email_count > 0:
        sections.append(f"{email_count} emails available.")
    else:
        sections.append("No emails.")

    return "\n\n".join(sections)


async def call_telephony_api(call_context, unique_code, bot_name, name, callee_number):
    """
    Call the telephony server API at port 8021
    """
    telephony_url = "http://localhost:8021/get_room_token"
    
    request_body = {
        "unique_code": str(unique_code),
        "bot_name": str(bot_name),
        "name": str(name),
        "call_context": str(call_context),
        "callee_number": str(callee_number),
        "call_id": 0
    }
    
    try:
        # Prepare call_context for JSON
        request_body["call_context"] = json.dumps(request_body["call_context"])[1:-1]
        json_str = json.dumps(request_body)
        
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(telephony_url, data=json_str, headers=headers, timeout=aiohttp.ClientTimeout(total=45)) as response:
                try:
                    result = await response.json()
                    print(f"Telephony API Response: {result}")
                    return result
                except aiohttp.ContentTypeError:
                    text = await response.text()
                    print(f"Invalid JSON response: {text}")
                    return {"status": 0, "message": f"Error: Invalid response format: {text[:100]}..."}
    except Exception as e:
        print(f"Error calling telephony API: {e}")
        return {"status": 0, "message": f"Error: {str(e)}"}


@app.post("/fetch-and-call")
async def fetch_and_call(call_request: CallRequest):
    """
    Main endpoint - fetches email/calendar context and initiates call
    """
    print("\n" + "="*60)
    print("FETCH-AND-CALL ENDPOINT CALLED")
    print("="*60)
    print(f"User: {call_request.name} ({call_request.email})")
    print(f"Phone: {call_request.phone}")
    print(f"Unique Code: {call_request.unique_code}")
    
    try:
        # Initialize the agent
        print("\n📧 Initializing Email and Calendar Agent...")
        agent = AIVoiceAgent()
        
        # Fetch and analyze data
        print("📊 Fetching email and calendar data...")
        await agent.start()
        
        # Get summary and format it
        summary = agent.state.get("summary", {})
        formatted_summary = format_summary_for_api(summary)
        
        print("\n✅ Data fetched successfully!")
        print(f"  Total Emails: {summary.get('total_emails', 0)}")
        print(f"  Total Calendar Events: {summary.get('total_calendar_events', 0)}")
        print(f"  Today's Events: {summary.get('today_events', 0)}")
        
        # Check if there's a reservation text in the state
        reservation_text = agent.state.get("reservation_text", "")
        
        if reservation_text:
            print("\n📝 Using reservation context")
            call_context = reservation_text
        else:
            print("\n📝 Using email/calendar summary context")
            call_context = formatted_summary
        
        # Call telephony API
        print("\n📞 Calling telephony server to initiate call...")
        response = await call_telephony_api(
            call_context=call_context,
            unique_code=call_request.unique_code,
            bot_name="Donna",
            name=call_request.name,
            callee_number=call_request.phone
        )
        
        # Stop the agent
        await agent.stop()
        
        if response.get("status") == 1:
            print("✅ Call initiated successfully!")
            return {
                "status": "success",
                "message": "Call initiated successfully",
                "telephony_response": response
            }
        else:
            print(f"❌ Call initiation failed: {response.get('message')}")
            raise HTTPException(status_code=500, detail=response.get("message", "Unknown error"))
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "context_fetcher"}


# Run the application
if __name__ == "__main__":
    import uvicorn
    print("Starting Context Fetcher Server on port 8000...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
