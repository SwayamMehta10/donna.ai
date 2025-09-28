"""
Example usage of the AI Voice Agent with LangGraph
This demonstrates how to start and use the agent for a hackathon
"""

import asyncio
import os
import sys
from datetime import datetime, timedelta
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

# Set environment variables for the example (only if not already set from .env)
os.environ.setdefault('GMAIL_CREDENTIALS_PATH', 'credentials/gmail_credentials.json')
os.environ.setdefault('CALENDAR_CREDENTIALS_PATH', 'credentials/calendar_credentials.json')
os.environ.setdefault('TWILIO_ACCOUNT_SID', 'your_twilio_sid_here')
os.environ.setdefault('TWILIO_AUTH_TOKEN', 'your_twilio_token_here')
os.environ.setdefault('USER_PHONE_NUMBER', '+1234567890')

# Ensure Groq is used as the LLM provider
os.environ.setdefault('LLM_PROVIDER', 'groq')
os.environ.setdefault('LLM_MODEL', 'llama-3.1-8b-instant')

async def main():
    """Main example function"""
    print("🤖 AI Voice Agent - LangGraph Implementation")
    print("=" * 50)
    
    # Import after setting environment variables
    from llm.agent_runner import AIVoiceAgent
    from api.web_interface import run_server
    import threading
    
    # Initialize the agent
    print("Initializing AI Voice Agent...")
    agent = AIVoiceAgent()
    
    # Print initial status
    status = agent.get_status()
    print(f"Agent Status: {status}")
    
    # Print helpful information
    print("\n📊 Data Logging Information:")
    print("  📧 Email logs will be saved to: logs/fetched_emails_*.json")
    print("  📅 Calendar logs will be saved to: logs/fetched_calendar_*.json")
    print("  🔍 Analysis logs will be saved to: logs/analysis_results_*.txt")
    print("  📄 Summary files will be saved to: logs/*_summary_*.txt")
    print("\n🔍 Check these log files to verify data fetching is working!")
    
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
    
    # Example: Force a check before starting monitoring
    print("\nPerforming initial check...")
    print("🔍 This will create log files showing what data is fetched...")
    try:
        result = await agent.force_check()
        print(f"✅ Initial check completed!")
        print(f"   📧 Check logs/fetched_emails_*.json for email data")
        print(f"   📅 Check logs/fetched_calendar_*.json for calendar data")
        print(f"   📊 Current status: {result}")
    except Exception as e:
        print(f"⚠️ Initial check failed: {e}")
        print("   📝 Check the log files to see if data was fetched before the error")
    
    # Start the main monitoring loop
    print("\n🚀 Starting continuous monitoring...")
    print("Press Ctrl+C to stop the agent")
    
    try:
        await agent.start()
    except KeyboardInterrupt:
        print("\n🛑 Shutdown requested...")
        await agent.stop()
        print("✅ Agent stopped successfully")

def run_example():
    """Wrapper to run the async example"""
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")

if __name__ == "__main__":
    run_example()