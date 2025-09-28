"""
LangGraph implementation for AI Voice Agent
Manages the flow between Gmail monitoring, Calendar analysis, and user interactions
"""

from typing import TypedDict, List, Dict, Any
from datetime import datetime, timedelta
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
import logging
import sys
import os
from services.gmail import GmailAPI
from services.calendar import CalendarAPI

# Add parent directory to path for service imports
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.append(parent_dir)


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# State Management Class
class AgentState(TypedDict):
    # Data sources - using simple dictionaries instead of typed structures
    emails: List[Dict[str, Any]]
    calendar_events: List[Dict[str, Any]]
    
    # System state
    last_check: datetime
    error_count: int
    
    # Flow control
    current_step: str
    
    # Summary data - contains processed information
    summary: Dict[str, Any]

# Node Functions
def fetch_emails_node(state: AgentState) -> AgentState:
    """Fetch emails from the last 24 hours"""
    logger.info("Fetching emails from the last 24 hours...")
    
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
            logger.warning(f"Failed to log emails: {log_error}")
        
        # Add basic processing to each email
        formatted_emails = []
        for email in new_emails:
            # Just use the dictionary directly, adding any needed fields
            email_dict = {
                "id": email.get("id", ""),
                "subject": email.get("subject", "No Subject"),
                "sender": email.get("sender", "Unknown"),
                "body": email.get("body", "")[:500],  # Truncate for LLM processing
                "timestamp": email.get("timestamp", datetime.now()),
                "importance_score": 0.0,  # Default until analysis
            }
            formatted_emails.append(email_dict)
        
        state["emails"].extend(formatted_emails)
        state["current_step"] = "fetch_calendar"  # Changed from "analyze_emails" to skip analysis
        logger.info(f"Fetched {len(formatted_emails)} new emails")
        
    except Exception as e:
        logger.error(f"Error fetching emails: {e}")
        state["error_count"] += 1
        
    return state

def fetch_calendar_node(state: AgentState) -> AgentState:
    """Fetch calendar events from Google Calendar API"""
    logger.info("Fetching calendar events...")
    
    try:
        # Use directly imported CalendarAPI or import if needed
        if CalendarAPI is None:
            from services.calendar import CalendarAPI as Calendar
        else:
            Calendar = CalendarAPI
        
        calendar_api = Calendar()
        
        # Fetch events for next 7 days
        end_date = datetime.now() + timedelta(days=7)
        events = calendar_api.fetch_upcoming_events(end_date=end_date)
        
        # LOG FETCHED CALENDAR EVENTS FOR DEBUGGING
        try:
            from services.data_logger import log_fetched_calendar_events
            log_fetched_calendar_events(events)
        except Exception as log_error:
            logger.warning(f"Failed to log calendar events: {log_error}")
        
        # Process each event into a simple dictionary
        formatted_events = []
        for event in events:
            try:
                # Add debugging to trace the event structure
                logger.debug(f"Processing event: {event.get('title', 'Untitled')}")
                logger.debug(f"Event type: {type(event)}")
                
                # Create a simplified event dictionary
                event_dict = {
                    "id": event.get("id", ""),
                    "title": event.get("title", "Untitled Event"),
                    "start_time": event.get("start_time"),
                    "end_time": event.get("end_time"),
                    "attendees": event.get("attendees", []),
                    "location": event.get("location", ""),
                    "description": event.get("description", ""),
                    "importance_score": 0.0,  # Will be set by analysis
                    "requires_action": False,
                    "conflict_detected": False
                }
                formatted_events.append(event_dict)
            except Exception as event_error:
                logger.error(f"Error processing event: {event_error}")
                logger.error(f"Event data: {event}")
                continue
        
        state["calendar_events"] = formatted_events
        state["current_step"] = "check_zoom"  # Changed from "analyze_calendar" to skip analysis
        logger.info(f"Fetched {len(formatted_events)} calendar events")
        
    except Exception as e:
        logger.error(f"Error fetching calendar: {e}")
        state["error_count"] += 1
        
    return state

def check_zoom_node(state: AgentState) -> AgentState:
    """Placeholder for Zoom integration - to be implemented in future"""
    logger.info("Checking Zoom meetings... (placeholder for future implementation)")
    
    # Simply pass through for now
    state["current_step"] = "check_slack"
    
    return state

def check_slack_node(state: AgentState) -> AgentState:
    """Placeholder for Slack integration - to be implemented in future"""
    logger.info("Checking Slack messages... (placeholder for future implementation)")
    
    # Simply pass through for now
    state["current_step"] = "summarize"
    
    return state

def summarize_node(state: AgentState) -> AgentState:
    """Create a summary of emails and calendar events"""
    logger.info("Creating summary of emails and calendar events...")
    
    try:
        # Count today's calendar events
        today = datetime.now().date()
        today_events = [
            event for event in state["calendar_events"] 
            if isinstance(event.get("start_time"), datetime) and event["start_time"].date() == today
        ]
        
        # Create summary information
        state["summary"] = {
            "total_emails": len(state["emails"]),
            "total_calendar_events": len(state["calendar_events"]),
            "today_events": len(today_events),
            "today_events_details": [{
                "title": event["title"],
                "time": event["start_time"].strftime("%I:%M %p") if hasattr(event["start_time"], "strftime") else str(event["start_time"]),
                "location": event.get("location", "No location"),
                "attendees": len(event.get("attendees", [])),
                "attendee_names": event.get("attendees", [])[:5]  # Show up to 5 attendees
            } for event in today_events],
            "email_subjects": [{"subject": email["subject"], "sender": email["sender"]} for email in state["emails"][:10]]  # Limit to first 10
        }
        
        # Log the summary
        logger.info(f"Summary generated:")
        logger.info(f"- Total emails: {state['summary']['total_emails']}")
        logger.info(f"- Today's events: {state['summary']['today_events']}")
        
        # Set final state
        state["last_check"] = datetime.now()
        
    except Exception as e:
        logger.error(f"Error creating summary: {e}")
        state["error_count"] += 1
        
    return state

# Create the main workflow graph
def create_agent_graph() -> StateGraph:
    """Create and configure the simplified LangGraph workflow"""
    
    # Initialize the graph
    workflow = StateGraph(AgentState)
    
    # Add only the necessary nodes
    workflow.add_node("fetch_emails", fetch_emails_node)
    workflow.add_node("fetch_calendar", fetch_calendar_node)
    workflow.add_node("check_zoom", check_zoom_node)
    workflow.add_node("check_slack", check_slack_node)
    workflow.add_node("summarize", summarize_node)
    
    # Set entry point
    workflow.set_entry_point("fetch_emails")

    # Simplified flow: fetch emails -> fetch calendar -> check_zoom -> check_slack -> summarize -> end
    workflow.add_edge("fetch_emails", "fetch_calendar")
    workflow.add_edge("fetch_calendar", "check_zoom")
    workflow.add_edge("check_zoom", "check_slack")
    workflow.add_edge("check_slack", "summarize")
    
    # Summarize node always ends the workflow
    workflow.add_edge("summarize", END)
    
    # Add memory for state persistence
    memory = MemorySaver()
    
    # Compile the graph
    app = workflow.compile(checkpointer=memory)
    
    return app

def initialize_agent_state() -> AgentState:
    """Initialize the agent state with default values"""
    return AgentState(
        emails=[],
        calendar_events=[],
        last_check=datetime.now(),
        error_count=0,
        current_step="fetch_emails",
        summary={
            "total_emails": 0,
            "total_calendar_events": 0,
            "today_events": 0,
            "today_events_details": [],
            "email_subjects": []
        }
    )