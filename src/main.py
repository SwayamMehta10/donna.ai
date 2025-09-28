"""
Simple Email and Calendar Reader    # Start web server in a separate thread for viewing results
    print("Starting web dashboard on http://localhost:8000")
    web_thread = threading.Thread(
        target=run_server,
        kwargs={"host": "localhost", "port": 8000},
        daemon=True
    )
    web_thread.start()
    
    print("\n📊 Dashboard available at: http://localhost:8000/dashboard")
    
    # Fetch emails and calendar data once
    print("\n🔄 Fetching emails and calendar events...")mmarizes emails and calendar events without continuous monitoring
"""

import asyncio
import os
import sys
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from llm.agent_runner import AIVoiceAgent
from api.web_interface import run_server
import threading

dotenv_path = Path(__file__).resolve().parent.parent / '.env'
load_dotenv(dotenv_path=str(dotenv_path), override=True)

# Add current directory to Python path to handle relative imports
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

def format_summary_for_api(summary):
    """
    Format the email and calendar summary data for the API call_context parameter.
    Creates a structured conversational context for the calling agent.
    
    Args:
        summary (dict): The summary dictionary from agent.state
        
    Returns:
        str: A well-formatted string that provides conversational context
    """
    # Create a structured text that's both informative and conversational
    sections = []
    
    # 1. GREETING & INTRODUCTION
    current_time = datetime.now()
    time_of_day = "morning" if current_time.hour < 12 else "afternoon" if current_time.hour < 18 else "evening"
    sections.append(f"Good {time_of_day}. I'm your personal assistant with updates on your emails and schedule.")
    
    # 2. CALENDAR SECTION - Start with most urgent/relevant info
    calendar_count = summary.get("total_calendar_events", 0)
    today_events = summary.get("today_events", 0)
    upcoming_events = len(summary.get("upcoming_events", []))
    
    # Calendar summary paragraph
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
    
    # 3. EMAIL SECTION - Focus on important/priority emails
    email_count = summary.get("total_emails", 0)
    important_emails = summary.get("important_emails", [])
    recent_emails = summary.get("email_subjects", [])
    
    # Email summary paragraph
    email_text = []
    if email_count > 0:
        email_text.append(f"You have {email_count} {'email' if email_count == 1 else 'emails'} in your inbox.")
        
        if important_emails:
            email_text.append(f"{len(important_emails)} {'email requires' if len(important_emails) == 1 else 'emails require'} your attention:")
            for email in important_emails:  
                subject = email.get("subject", "No subject")
                sender = email.get("sender", "Unknown sender")
                email_text.append(f"• From {sender}: \"{subject}\"")
        
        if recent_emails and not important_emails:
            email_text.append("Recent emails include:")
            for email in recent_emails[:3]:  # Show only 3 most recent if no important emails
                subject = email.get("subject", "No subject")
                sender = email.get("sender", "Unknown sender")
                email_text.append(f"• From {sender}: \"{subject}\"")
    else:
        email_text.append("You have no new emails.")
    
    sections.append("EMAIL SUMMARY:\n" + "\n".join(email_text))
    
    # 4. CONFLICTS & ACTION ITEMS
    conflicts = summary.get("conflicts", [])
    if conflicts:
        conflict_text = ["ATTENTION NEEDED:"]
        for conflict in conflicts:
            conflict_text.append(f"• {conflict.get('description', 'Schedule conflict')}")
        sections.append("\n".join(conflict_text))
    
    # Join all sections with double line breaks for readability
    return "\n\n".join(sections)

