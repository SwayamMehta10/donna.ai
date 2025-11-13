from src.utils.mylogger import logging
from src.services.gmail import GmailAPI
from src.services.google_calendar import CalendarAPI
from datetime import datetime, timedelta
from typing import TypedDict, Optional
from livekit.agents import RunContext
import dateparser
from dateutil import parser as dateutil_parser

class EmailData(TypedDict):
    id: str
    subject: str
    sender: str
    body: str
    timestamp: datetime
    importance_score: float
    requires_action: bool
    action_type: Optional[str]  # "reply", "schedule", "urgent", etc.
    urgency: str  # "low", "medium", "high", "critical"
    suggested_action: Optional[str]
    summary: Optional[str]

async def fetch_emails(sender_name: Optional[str] = None, subject_keyword: Optional[str] = None):
    """
    Fetch and display full email details when user asks about specific emails.
    
    Args:
        sender_name: Name or email address of sender (e.g., "John Smith", "john@example.com")
        subject_keyword: Keyword from email subject to search for
    
    Use this when user asks:
    - "Tell me more about the email from [sender]"
    - "What did [sender] say?"
    - "Show me the email about [subject]"
    - "Read the full email from [sender]"
    """
    logging.info(f"Fetching email details - sender: {sender_name}, subject: {subject_keyword}")
    
    try:
        gmail_api = GmailAPI()
        
        # Fetch recent emails
        since_24h = datetime.now() - timedelta(hours=24)
        recent_emails = gmail_api.fetch_recent_emails(since=since_24h, max_results=50)
        
        if not recent_emails:
            return "No emails found in the last 24 hours."
        
        # If no search criteria, return summary of recent emails
        if not sender_name and not subject_keyword:
            email_summary = f"Here are your recent emails:\n\n"
            for i, email in enumerate(recent_emails[:5], 1):
                email_summary += f"{i}. From: {email['sender']}\n"
                email_summary += f"   Subject: {email['subject']}\n"
                email_summary += f"   Preview: {email['body'][:100]}...\n\n"
            
            if len(recent_emails) > 5:
                email_summary += f"\n...and {len(recent_emails) - 5} more emails."
            
            return email_summary
        
        # Search for matching email
        matched_email = None
        search_term = (sender_name or subject_keyword or "").lower()
        
        for email in recent_emails:
            sender = email['sender'].lower()
            subject = email['subject'].lower()
            
            # Check if search term matches sender or subject
            if sender_name and search_term in sender:
                matched_email = email
                break
            elif subject_keyword and search_term in subject:
                matched_email = email
                break
        
        if not matched_email:
            return f"I couldn't find an email matching '{search_term}' in your recent emails. Could you be more specific or check if you have emails from them?"
        
        # Get full email content (already in matched_email['body'])
        full_body = matched_email.get('body', 'Email body not available')
        timestamp = matched_email['timestamp'].strftime("%B %d at %I:%M %p")
        
        # Format full email in voice-friendly way
        response = f"""
Here's the full email from {matched_email['sender']}:

Subject: {matched_email['subject']}
Received: {timestamp}

{full_body}

Would you like to reply to this email?
"""
        
        return response.strip()
        
    except Exception as e:
        logging.error(f"Error fetching emails: {e}")
        return f"I encountered an error fetching email details: {str(e)}"


