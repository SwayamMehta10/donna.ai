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
from services.google_calendar import CalendarAPI
from services.email_analyzer import EmailAnalyzer
# Org Lookup
import requests
import re
from bs4 import BeautifulSoup
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get API credentials from environment variables
API_KEY = os.getenv('GOOGLE_API_KEY')
CSE_ID = os.getenv('GOOGLE_CSE_ID')

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

    # Reservation data
    reservation_summary: Dict[str, Any]
    reservation_text: str
    phone_number_to_call: str  # Phone number for reservation callback

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
        
        formatted_emails = []
        for email in new_emails:
            email_dict = {
                "id": email.get("id", ""),
                "subject": email.get("subject", "No Subject"),
                "sender": email.get("sender", "Unknown"),
                "body": email.get("body", "")[:1000],
                "timestamp": email.get("timestamp", datetime.now()),
            }
            formatted_emails.append(email_dict)
        
        state["emails"].extend(formatted_emails)
        state["current_step"] = "analyze_emails"
        logger.info(f"Fetched {len(formatted_emails)} new emails")
        
    except Exception as e:
        logger.error(f"Error fetching emails: {e}")
        state["error_count"] += 1
        
    return state

def analyze_emails_node(state: AgentState) -> AgentState:
    """
    SKIP Gemini AI analysis for speed - just pass through emails
    Agent will read emails in batches of 5 during the call
    """
    logger.info("Skipping Gemini analysis - emails will be read in batches during call")

    try:
        emails = state.get("emails", [])

        if not emails:
            logger.info("No emails to analyze")
            state["current_step"] = "fetch_calendar"
            return state

        # NO GEMINI ANALYSIS - Just log count
        logger.info(f"📧 {len(emails)} emails fetched (no AI analysis - will read in batches)")
        
        # Store emails as-is without analysis
        # The call agent will read them in batches of 5
        
        state["current_step"] = "fetch_calendar"

    except Exception as e:
        logger.error(f"Error in analyze_emails_node: {e}")
        state["error_count"] += 1
        state["current_step"] = "fetch_calendar"

    return state


def fetch_calendar_node(state: AgentState) -> AgentState:
    """Fetch calendar events from Google Calendar API"""
    logger.info("Fetching calendar events...")
    
    try:
        # Use directly imported CalendarAPI or import if needed
        if CalendarAPI is None:
            from services.google_calendar import CalendarAPI as Calendar
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
                    "description": event.get("description", "")
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

# Zoom integration removed - not needed for current requirements

# Slack integration removed - not needed for current requirements

def lookup_organization(organization_name):
    """Search Google Custom Search for organization details."""
    if not API_KEY or not CSE_ID:
        logger.error("Google Custom Search API credentials not configured")
        return None

    query = f"{organization_name} contact details and timings"

    try:
        search_url = f"https://www.googleapis.com/customsearch/v1?key={API_KEY}&cx={CSE_ID}&q={query.replace(' ', '+')}&num=5"
        response = requests.get(search_url)
        response.raise_for_status()
        results = response.json()
        
        details = {
            'phone': None,
            'address': None,
            'hours': None,
            'website': None
        }
        
        # Extract from snippets and links
        for item in results.get('items', []):
            snippet = item.get('snippet', '')
            title = item.get('title', '')
            
            # Phone (regex for various formats like (800) 642-7676 or 480-858-1660)
            phone_match = re.search(r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}|\d{10}', snippet)
            if phone_match and not details['phone']:
                details['phone'] = phone_match.group().strip()
            
            # Address (loosen regex to catch partial addresses)
            address_match = re.search(r'[\d]+ [A-Za-z\s]+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd),?\s*[A-Za-z\s]+,?\s*[A-Z]{2}\s*\d{5}|(?:[A-Za-z\s]+,?\s*[A-Z]{2})', snippet)
            if address_match and not details['address']:
                details['address'] = address_match.group().strip()
            
            # Hours (e.g., "Mon–Fri 6:00 AM to 6:00 PM")
            hours_match = re.search(r'(?:mon|tue|wed|thu|fri|sat|sun)[a-z]*\s*[-–]\s*(?:mon|tue|wed|thu|fri|sat|sun)[a-z]*\s*\d{1,2}:\d{2}\s*(?:AM|PM)\s*to\s*\d{1,2}:\d{2}\s*(?:AM|PM)', snippet, re.IGNORECASE)
            if hours_match and not details['hours']:
                details['hours'] = hours_match.group()
            
            # Website
            if not details['website']:
                details['website'] = item.get('link')
        
        # Fallback: Check website content for address (basic attempt)
        if not details['address'] and details['website']:
            try:
                website_response = requests.get(details['website'], headers={'User-Agent': 'Mozilla/5.0'}, timeout=5)
                website_soup = BeautifulSoup(website_response.text, 'html.parser')
                address_tag = website_soup.find('address') or website_soup.find(string=re.compile(r'[A-Za-z\s]+, [A-Z]{2} \d{5}'))
                if address_tag:
                    details['address'] = address_tag.get_text().strip() if isinstance(address_tag, str) else address_tag.strip()
            except Exception:
                pass  # Skip if website fails
        
        return details
        
    except Exception as e:
        return {'error': f'Search failed: {str(e)}'}
    