async def call_room_token_api(call_context, unique_code="user123", bot_name="AI Assistant", name="User", call_id=None, callee_number=None, meeting_id=None, meeting_password=None):
    """
    Call the /get_room_token API with the formatted summary data in call_context.
    
    Args:
        call_context (str): The JSON-formatted string containing the summary information
        unique_code (str): The unique code identifier for the user
        bot_name (str): The name of the bot
        name (str): The user's name
        call_id (int, optional): The call ID
        callee_number (str, optional): The callee number
        meeting_id (str, optional): The meeting ID
        meeting_password (str, optional): The meeting password
        
    Returns:
        dict: The API response
    """
    import aiohttp
    import json
    import logging
    
    # API endpoint
    api_url = "http://localhost:8020/get_room_token"
    
    # Prepare the request body
    request_body = {
        "unique_code": unique_code,
        "bot_name": bot_name,
        "name": name,
        "call_context": call_context
    }
    
    # Add optional parameters if provided
    if call_id is not None:
        request_body["call_id"] = call_id
    if callee_number is not None:
        request_body["callee_number"] = callee_number
    if meeting_id is not None:
        request_body["meeting_id"] = meeting_id
    if meeting_password is not None:
        request_body["meeting_password"] = meeting_password
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(api_url, json=request_body) as response:
                result = await response.json()
                logging.info(f"API Response: {result}")
                return result
    except Exception as e:
        logging.error(f"Error calling API: {e}")
        return {"status": 0, "message": f"Error: {str(e)}"}

async def main():
    """Main function to fetch emails and calendar events"""
    print("📧 Email and Calendar Summarizer")
    print("=" * 50)
   
    # Initialize the agent
    print("Initializing Email and Calendar Agent...")
    agent = AIVoiceAgent()
    
    # Start web server in a separate thread for monitoring
    print("Starting web dashboard on http://localhost:8000")
    web_thread = threading.Thread(
        target=run_server,
        kwargs={"host": "localhost", "port": 8000},
        daemon=True
    )
    web_thread.start()
    
    print("\n📊 Dashboard available at: http://localhost:8000/dashboard")
    print("🔗 API endpoints at: http://localhost:8000")
    
    # We'll fetch and analyze when the app starts, no need for an initial check
    print("\nPreparing to fetch and analyze data...")
    print("� This will create log files showing what data is fetched...")
    
    try:
        await agent.start()
        
        summary = agent.state.get("summary", {})
        formatted_summary = format_summary_for_api(summary)
        
        print("\n" + formatted_summary)
        
        # Print the summary
        print("\n✅ Processing completed!")
        print("\n📋 SUMMARY")
        print(f"  📧 Total Emails: {summary.get('total_emails', 0)}")
        print(f"  📅 Total Calendar Events: {summary.get('total_calendar_events', 0)}")
        print(f"  📆 Today's Events: {summary.get('today_events', 0)}")
        
        # Print today's events
        if summary.get('today_events', 0) > 0:
            print("\n📆 TODAY'S SCHEDULE:")
            for idx, event in enumerate(summary.get('today_events_details', []), 1):
                print(f"  {idx}. {event['title']} at {event['time']}")
                print(f"     Location: {event['location']}")
                print(f"     Attendees: {event['attendees']}")
        
        # Print email subjects
        if summary.get('total_emails', 0) > 0:
            print("\n📧 RECENT EMAILS:")
            for idx, email in enumerate(summary.get('email_subjects', []), 1):
                print(f"  {idx}. {email['subject']} (from: {email['sender']})")
        
        # Call the API with the formatted summary
        print("\n🔄 Calling /get_room_token API with summarized data...")
        
        # Using our plain text summary
        response = await call_room_token_api(
            call_context=formatted_summary,
            unique_code=os.getenv("UNIQUE_CODE", "user123"),
            bot_name=os.getenv("BOT_NAME", "Email & Calendar Assistant"),
            name=os.getenv("USER_NAME", "User"),
            # Optional: Add a dummy call_id if needed
            call_id=0
        )
        
        print(f"📞 API Response: {response}")
        
        print("\nThe web dashboard will remain available for viewing details.")
        
    except KeyboardInterrupt:
        print("\n🛑 Shutdown requested...")
        await agent.stop()
        print("✅ Agent stopped successfully")


if __name__ == "__main__":
    asyncio.run(main())