async def draft_reply(email_identifier: str, reply_content: str):
    """
    Create a draft reply to an existing email using Gemini AI for professional drafting.
    Use this when user asks to reply to an email or draft a response.
    
    Args:
        email_identifier: Either the email ID, sender's email address, or sender's name
                         Examples: "19a6b5831a3b8e73", "john@example.com", "John Smith"
        reply_content: User's casual description of what they want to communicate
                      Example: "tell him I'll be there and bring the reports"
    
    Returns:
        Confirmation message with draft ID
    """
    logging.info(f"Creating draft reply for email identifier: {email_identifier}")
    
    try:
        from src.services.email_drafter import EmailDrafter
        
        gmail_api = GmailAPI()
        
        # Check if it's already an email ID (starts with alphanumeric, no @ or spaces)
        if '@' not in email_identifier and ' ' not in email_identifier and len(email_identifier) > 10:
            # Likely an email ID, use directly
            email_id = email_identifier
            logging.info(f"Using provided email ID: {email_id}")
            # Need to fetch email details for Gemini drafting
            recent_emails = gmail_api.fetch_recent_emails(max_results=50)
            matched_email = next((e for e in recent_emails if e['id'] == email_id), None)
        else:
            # It's a name or email address - search for matching email
            logging.info(f"Searching for email matching: {email_identifier}")
            recent_emails = gmail_api.fetch_recent_emails(max_results=50)
            
            # Search for matching email
            email_id = None
            matched_email = None
            
            for email in recent_emails:
                sender = email['sender'].lower()
                # Check if identifier matches email address or name in sender
                if email_identifier.lower() in sender:
                    email_id = email['id']
                    matched_email = email
                    logging.info(f"Found matching email from: {email['sender']}")
                    break
            
            if not email_id:
                return f"I couldn't find a recent email from '{email_identifier}'. Could you be more specific or check if you have emails from them in the last 24 hours?"
        
        if not matched_email:
            return f"I found the email but couldn't retrieve its details. Please try again."
        
        # Use Gemini to draft professional reply
        logging.info(f"Using Gemini AI to draft professional reply based on user intent: '{reply_content}'")
        drafter = EmailDrafter()
        professional_reply = drafter.draft_reply(matched_email, reply_content)
        
        logging.info(f"Gemini drafted reply (first 100 chars): {professional_reply[:100]}")
        
        # Create the draft reply with Gemini-generated content
        draft_id = gmail_api.create_draft_reply(email_id, professional_reply)
        
        if draft_id:
            return f"I've created a professional draft reply to {matched_email['sender']} (Subject: {matched_email['subject']}). Draft ID: {draft_id}. You can review and send it from your Gmail drafts."
        else:
            return "I encountered an error creating the draft reply. Please try again."
            
    except Exception as e:
        logging.error(f"Error creating draft reply: {e}")
        return f"Failed to create draft: {str(e)}"


async def draft_new_email(to: str, subject: str, body: str, cc: str = None):
    """
    Create a new draft email using Gemini AI for professional drafting.
    Use this when user asks to compose a new email or draft a message to someone.
    
    Args:
        to: Recipient email address (must be valid format: name@domain.com)
        subject: Email subject line
        body: User's casual description of what they want to communicate
              Example: "ask him about the Q4 budget and if he needs anything"
        cc: Optional CC recipients (comma-separated email addresses)
    
    Returns:
        Confirmation message with draft ID
    """
    logging.info(f"Creating new draft email to {to}")
    
    try:
        import re
        from src.services.email_drafter import EmailDrafter
        
        # Validate email address format
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        
        if not re.match(email_pattern, to):
            return f"Invalid email address '{to}'. Please provide a valid email address in the format name@domain.com"
        
        # Validate CC if provided
        if cc:
            cc_emails = [email.strip() for email in cc.split(',')]
            for email in cc_emails:
                if not re.match(email_pattern, email):
                    return f"Invalid CC email address '{email}'. Please use format name@domain.com"
        
        # Use Gemini to draft professional email body
        logging.info(f"Using Gemini AI to draft professional email to {to}")
        drafter = EmailDrafter()
        professional_body = drafter.draft_new_email(to, subject, body)
        
        logging.info(f"Gemini drafted email (first 100 chars): {professional_body[:100]}")
        
        gmail_api = GmailAPI()
        draft_id = gmail_api.create_draft_email(to, subject, professional_body, cc)
        
        if draft_id:
            return f"I've created a professional draft email to {to} with subject '{subject}' (ID: {draft_id}). You can review and send it from your Gmail drafts."
        else:
            return "I encountered an error creating the draft. Please try again."
            
    except Exception as e:
        logging.error(f"Error creating draft email: {e}")
        return f"Failed to create draft: {str(e)}"


def parse_natural_datetime(time_string: str) -> Optional[datetime]:
    """
    Parse natural language time strings into datetime objects.
    
    Args:
        time_string: Natural language time description
                    Examples: "tomorrow at 2pm", "next Monday 10am", "in 3 hours"
    
    Returns:
        datetime object or None if parsing fails
    """
    try:
        # Use dateparser for natural language parsing
        settings = {
            'PREFER_DATES_FROM': 'future',
            'RETURN_AS_TIMEZONE_AWARE': False,
            'RELATIVE_BASE': datetime.now()
        }
        
        parsed_time = dateparser.parse(time_string, settings=settings)
        
        if parsed_time:
            logging.info(f"Parsed '{time_string}' to {parsed_time}")
            return parsed_time
        
        # Fallback to dateutil parser
        try:
            parsed_time = dateutil_parser.parse(time_string, fuzzy=True)
            logging.info(f"Parsed '{time_string}' to {parsed_time} (using dateutil)")
            return parsed_time
        except:
            pass
            
        logging.warning(f"Failed to parse time string: {time_string}")
        return None
        
    except Exception as e:
        logging.error(f"Error parsing datetime '{time_string}': {e}")
        return None


