"""
Configuration example for the AI Voice Agent
Copy this to config/settings.py and customize as needed
"""

import os
from typing import Dict, Any

def load_settings() -> Dict[str, Any]:
    """Load configuration settings from environment variables"""
    
    return {
        # Gmail API settings
        'gmail_credentials_path': os.getenv('GMAIL_CREDENTIALS_PATH', 'credentials/gmail_credentials.json'),
        'gmail_token_path': os.getenv('GMAIL_TOKEN_PATH', 'credentials/gmail_token.json'),
        
        # Google Calendar API settings
        'calendar_credentials_path': os.getenv('CALENDAR_CREDENTIALS_PATH', 'credentials/calendar_credentials.json'),
        'calendar_token_path': os.getenv('CALENDAR_TOKEN_PATH', 'credentials/calendar_token.json'),
        
        # LLM settings (using free options)
        'llm_provider': os.getenv('LLM_PROVIDER', 'groq'),  # 'groq', 'ollama', 'openai-compatible'
        'llm_model': os.getenv('LLM_MODEL', 'llama-3.1-8b-instant'),  # For Groq
        'llm_api_url': os.getenv('LLM_API_URL', ''),  # Only needed for Ollama
        'llm_api_key': os.getenv('LLM_API_KEY', ''),  # Required for Groq
        
        # Voice/Phone settings
        'twilio_account_sid': os.getenv('TWILIO_ACCOUNT_SID'),
        'twilio_auth_token': os.getenv('TWILIO_AUTH_TOKEN'),
        'twilio_phone_number': os.getenv('TWILIO_PHONE_NUMBER'),
        'user_phone_number': os.getenv('USER_PHONE_NUMBER'),
        
        # Monitoring intervals (in seconds)
        'email_check_interval': int(os.getenv('EMAIL_CHECK_INTERVAL', '300')),  # 5 minutes
        'calendar_check_interval': int(os.getenv('CALENDAR_CHECK_INTERVAL', '900')),  # 15 minutes
        'user_response_timeout': int(os.getenv('USER_RESPONSE_TIMEOUT', '300')),  # 5 minutes
        
        # Analysis thresholds
        'importance_threshold': float(os.getenv('IMPORTANCE_THRESHOLD', '0.7')),
        'conflict_severity_threshold': os.getenv('CONFLICT_SEVERITY_THRESHOLD', 'medium'),
        
        # Web interface settings
        'web_host': os.getenv('WEB_HOST', '0.0.0.0'),
        'web_port': int(os.getenv('WEB_PORT', '8000')),
        
        # Debug settings
        'debug_mode': os.getenv('DEBUG_MODE', 'false').lower() == 'true',
        'log_level': os.getenv('LOG_LEVEL', 'INFO'),
        'log_file': os.getenv('LOG_FILE', 'agent.log'),
    }

# Example .env file content
ENV_EXAMPLE = """
# Gmail API credentials
GMAIL_CREDENTIALS_PATH=credentials/gmail_credentials.json
GMAIL_TOKEN_PATH=credentials/gmail_token.json

# Google Calendar API credentials  
CALENDAR_CREDENTIALS_PATH=credentials/calendar_credentials.json
CALENDAR_TOKEN_PATH=credentials/calendar_token.json

# LLM Configuration (choose one)
# Option 1: Ollama (free, runs locally)
LLM_PROVIDER=ollama
LLM_MODEL=llama3.2
LLM_API_URL=http://localhost:11434

# Option 2: Groq (free tier)
# LLM_PROVIDER=groq
# LLM_API_KEY=your_groq_api_key_here
# LLM_MODEL=llama3-8b-8192

# Option 3: OpenAI-compatible API
# LLM_PROVIDER=openai-compatible
# LLM_API_URL=https://api.your-provider.com/v1
# LLM_API_KEY=your_api_key_here

# Twilio for voice calls
TWILIO_ACCOUNT_SID=your_twilio_sid
TWILIO_AUTH_TOKEN=your_twilio_token
TWILIO_PHONE_NUMBER=+1234567890
USER_PHONE_NUMBER=+0987654321

# Monitoring settings
EMAIL_CHECK_INTERVAL=300
CALENDAR_CHECK_INTERVAL=900
USER_RESPONSE_TIMEOUT=300

# Analysis settings
IMPORTANCE_THRESHOLD=0.7
CONFLICT_SEVERITY_THRESHOLD=medium

# Web interface
WEB_HOST=0.0.0.0
WEB_PORT=8000

# Debug settings
DEBUG_MODE=true
LOG_LEVEL=INFO
LOG_FILE=agent.log
"""

def create_env_file():
    """Create example .env file"""
    with open('.env.example', 'w') as f:
        f.write(ENV_EXAMPLE.strip())
    print("Created .env.example file. Copy it to .env and customize the values.")

if __name__ == "__main__":
    create_env_file()