"""
Startup script for running the AI Voice Agent with Groq
This script handles environment setup and starts the agent
"""

import os
import sys
import argparse
import asyncio
from dotenv import load_dotenv
import logging
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('agent.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def create_env_file():
    """Create a .env file if it doesn't exist"""
    if os.path.exists(".env"):
        return False
    
    # Create a basic .env file with Groq configuration
    with open(".env", "w") as f:
        f.write("""# AI Voice Agent - Environment Configuration
LLM_PROVIDER=groq
LLM_MODEL=llama-3.1-8b-instant
LLM_API_KEY=

# API Credential Paths
GMAIL_CREDENTIALS_PATH=credentials/gmail_credentials.json
GMAIL_TOKEN_PATH=credentials/gmail_token.json
CALENDAR_CREDENTIALS_PATH=credentials/calendar_credentials.json
CALENDAR_TOKEN_PATH=credentials/calendar_token.json
""")
    
    return True

def setup_groq():
    """Setup Groq configuration"""
    # Load environment variables
    load_dotenv()
    
    # Check if Groq API key is set
    api_key = os.getenv('LLM_API_KEY', '')
    if not api_key:
        api_key = input("Enter your Groq API key: ")
        # Update .env file with API key
        with open(".env", "r") as f:
            env_content = f.read()
        
        env_content = env_content.replace("LLM_API_KEY=", f"LLM_API_KEY={api_key}")
        
        with open(".env", "w") as f:
            f.write(env_content)
        
        # Set it for current session
        os.environ['LLM_API_KEY'] = api_key
    
    # Set LLM provider to Groq for current session
    os.environ['LLM_PROVIDER'] = 'groq'
    
    return api_key

async def test_groq_connection():
    """Test the Groq API connection"""
    # Import after setting environment variables
    from src.services.model import LLMService
    
    try:
        # Initialize LLM service with Groq configuration
        llm = LLMService()
        result = await llm._call_llm('Hello, please respond with a short greeting')
        print(f"✅ Groq test successful: {result}")
        return True
    except Exception as e:
        print(f"❌ Groq connection test failed: {e}")
        return False

def create_credential_dirs():
    """Create credentials directory if it doesn't exist"""
    os.makedirs('credentials', exist_ok=True)
    os.makedirs('logs', exist_ok=True)

def check_credentials():
    """Check if Google API credentials exist"""
    gmail_cred = os.path.exists('credentials/gmail_credentials.json')
    calendar_cred = os.path.exists('credentials/calendar_credentials.json')
    
    if not gmail_cred:
        print("❌ Gmail credentials not found at credentials/gmail_credentials.json")
        print("Please follow the setup guide to configure Google API credentials")
    
    if not calendar_cred:
        print("❌ Calendar credentials not found at credentials/calendar_credentials.json")
        print("Please follow the setup guide to configure Google API credentials")
    
    return gmail_cred and calendar_cred

async def main():
    """Main function for starting the AI Voice Agent"""
    parser = argparse.ArgumentParser(description="Start AI Voice Agent with Groq")
    parser.add_argument("--test", action="store_true", help="Test Groq connection only")
    parser.add_argument("--setup", action="store_true", help="Run setup only")
    args = parser.parse_args()
    
    print("=" * 60)
    print("🤖 AI Voice Agent - Groq Edition")
    print("=" * 60)
    
    # Create directories
    create_credential_dirs()
    
    # Create .env file if it doesn't exist
    if create_env_file():
        print("✅ Created new .env file")
    
    # Set up Groq
    api_key = setup_groq()
    if not api_key:
        print("❌ No Groq API key provided. Please edit .env file to add your API key")
        return
    
    if args.setup:
        print("✅ Setup completed. Edit .env file to customize settings.")
        return
    
    # Test Groq connection
    groq_working = await test_groq_connection()
    if not groq_working:
        print("❌ Unable to connect to Groq API. Please check your API key and internet connection.")
        return
    
    if args.test:
        print("✅ Groq API connection test completed successfully.")
        return
    
    # Check Google API credentials
    if not check_credentials():
        print("\nℹ️ Please configure Google API credentials before starting the agent.")
        print("   See SETUP_GUIDE.md for instructions.")
        return
    
    # All checks passed, start the agent
    print("\n✅ All checks passed! Starting AI Voice Agent...\n")
    
    # Import after setting environment variables
    from src.main import main as start_agent
    await start_agent()

if __name__ == "__main__":
    asyncio.run(main())