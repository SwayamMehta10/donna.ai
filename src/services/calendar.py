"""
Google Calendar API integration module
Handles authentication and calendar event fetching
"""

import os
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import logging

logger = logging.getLogger(__name__)

# Calendar API scopes
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']

class CalendarAPI:
    """Google Calendar API client for fetching events"""
    
    def __init__(self, credentials_path: str = None, token_path: str = None):
        self.credentials_path = credentials_path or os.getenv('CALENDAR_CREDENTIALS_PATH', 'credentials/calendar_credentials.json')
        self.token_path = token_path or os.getenv('CALENDAR_TOKEN_PATH', 'credentials/calendar_token.json')
        self.service = None
        self._authenticate()
    
    def _authenticate(self):
        """Authenticate with Google Calendar API"""
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
                    raise FileNotFoundError(f"Calendar credentials file not found: {self.credentials_path}")
                
                flow = InstalledAppFlow.from_client_secrets_file(self.credentials_path, SCOPES)
                creds = flow.run_local_server(port=0)
            
            # Save credentials for next run
            os.makedirs(os.path.dirname(self.token_path), exist_ok=True)
            with open(self.token_path, 'w') as token:
                token.write(creds.to_json())
        
        # Build service
        self.service = build('calendar', 'v3', credentials=creds)
        logger.info("Calendar API authenticated successfully")
    
    def fetch_upcoming_events(self, end_date: datetime = None, max_results: int = 50) -> List[Dict[str, Any]]:
        """Fetch upcoming calendar events"""
        try:
            now = datetime.utcnow().isoformat() + 'Z'  # 'Z' indicates UTC time
            
            if end_date is None:
                end_date = datetime.utcnow() + timedelta(days=7)
            
            end_time = end_date.isoformat() + 'Z'
            
            events_result = self.service.events().list(
                calendarId='primary',
                timeMin=now,
                timeMax=end_time,
                maxResults=max_results,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            formatted_events = []
            
            for event in events:
                try:
                    event_data = self._format_event(event)
                    if event_data:
                        formatted_events.append(event_data)
                except Exception as e:
                    logger.error(f"Error processing event {event.get('id', 'unknown')}: {e}")
                    continue
            
            logger.info(f"Fetched {len(formatted_events)} calendar events")
            return formatted_events
            
        except HttpError as error:
            logger.error(f"Calendar API error: {error}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error fetching calendar events: {e}")
            return []
    
    def _format_event(self, event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Format a calendar event"""
        try:
            # Debug logging
            logger.debug(f"Raw event data: {event}")
            
            # Get start and end times
            start = event['start'].get('dateTime', event['start'].get('date'))
            end = event['end'].get('dateTime', event['end'].get('date'))
            
            # Parse datetime
            if 'T' in str(start):  # datetime format
                start_time = datetime.fromisoformat(str(start).replace('Z', '+00:00'))
                end_time = datetime.fromisoformat(str(end).replace('Z', '+00:00'))
            else:  # date format (all-day event)
                start_time = datetime.fromisoformat(str(start))
                end_time = datetime.fromisoformat(str(end))
            
            # Extract attendees
            attendees = []
            if 'attendees' in event and isinstance(event['attendees'], list):
                attendees = [
                    attendee.get('email', '')
                    for attendee in event['attendees']
                    if isinstance(attendee, dict) and attendee.get('email')
                ]
            
            formatted_event = {
                'id': event.get('id', ''),
                'title': event.get('summary', 'Untitled Event'),
                'description': event.get('description', '') if event.get('description') else '',
                'start_time': start_time,
                'end_time': end_time,
                'location': event.get('location', '') if event.get('location') else '',
                'attendees': attendees,
                'status': event.get('status', 'confirmed'),
                'creator': event.get('creator', {}).get('email', '') if isinstance(event.get('creator'), dict) else '',
                'html_link': event.get('htmlLink', '') if event.get('htmlLink') else ''
            }
            
            logger.debug(f"Formatted event: {formatted_event}")
            return formatted_event
            
        except Exception as e:
            logger.error(f"Error formatting event: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return None
    
    def create_event(self, event_data: Dict[str, Any]) -> Optional[str]:
        """Create a new calendar event"""
        try:
            event = {
                'summary': event_data.get('title', 'New Event'),
                'location': event_data.get('location', ''),
                'description': event_data.get('description', ''),
                'start': {
                    'dateTime': event_data['start_time'].isoformat(),
                    'timeZone': 'UTC',
                },
                'end': {
                    'dateTime': event_data['end_time'].isoformat(),
                    'timeZone': 'UTC',
                },
            }
            
            # Add attendees if provided
            if event_data.get('attendees'):
                event['attendees'] = [
                    {'email': email}
                    for email in event_data['attendees']
                ]
            
            created_event = self.service.events().insert(
                calendarId='primary',
                body=event,
                sendUpdates='all' if event_data.get('attendees') else 'none'
            ).execute()
            
            logger.info(f"Created event: {created_event['id']}")
            return created_event['id']
            
        except HttpError as error:
            logger.error(f"Error creating event: {error}")
            return None
    
    def update_event(self, event_id: str, updates: Dict[str, Any]) -> bool:
        """Update an existing calendar event"""
        try:
            # Get existing event
            event = self.service.events().get(
                calendarId='primary',
                eventId=event_id
            ).execute()
            
            # Apply updates
            if 'title' in updates:
                event['summary'] = updates['title']
            if 'start_time' in updates:
                event['start']['dateTime'] = updates['start_time'].isoformat()
            if 'end_time' in updates:
                event['end']['dateTime'] = updates['end_time'].isoformat()
            if 'location' in updates:
                event['location'] = updates['location']
            if 'description' in updates:
                event['description'] = updates['description']
            
            # Update the event
            updated_event = self.service.events().update(
                calendarId='primary',
                eventId=event_id,
                body=event,
                sendUpdates='all'
            ).execute()
            
            logger.info(f"Updated event: {event_id}")
            return True
            
        except HttpError as error:
            logger.error(f"Error updating event {event_id}: {error}")
            return False

# Test function
def test_connection():
    """Test Calendar API connection"""
    try:
        calendar = CalendarAPI()
        events = calendar.fetch_upcoming_events(max_results=5)
        print(f"Successfully connected! Found {len(events)} upcoming events.")
        return True
    except Exception as e:
        print(f"Connection failed: {e}")
        return False

if __name__ == "__main__":
    test_connection()