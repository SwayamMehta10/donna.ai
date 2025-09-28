from mylogger import logging
from services.gmail import GmailAPI
from services.calendar import CalendarAPI
from services import model
from services import notification
from services import conflict_detector
from services import scheduler
from datetime import datetime, timedelta
from typing import TypedDict, Optional
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

async def fetch_emails():
    """Fetch emails from the last 24 hours"""
    logging.info("Fetching emails from the last 24 hours...")
    
    try:
        # Use directly imported GmailAPI or import if needed
        if GmailAPI is None:
            from services.gmail import GmailAPI as Gmail
        else:
            Gmail = GmailAPI
        
        gmail_api = Gmail()
        
        # Always fetch emails from last 24 hours, regardless of last_check
        since_24h = datetime.now() - timedelta(hours=24)
        new_emails = gmail_api.fetch_recent_emails(since=since_24h)
        
        # LOG FETCHED EMAILS FOR DEBUGGING
        try:
            from services.data_logger import log_fetched_emails
            log_fetched_emails(new_emails)
        except Exception as log_error:
            logging.warning(f"Failed to log emails: {log_error}")
        
        # Convert to EmailData format
        formatted_emails = []
        for email in new_emails:
            formatted_emails.append(EmailData(
                id=email["id"],
                subject=email["subject"],
                sender=email["sender"],
                body=email["body"][:500],  # Truncate for LLM processing
                timestamp=email["timestamp"],
                importance_score=0.0,  # Will be set by analysis
                requires_action=False,  # Will be determined by LLM
                action_type=None,
                urgency="medium",  # Default value until analysis
                suggested_action=None,
                summary=email["subject"]  # Default to subject until analyzed
            ))

        return formatted_emails
    except Exception as e:
        logging.error(f"Error fetching emails: {e}")

        
