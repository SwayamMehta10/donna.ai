"""
Gmail API integration module
Handles authentication and email fetching from Gmail API
"""

import os
import pickle
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import base64
import email
import logging

logger = logging.getLogger(__name__)

# Gmail API scopes - readonly for fetching, compose for drafting
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.compose'
]

class GmailAPI:
    """Gmail API client for fetching emails"""
    
    def __init__(self, credentials_path: str = None, token_path: str = None):
        self.credentials_path = credentials_path or os.getenv('GMAIL_CREDENTIALS_PATH', 'credentials/client_secret.json')
        self.token_path = token_path or os.getenv('GMAIL_TOKEN_PATH', 'credentials/gmail_token.json')
        self.service = None
        self._authenticate()
    
    def _authenticate(self):
        """Authenticate with Gmail API"""
        creds = None
        
        # Load existing token
        if os.path.exists(self.token_path):
            with open(self.token_path, 'r') as token:
                creds_data = json.load(token)
                creds = Credentials.from_authorized_user_info(creds_data, SCOPES)
        
        # If no valid credentials, go through OAuth flow
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception as e:
                    logger.error(f"Failed to refresh credentials: {e}")
                    creds = None
            
            if not creds:
                if not os.path.exists(self.credentials_path):
                    raise FileNotFoundError(f"Gmail credentials file not found: {self.credentials_path}")
                
                flow = InstalledAppFlow.from_client_secrets_file(self.credentials_path, SCOPES)
                creds = flow.run_local_server(port=0)
            
            # Save credentials for next run
            os.makedirs(os.path.dirname(self.token_path), exist_ok=True)
            with open(self.token_path, 'w') as token:
                token.write(creds.to_json())
        
        # Build service
        self.service = build('gmail', 'v1', credentials=creds)
        logger.info("Gmail API authenticated successfully")
    
    def fetch_recent_emails(self, since: datetime = None, max_results: int = 50) -> List[Dict[str, Any]]:
        """Fetch emails from the last 24 hours"""
        try:
            if since is None:
                # Default to last 24 hours
                since = datetime.now() - timedelta(hours=24)
            
            # Convert datetime to Gmail API format (YYYY/MM/DD)
            date_str = since.strftime('%Y/%m/%d')
            
            # Create query to get emails from the last 24 hours
            # Exclude spam and trash, focus on inbox
            query = f"after:{date_str} is:unread in:inbox -in:spam -in:trash"
            
            logger.info(f"Fetching emails since {since.strftime('%Y-%m-%d %H:%M:%S')}")
            
            # Get message IDs
            results = self.service.users().messages().list(
                userId='me',
                q=query,
                maxResults=max_results
            ).execute()
            
            messages = results.get('messages', [])
            emails = []
            
            for message in messages:
                try:
                    email_data = self._get_email_details(message['id'])
                    if email_data:
                        emails.append(email_data)
                except Exception as e:
                    logger.error(f"Error processing email {message['id']}: {e}")
                    continue
            
            logger.info(f"Fetched {len(emails)} emails since {since}")
            return emails
            
        except HttpError as error:
            logger.error(f"Gmail API error: {error}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error fetching emails: {e}")
            return []
    
    def _get_email_details(self, message_id: str) -> Optional[Dict[str, Any]]:
        """Get details for a specific email"""
        try:
            message = self.service.users().messages().get(
                userId='me',
                id=message_id,
                format='full'
            ).execute()
            
            payload = message['payload']
            headers = payload.get('headers', [])
            
            # Extract headers
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
            sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown')
            date_str = next((h['value'] for h in headers if h['name'] == 'Date'), '')
            
            # Parse date
            try:
                timestamp = email.utils.parsedate_to_datetime(date_str)
            except:
                timestamp = datetime.now()
            
            # Extract body
            body = self._extract_email_body(payload)
            
            return {
                'id': message_id,
                'subject': subject,
                'sender': sender,
                'timestamp': timestamp,
                'body': body,
                'labels': message.get('labelIds', [])
            }
            
        except Exception as e:
            logger.error(f"Error getting email details for {message_id}: {e}")
            return None
    
    def _extract_email_body(self, payload: Dict[str, Any]) -> str:
        """Extract email body from payload"""
        body = ""
        
        if 'parts' in payload:
            for part in payload['parts']:
                if part['mimeType'] == 'text/plain':
                    if 'data' in part['body']:
                        body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
                        break
                elif part['mimeType'] == 'multipart/alternative':
                    # Recursively extract from multipart
                    body = self._extract_email_body(part)
                    if body:
                        break
        else:
            if payload['mimeType'] == 'text/plain' and 'data' in payload['body']:
                body = base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8')
        
        return body.strip() if body else "No content"
    
    def create_draft_reply(self, email_id: str, reply_body: str) -> Optional[str]:
        """
        Create a draft reply to an existing email
        
        Args:
            email_id: ID of the email to reply to
            reply_body: Content of the reply
            
        Returns:
            Draft ID if successful, None otherwise
        """
        try:
            # Get original email to extract headers
            original = self.service.users().messages().get(
                userId='me',
                id=email_id,
                format='full'
            ).execute()
            
            headers = original['payload'].get('headers', [])
            to = next((h['value'] for h in headers if h['name'] == 'From'), None)
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), '')
            message_id = next((h['value'] for h in headers if h['name'] == 'Message-ID'), None)
            references = next((h['value'] for h in headers if h['name'] == 'References'), '')
            
            if not to:
                logger.error("Cannot reply: original email has no sender")
                return None
            
            # Add "Re: " to subject if not already present
            if not subject.startswith('Re: '):
                subject = f"Re: {subject}"
            
            # Build reply message
            message = email.message.EmailMessage()
            message['To'] = to
            message['Subject'] = subject
            message.set_content(reply_body)
            
            # Add threading headers for proper reply chain
            if message_id:
                message['In-Reply-To'] = message_id
                if references:
                    message['References'] = f"{references} {message_id}"
                else:
                    message['References'] = message_id
            
            # Create draft
            draft_body = {
                'message': {
                    'raw': base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8'),
                    'threadId': original.get('threadId')
                }
            }
            
            draft = self.service.users().drafts().create(
                userId='me',
                body=draft_body
            ).execute()
            
            draft_id = draft['id']
            logger.info(f"Created draft reply {draft_id} to email {email_id}")
            return draft_id
            
        except HttpError as error:
            logger.error(f"Gmail API error creating draft reply: {error}")
            return None
        except Exception as e:
            logger.error(f"Error creating draft reply: {e}")
            return None
    
    def create_draft_email(self, to: str, subject: str, body: str, cc: str = None) -> Optional[str]:
        """
        Create a new draft email
        
        Args:
            to: Recipient email address
            subject: Email subject
            body: Email content
            cc: Optional CC recipients (comma-separated)
            
        Returns:
            Draft ID if successful, None otherwise
        """
        try:
            # Build message
            message = email.message.EmailMessage()
            message['To'] = to
            message['Subject'] = subject
            if cc:
                message['Cc'] = cc
            message.set_content(body)
            
            # Create draft
            draft_body = {
                'message': {
                    'raw': base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
                }
            }
            
            draft = self.service.users().drafts().create(
                userId='me',
                body=draft_body
            ).execute()
            
            draft_id = draft['id']
            logger.info(f"Created draft email {draft_id} to {to}")
            return draft_id
            
        except HttpError as error:
            logger.error(f"Gmail API error creating draft: {error}")
            return None
        except Exception as e:
            logger.error(f"Error creating draft: {e}")
            return None

# Test function
def test_connection():
    """Test Gmail API connection"""
    try:
        gmail = GmailAPI()
        emails = gmail.fetch_recent_emails(max_results=1)
        print(f"Successfully connected! Found {len(emails)} recent emails.")
        return True
    except Exception as e:
        print(f"Connection failed: {e}")
        return False

if __name__ == "__main__":
    test_connection()