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
try:
    from dotenv import load_dotenv
    # Try to load environment variables from .env file
    dotenv_path = Path(__file__).resolve().parent.parent / '.env'
    if dotenv_path.exists():
        load_dotenv(dotenv_path=str(dotenv_path), override=True)
        print("✅ Loaded environment variables from .env file")
except ImportError:
    print("⚠️ dotenv package not installed, using default environment variables")

# Add current directory to Python path to handle relative imports
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

async def main():
    """Main function to fetch emails and calendar events"""
    print("📧 Email and Calendar Summarizer")
    print("=" * 50)
    
    # Import after setting environment variables
    from llm.agent_runner import AIVoiceAgent
    from api.web_interface import run_server
    import threading
    
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
        
        # Print the summary
        summary = agent.state.get("summary", {})
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
        
        print("\nThe web dashboard will remain available for viewing details.")
        
    except KeyboardInterrupt:
        print("\n🛑 Shutdown requested...")
        await agent.stop()
        print("✅ Agent stopped successfully")

def run_app():
    """Wrapper to run the async main function"""
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")

if __name__ == "__main__":
    run_app()