async def create_calendar_event(
    title: str,
    start_time: str,
    duration_minutes: int = 60,
    description: str = "",
    location: str = "",
    attendees: str = None
):
    """
    Create a new calendar event.
    Use this when user wants to schedule a meeting, appointment, reminder, or any calendar event.
    
    Args:
        title: Event title/summary (e.g., "Team standup", "Lunch with John")
        start_time: Start time in natural language (e.g., "tomorrow at 2pm", "next Monday 10am", "Friday 3pm")
        duration_minutes: Event duration in minutes (default: 60). Use 30 for short meetings, 120 for long ones.
        description: Event description/notes/agenda (optional)
        location: Event location (e.g., "Conference Room A", "Zoom", address) (optional)
        attendees: Comma-separated email addresses of attendees (optional)
                  Example: "john@example.com, sarah@example.com"
    
    Returns:
        Confirmation message with event details and ID
    """
    logging.info(f"Creating calendar event: {title} at {start_time}")
    
    try:
        # Parse the start time
        start_dt = parse_natural_datetime(start_time)
        
        if not start_dt:
            return f"I couldn't understand the time '{start_time}'. Could you rephrase it? For example: 'tomorrow at 2pm' or 'next Monday at 10am'."
        
        # Calculate end time
        end_dt = start_dt + timedelta(minutes=duration_minutes)
        
        # Parse attendees if provided
        attendee_list = None
        if attendees:
            attendee_list = [email.strip() for email in attendees.split(',') if email.strip()]
        
        # Create event data
        event_data = {
            'title': title,
            'start_time': start_dt,
            'end_time': end_dt,
            'description': description,
            'location': location,
            'attendees': attendee_list
        }
        
        # Create the event
        calendar_api = CalendarAPI()
        event_id = calendar_api.create_event(event_data)
        
        if event_id:
            # Format confirmation message
            date_str = start_dt.strftime("%A, %B %d at %I:%M %p")
            duration_str = f"{duration_minutes} minutes" if duration_minutes != 60 else "1 hour"
            
            message = f"I've created '{title}' for {date_str} ({duration_str})."
            
            if attendee_list:
                attendee_names = ', '.join([email.split('@')[0] for email in attendee_list])
                message += f" Calendar invitations sent to {attendee_names}."
            
            if location:
                message += f" Location: {location}."
            
            message += f" Event ID: {event_id}"
            
            logging.info(f"Successfully created event: {event_id}")
            return message
        else:
            return "I encountered an error creating the calendar event. Please try again."
            
    except Exception as e:
        logging.error(f"Error creating calendar event: {e}")
        import traceback
        logging.error(traceback.format_exc())
        return f"Failed to create event: {str(e)}"


async def view_calendar(days_ahead: int = 7):
    """
    View upcoming calendar events.
    Use this when user asks about their schedule, upcoming meetings, or what's on their calendar.
    
    Args:
        days_ahead: Number of days to look ahead (default: 7)
    
    Returns:
        Formatted list of upcoming events
    """
    # Handle string to int conversion if needed
    if isinstance(days_ahead, str):
        try:
            days_ahead = int(days_ahead)
        except ValueError:
            days_ahead = 7  # Default fallback
    
    logging.info(f"Fetching calendar events for next {days_ahead} days")
    
    try:
        calendar_api = CalendarAPI()
        end_date = datetime.now() + timedelta(days=days_ahead)
        events = calendar_api.fetch_upcoming_events(end_date=end_date)
        
        if not events:
            return f"You have no events scheduled for the next {days_ahead} days."
        
        # Format events
        message = f"You have {len(events)} upcoming events:\n\n"
        
        for i, event in enumerate(events[:10], 1):  # Limit to 10 events
            start_time = event['start_time']
            date_str = start_time.strftime("%A, %B %d at %I:%M %p")
            
            message += f"{i}. {event['title']}\n"
            message += f"   When: {date_str}\n"
            
            if event.get('location'):
                message += f"   Where: {event['location']}\n"
            
            if event.get('attendees'):
                attendee_count = len(event['attendees'])
                message += f"   Attendees: {attendee_count} people\n"
            
            message += "\n"
        
        if len(events) > 10:
            message += f"...and {len(events) - 10} more events."
        
        return message
        
    except Exception as e:
        logging.error(f"Error fetching calendar: {e}")
        return f"I encountered an error fetching your calendar: {str(e)}"

        

        

        

        
