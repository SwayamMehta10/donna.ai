import os.path
import logging
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/calendar'

]

def authenticate_gmail():
    """Authenticate and return the Gmail service."""
    creds = None
    # Load existing token
    if os.path.exists('token.json'):
        logger.debug("Found token.json, loading credentials...")
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    
    # If no valid creds, authenticate
    if not creds or not creds.valid:
        logger.debug("No valid credentials found, initiating authentication...")
        if creds and creds.expired and creds.refresh_token:
            logger.debug("Refreshing expired credentials...")
            creds.refresh(Request())
        else:
            logger.debug("Starting new authentication flow...")
            flow = InstalledAppFlow.from_client_secrets_file(os.path.join(os.path.dirname(__file__), 'client_secret.json'), SCOPES).run_local_server(port=5000)
            logger.debug(f"Client secrets file path: {os.path.join(os.path.dirname(__file__), 'client_secret.json')}")
            try:
                creds = flow.run_local_server(port=0)
                logger.debug("Authentication successful, saving token...")
                with open('token.json', 'w') as token:
                    token.write(creds.to_json())
            except Exception as e:
                logger.error(f"Authentication failed: {e}")
                raise
        
        logger.debug("Building Gmail service...")
    
    service = build('gmail', 'v1', credentials=creds)
    return service

def authenticate_google(service_name, version='v1'):
    """Authenticate and return a Google service (e.g., 'gmail' or 'calendar')."""
    creds = None
    # Load existing token
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    
    # If no valid creds, authenticate
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                os.path.join(os.path.dirname(__file__), 'client_secret.json'), SCOPES)
            creds = flow.run_local_server(port=0)
        
        # Save token for next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    
    # Build the service
    service = build(service_name, version, credentials=creds)
    return service


if __name__ == '__main__':
    try:
        service = authenticate_gmail()
        logger.debug("Authentication completed successfully.")
    except Exception as e:
        logger.error(f"Error in main: {e}")