def make_reservation_node(state: AgentState) -> AgentState:
    """Make reservation for a restaurant, doctor appointment, etc."""
    import os
    import groq
    import json
    import re

    logger.info("Checking if user wants to make a reservation...")

    # Get user input for reservation
    needs_reservation = input("\n🍽️  Do you want to make a reservation? (yes/no): ").strip().lower()
    
    # Skip if user doesn't want to make a reservation
    if needs_reservation in ['no', 'n', 'skip', 'nope']:
        logger.info("No reservation requested, proceeding to summary and call")
        state["current_step"] = "summarize"
        return state

    # Interactive reservation details collection
    try:
        print("\n📋 Let's collect the reservation details...")

        # Collect restaurant name
        place_name = input("🏪 Restaurant name: ").strip()
        if not place_name:
            logger.info("No restaurant name provided, skipping reservation")
            state["current_step"] = "summarize"
            return state

        # Collect number of people
        people = input("👥 Number of people: ").strip()

        # Collect date
        date = input("📅 Date (e.g., 'today', 'tomorrow', '12/25'): ").strip() or "today"

        # Collect time
        time = input("🕐 Time (e.g., '7:00 PM', '19:00'): ").strip()

        # Optional special requests
        special_requests = input("📝 Any special requests? (optional): ").strip() or None

        logger.info(f"Collected reservation details: {place_name}, {people} people, {date} at {time}")

        # Lookup restaurant details
        print(f"\n🔍 Looking up {place_name} details...")
        location_details = lookup_organization(place_name)

        if location_details:
            logger.info(f"Found location details: {location_details}")
            print(f"✅ Found: {location_details.get('phone', 'No phone')}")
            if location_details.get('address'):
                print(f"   Address: {location_details['address']}")
            if location_details.get('hours'):
                print(f"   Hours: {location_details['hours']}")
        else:
            logger.warning(f"Could not find details for {place_name}")
            location_details = {}

        # Create reservation summary
        reservation_summary = {
            "reservation_type": "restaurant",
            "location_name": place_name,
            "location_details": location_details,
            "time": time,
            "date": date,
            "people": people,
            "special_requests": special_requests
        }

        # Create call context for making the reservation
        phone = location_details.get("phone") if location_details else None
        if phone:
            reservation_text = (
                f"Call {place_name} at {phone} to make a reservation "
                f"for {people} people on {date} at {time}."
            )
            if special_requests:
                reservation_text += f" Special requests: {special_requests}."

            # Store reservation data
            state["reservation_summary"] = reservation_summary
            state["reservation_text"] = reservation_text
            state["phone_number_to_call"] = phone

            print(f"\n✅ Reservation details collected!")
            print(f"📍 Restaurant: {place_name}")
            print(f"📞 Phone: {phone}")
            print(f"👥 Party size: {people}")
            print(f"📅 Date: {date}")
            print(f"🕐 Time: {time}")
            if special_requests:
                print(f"📝 Special requests: {special_requests}")

            print(f"\n📞 Agent will now call the restaurant to make your reservation...")
            logger.info("Reservation details ready for phone call")
        else:
            print(f"\n⚠️  Could not find phone number for {place_name}")
            print("Please provide the phone number manually or proceed to summary.")
            state["current_step"] = "summarize"

    except Exception as e:
        logger.error(f"Error collecting reservation details: {e}")
        print(f"❌ Error: {e}")
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
            "email_subjects": [{"subject": email["subject"], "sender": email["sender"]} for email in state["emails"][:10]],  # Limit to first 10
            "important_emails": state.get("important_emails", []),  # Include AI-analyzed important emails
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
    workflow.add_node("analyze_emails", analyze_emails_node)
    workflow.add_node("fetch_calendar", fetch_calendar_node)
    # workflow.add_node("make_reservation", make_reservation_node)
    workflow.add_node("summarize", summarize_node)

    # Set entry point
    workflow.set_entry_point("fetch_emails")

    # Updated flow: fetch emails -> analyze emails -> fetch calendar -> summarize
    # The `make_reservation` node is temporarily commented out and removed from routing.
    workflow.add_edge("fetch_emails", "analyze_emails")
    workflow.add_edge("analyze_emails", "fetch_calendar")

    # Temporarily disabled 'make_reservation' routing (node preserved but not used):
    # workflow.add_edge("fetch_calendar", "make_reservation")
    # workflow.add_conditional_edges(
    #     "make_reservation",
    #     lambda state: "summarize" if not state.get("reservation_text") else END,
    #     {
    #         "summarize": "summarize",
    #         END: END
    #     }
    # )

    # Directly proceed to summarize while reservation node is disabled
    workflow.add_edge("fetch_calendar", "summarize")

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
        },
        reservation_summary={},
        reservation_text="",
        phone_number_to_call=""
    )