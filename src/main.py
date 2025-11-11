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
    """
    sections = []
    
    # 1. GREETING & INTRODUCTION
    current_time = datetime.now()
    time_of_day = "morning" if current_time.hour < 12 else "afternoon" if current_time.hour < 18 else "evening"
    sections.append(f"Good {time_of_day}. It's Donna here, I'll give you an overview of the emails you have received in the past 24 hours and the events scheduled for today.")
    
    # 2. CALENDAR SECTION
    calendar_count = summary.get("total_calendar_events", 0)
    today_events = summary.get("today_events", 0)
    upcoming_events = len(summary.get("upcoming_events", []))
    
    calendar_text = []
    if today_events > 0:
        calendar_text.append(f"You have {today_events} {'event' if today_events == 1 else 'events'} scheduled today.")
        events_details = summary.get("today_events_details", [])
        if events_details:
            for event in events_details:
                title = event.get("title", "Untitled")
                time = event.get("time", "No time specified")
                location = event.get("location", "No location specified")
                attendees_count = event.get("attendees", "")
                
                event_details = f"'{title}' at {time}"
                if location and location.lower() != "no location specified":
                    event_details += f" in {location}"
                if attendees_count and str(attendees_count).isdigit():
                    event_details += f" with {attendees_count} {'person' if attendees_count == '1' else 'people'}"
                
                calendar_text.append(f"• {event_details}")
    else:
        calendar_text.append("You have no events scheduled for today.")
    
    if upcoming_events > 0:
        calendar_text.append(f"You also have {upcoming_events} upcoming {'event' if upcoming_events == 1 else 'events'} in the next few days.")
    
    sections.append("SCHEDULE SUMMARY:\n" + "\n".join(calendar_text))
    
    # 3. EMAIL SECTION
    email_count = summary.get("total_emails", 0)
    important_emails = summary.get("important_emails", [])
    recent_emails = summary.get("email_subjects", [])

    email_text = []
    if email_count > 0:
        email_text.append(f"You have {email_count} {'email' if email_count == 1 else 'emails'} in your inbox.")

        if important_emails:
            email_text.append(f"\nTop {len(important_emails)} priority emails requiring your attention:")
            for idx, email in enumerate(important_emails[:5], 1):
                subject = email.get("subject", "No subject")
                sender = email.get("sender", "Unknown sender")
                urgency = email.get("urgency", "medium")
                importance = email.get("importance_score", 5)

                urgency_indicator = "🔴" if urgency == "critical" else "🟠" if urgency == "high" else "🟡" if urgency == "medium" else "🟢"
                email_text.append(f"{urgency_indicator} {idx}. From {sender}: \"{subject}\" (Priority: {importance}/10)")

                ai_summary = email.get("summary", "")
                if ai_summary and ai_summary != subject:
                    email_text.append(f"   Summary: {ai_summary}")

                suggested_action = email.get("suggested_action", "")
                if suggested_action:
                    email_text.append(f"   Action needed: {suggested_action}")

        elif recent_emails:
            email_text.append("Recent emails include:")
            for email in recent_emails[:3]:
                subject = email.get("subject", "No subject")
                sender = email.get("sender", "Unknown sender")
                email_text.append(f"• From {sender}: \"{subject}\"")
    else:
        email_text.append("You have no new emails.")

    sections.append("EMAIL SUMMARY:\n" + "\n".join(email_text))

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
