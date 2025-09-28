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
# Org Lookup
import requests
import re
from bs4 import BeautifulSoup

# Replace with your API key and CSE ID
API_KEY = 'AIzaSyDSNb9Ak99yF64K2sc5LAjdSZJ0rLLFl8Q'  # From Google Cloud Credentials
CSE_ID = 'e47b6bcbeb6e64c9a'    # From cse.google.com

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
    state["current_step"] = "make_reservation"
    
    return state

def lookup_organization(organization_name):
    """Search Google Custom Search for organization details."""
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
    
    logger.info("Checking if user wants to make a reservation...")
    
    # Get user input for reservation
    needs_reservation = input("Do you want to make any reservations or appointments? ")
    
    # Skip if user doesn't want to make a reservation
    if not needs_reservation or needs_reservation.lower() == 'no' or needs_reservation.lower() == 'skip':
        logger.info("No reservation requested, proceeding to summary")
        state["current_step"] = "summarize"
        return state
    
    try:
        # Get Groq API key from environment
        api_key = os.getenv('GROQ_API_KEY') or os.getenv('LLM_API_KEY')
        if not api_key:
            logger.error("Groq API key not found in environment variables")
            state["current_step"] = "summarize"
            return state
            
        # Initialize Groq client
        client = groq.Groq(api_key=api_key)
        
        # Define the extraction prompt
        prompt = f"""
        Extract the following information from the user's request:
        - Restaurant/Place name
        - Date (today if not specified)
        - Time
        - Number of people/guests
        - Any special requests
        
        Format the output as JSON with the following structure:
        {{
            "place_name": "string",
            "date": "string",
            "time": "string",
            "people": "number as string",
            "special_requests": "string or null"
        }}
        
        User Request: {needs_reservation}
        
        JSON Output:
        """
        
        # Call Groq API
        logger.info("Calling Groq API to extract reservation details...")
        response = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.1-8b-instant",
            temperature=0.1,
            max_tokens=500
        )
        
        # Extract JSON from response
        result_text = response.choices[0].message.content
        logger.info(f"Raw response from Groq: {result_text}")
        
        # Find JSON content between braces
        json_start = result_text.find('{')
        json_end = result_text.rfind('}') + 1
        
        if json_start >= 0 and json_end > json_start:
            json_content = result_text[json_start:json_end]
            
            try:
                # Replace any newlines, extra spaces that might cause parsing issues
                cleaned_json = json_content.replace('\n', ' ').replace('\r', '')
                print(f"Attempting to parse JSON: {cleaned_json}")
                reservation_details = json.loads(cleaned_json)
                logger.info(f"Extracted reservation details: {reservation_details}")
            except json.JSONDecodeError as e:
                logger.error(f"JSON parsing error: {e}, JSON content: {cleaned_json}")
                
                # Fallback to manual extraction
                print("Using fallback extraction method...")
                # Create a simple extraction based on the original request
                reservation_details = {
                    "place_name": needs_reservation.split("at ")[1].split(" for ")[0].strip() if "at " in needs_reservation and " for " in needs_reservation else "",
                    "time": needs_reservation.split(" for ")[1].split(" ")[0] if " for " in needs_reservation and len(needs_reservation.split(" for ")) > 1 else "",
                    "date": "tonight" if "tonight" in needs_reservation else "today",
                    "people": "".join([c for c in needs_reservation.split("for ")[-1] if c.isdigit()]) if "for " in needs_reservation else ""
                }
            
            # Get organization details using the place name
            place_name = reservation_details.get("place_name", "")
            if place_name:
                location_details = lookup_organization(place_name)
                logger.info(f"Organization details: {location_details}")
                
                # Create summary for reservation
                reservation_summary = {
                    "reservation_type": "restaurant",  # Default to restaurant
                    "location_name": place_name,
                    "location_details": location_details,
                    "time": reservation_details.get("time", ""),
                    "date": reservation_details.get("date", "today"),
                    "people": reservation_details.get("people", ""),
                    "special_requests": reservation_details.get("special_requests", "")
                }
                
                # Format text for call context
                reservation_text = f"I'd like to make a reservation at {place_name} for {reservation_summary['time']} on {reservation_summary['date']} for {reservation_summary['people']} people."
                
                # Add organization details if available
                if location_details:
                    if location_details.get("phone"):
                        reservation_text += f" The phone number is {location_details['phone']}."
                    if location_details.get("address"):
                        reservation_text += f" The address is {location_details['address']}."
                    if location_details.get("hours"):
                        reservation_text += f" They're open {location_details['hours']}."
                
                # Store reservation data in state
                state["reservation_summary"] = reservation_summary
                state["reservation_text"] = reservation_text
                
                print("✅ Successfully processed reservation request")
                print(f"📍 Location: {place_name}")
                print(f"🕒 Time: {reservation_summary['time']}")
                print(f"📅 Date: {reservation_summary['date']}")
                print(f"👥 People: {reservation_summary['people']}")
                
                # Skip summarize node and end flow
                logger.info("Reservation details extracted, ending flow")
                return state
            else:
                logger.error("No place name extracted from user input")
        else:
            logger.error("Could not extract JSON from Groq response")
    
    except Exception as e:
        logger.error(f"Error processing reservation: {e}")
        print(f"Error processing reservation: {e}")
        
        # Try a simple fallback method if an exception occurs
        try:
            # Simple extraction logic based on common patterns in reservation requests
            if "reservation" in needs_reservation and "at " in needs_reservation:
                # Extract place name (after "at " but before " for ")
                parts = needs_reservation.split("at ")
                if len(parts) > 1:
                    place_parts = parts[1].split(" for ")
                    place_name = place_parts[0].strip()
                    
                    # Try to extract time and people
                    time = ""
                    people = ""
                    date = "today"
                    
                    if "tonight" in needs_reservation:
                        date = "tonight"
                    
                    # Look for time pattern (e.g., 8:30 pm)
                    import re
                    time_match = re.search(r'\d{1,2}(?::\d{2})?\s*(?:am|pm)', needs_reservation, re.IGNORECASE)
                    if time_match:
                        time = time_match.group()
                    
                    # Look for number of people
                    people_match = re.search(r'for\s+(\d+)\s+people', needs_reservation, re.IGNORECASE)
                    if people_match:
                        people = people_match.group(1)
                    
                    # Get location details
                    location_details = lookup_organization(place_name)
                    
                    # Create summary
                    reservation_summary = {
                        "reservation_type": "restaurant",
                        "location_name": place_name,
                        "location_details": location_details,
                        "time": time,
                        "date": date,
                        "people": people,
                        "special_requests": ""
                    }
                    
                    # Format text
                    reservation_text = f"I'd like to make a reservation at {place_name} for {time} on {date} for {people} people."
                    
                    # Add organization details
                    if location_details:
                        if location_details.get("phone"):
                            reservation_text += f" The phone number is {location_details['phone']}."
                        if location_details.get("address"):
                            reservation_text += f" The address is {location_details['address']}."
                        if location_details.get("hours"):
                            reservation_text += f" They're open {location_details['hours']}."
                    
                    # Store in state
                    state["reservation_summary"] = reservation_summary
                    state["reservation_text"] = reservation_text
                    
                    print("✅ Successfully processed reservation request using fallback method")
                    print(f"📍 Location: {place_name}")
                    print(f"🕒 Time: {time}")
                    print(f"📅 Date: {date}")
                    print(f"👥 People: {people}")
                    
                    logger.info(f"Used fallback method to extract reservation details: {reservation_summary}")
                    return state
        except Exception as fallback_error:
            logger.error(f"Fallback extraction also failed: {fallback_error}")
    
    # Continue to summary if all reservation processing fails
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
    workflow.add_node("make_reservation", make_reservation_node)
    workflow.add_node("summarize", summarize_node)
    
    # Set entry point
    workflow.set_entry_point("fetch_emails")

    # Simplified flow: fetch emails -> fetch calendar -> check_zoom -> check_slack -> make_reservation
    workflow.add_edge("fetch_emails", "fetch_calendar")
    workflow.add_edge("fetch_calendar", "check_zoom")
    workflow.add_edge("check_zoom", "check_slack")
    workflow.add_edge("check_slack", "make_reservation")
    
    # Add conditional routing based on whether we have a reservation
    workflow.add_conditional_edges(
        "make_reservation",
        lambda state: "summarize" if not state.get("reservation_text") else END,
        {
            "summarize": "summarize",
            END: END
        }
    )
    
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
        reservation_text=""
    )