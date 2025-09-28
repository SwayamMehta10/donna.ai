"""
LangGraph implementation for AI Voice Agent
Manages the flow between Gmail monitoring, Calendar analysis, and user interactions
"""

from typing import TypedDict, List, Dict, Any, Optional, Literal
from datetime import datetime, timedelta
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
import logging
import sys
import os

# Add parent directory to path for service imports
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

# Import services directly
try:
    from services.gmail import GmailAPI
    from services.calendar import CalendarAPI
    from services import model
    from services import notification
    from services import conflict_detector
    from services import scheduler
except ImportError as e:
    logger = logging.getLogger(__name__)
    logger.warning(f"Could not import services: {e}. Services will be imported dynamically.")
    
    # Fallback: Services will be imported in each function
    GmailAPI = None
    CalendarAPI = None
    model = None
    notification = None
    conflict_detector = None
    scheduler = None

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# State Management Classes
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

class CalendarEvent(TypedDict):
    id: str
    title: str
    start_time: datetime
    end_time: datetime
    attendees: List[str]
    location: Optional[str]
    description: Optional[str]
    importance_score: float
    requires_action: bool
    action_type: Optional[str]
    urgency: str
    suggested_action: Optional[str]
    conflict_detected: bool
    conflict_type: Optional[str]

class UserInteraction(TypedDict):
    interaction_id: str
    timestamp: datetime
    query: str
    response: str
    action_requested: str
    status: Literal["pending", "completed", "failed"]

class Conflict(TypedDict):
    conflict_id: str
    type: Literal["scheduling", "priority", "travel_time"]
    events_involved: List[str]
    emails_involved: List[str]
    severity: Literal["low", "medium", "high", "critical"]
    suggested_action: str
    user_decision: Optional[str]

class AgentState(TypedDict):
    # Data sources
    emails: List[EmailData]
    calendar_events: List[CalendarEvent]
    
    # Analysis results
    conflicts: List[Conflict]
    important_items: List[Dict[str, Any]]
    
    # User interactions
    user_interactions: List[UserInteraction]
    pending_actions: List[Dict[str, Any]]
    
    # System state
    last_check: datetime
    monitoring_active: bool
    error_count: int
    
    # Flow control
    current_step: str
    needs_user_input: bool
    voice_call_scheduled: bool

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
        
        state["emails"].extend(formatted_emails)
        state["current_step"] = "analyze_emails"
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
        
        # Convert to CalendarEvent format
        formatted_events = []
        for event in events:
            try:
                # Add debugging to trace the event structure
                logger.debug(f"Processing event: {event.get('title', 'Untitled')}")
                logger.debug(f"Event type: {type(event)}")
                
                formatted_events.append(CalendarEvent(
                    id=event.get("id", ""),
                    title=event.get("title", "Untitled Event"),
                    start_time=event.get("start_time"),
                    end_time=event.get("end_time"),
                    attendees=event.get("attendees", []),
                    location=event.get("location", ""),
                    description=event.get("description", ""),
                    importance_score=0.0,  # Will be set by analysis
                    requires_action=event.get("requires_action", False),  # Initialize with value from data or False
                    action_type=event.get("action_type"),  # Initialize with value from data or None
                    urgency=event.get("urgency", "medium"),  # Initialize with value from data or "medium"
                    suggested_action=event.get("suggested_action"),  # Initialize with value from data or None
                    conflict_detected=False,
                    conflict_type=None
                ))
            except Exception as event_error:
                logger.error(f"Error processing event: {event_error}")
                logger.error(f"Event data: {event}")
                continue
        
        state["calendar_events"] = formatted_events
        state["current_step"] = "analyze_calendar"
        logger.info(f"Fetched {len(formatted_events)} calendar events")
        
    except Exception as e:
        logger.error(f"Error fetching calendar: {e}")
        state["error_count"] += 1
        
    return state

def analyze_emails_node(state: AgentState) -> AgentState:
    """Analyze emails using LLM to determine importance and required actions"""
    logger.info("Analyzing emails with LLM...")
    
    try:
        # Use directly imported model or import if needed
        if model is None:
            from services import model as model_service
        else:
            model_service = model
        analyze_email_batch = model_service.analyze_email_batch
        
        unanalyzed_emails = [email for email in state["emails"] if email["importance_score"] == 0.0]
        
        if unanalyzed_emails:
            import asyncio
            analysis_results = asyncio.run(analyze_email_batch(unanalyzed_emails))
            
            # Update emails with analysis results
            for email, analysis in zip(unanalyzed_emails, analysis_results):
                email["importance_score"] = analysis["importance_score"]
                email["requires_action"] = analysis["requires_action"]
                email["action_type"] = analysis.get("action_type")
                email["urgency"] = analysis.get("urgency", "medium")
                email["suggested_action"] = analysis.get("suggested_action")
                email["summary"] = analysis.get("summary", email["subject"])
                
                # Add to important items if high importance
                if analysis["importance_score"] > 0.7:
                    state["important_items"].append({
                        "type": "email",
                        "id": email["id"],
                        "summary": analysis.get("summary", email["subject"]),
                        "urgency": analysis.get("urgency", "medium"),
                        "suggested_action": analysis.get("suggested_action")
                    })
        
        state["current_step"] = "fetch_calendar"
        logger.info(f"Analyzed {len(unanalyzed_emails)} emails")
        
    except Exception as e:
        logger.error(f"Error analyzing emails: {e}")
        state["error_count"] += 1
        
    return state

def analyze_calendar_node(state: AgentState) -> AgentState:
    """Analyze calendar events using LLM"""
    logger.info("Analyzing calendar events with LLM...")
    
    try:
        # Use directly imported model or import if needed
        if model is None:
            from services import model as model_service
        else:
            model_service = model
        analyze_calendar_batch = model_service.analyze_calendar_batch
        
        unanalyzed_events = [event for event in state["calendar_events"] if event["importance_score"] == 0.0]
        
        if unanalyzed_events:
            import asyncio
            analysis_results = asyncio.run(analyze_calendar_batch(unanalyzed_events))
            
            # Update events with analysis results
            for event, analysis in zip(unanalyzed_events, analysis_results):
                event["importance_score"] = analysis["importance_score"]
                event["requires_action"] = analysis.get("requires_action", False)
                event["action_type"] = analysis.get("action_type")
                event["urgency"] = analysis.get("urgency", "medium")
                event["suggested_action"] = analysis.get("suggested_action")
                event["summary"] = analysis.get("summary", event["title"])
                
                # Add to important items if high importance
                if analysis["importance_score"] > 0.7:
                    state["important_items"].append({
                        "type": "calendar_event",
                        "id": event["id"],
                        "summary": analysis.get("summary", event["title"]),
                        "urgency": analysis.get("urgency", "medium"),
                        "suggested_action": analysis.get("suggested_action")
                    })
        
        logger.info(f"Analyzed {len(unanalyzed_events)} calendar events")
        
        # Proceed to conflict detection
        state["current_step"] = "detect_conflicts"
        
    except Exception as e:
        logger.error(f"Error analyzing calendar: {e}")
        state["error_count"] += 1
        
    return state

def detect_conflicts_node(state: AgentState) -> AgentState:
    """Detect scheduling conflicts and other issues"""
    logger.info("Detecting conflicts...")
    
    try:
        # Use directly imported conflict_detector or import if needed
        if conflict_detector is None:
            from services import conflict_detector as conflict_service
        else:
            conflict_service = conflict_detector
        detect_all_conflicts = conflict_service.detect_all_conflicts
        
        conflicts = detect_all_conflicts(
            emails=state["emails"],
            calendar_events=state["calendar_events"]
        )
        
        state["conflicts"] = conflicts
        
        # Determine if user input is needed
        critical_conflicts = [c for c in conflicts if c["severity"] in ["high", "critical"]]
        if critical_conflicts or len(state["important_items"]) > 0:
            state["needs_user_input"] = True
            state["current_step"] = "prepare_user_interaction"
        else:
            state["current_step"] = "monitor"
            
        logger.info(f"Detected {len(conflicts)} conflicts, {len(critical_conflicts)} critical")
        
        # Log the analysis results with conflicts
        try:
            from services.data_logger import log_analysis_results, log_conflicts
            
            # Log comprehensive analysis
            log_analysis_results(
                emails=state["emails"],
                events=state["calendar_events"],
                conflicts=conflicts,
                log_dir="logs"
            )
            
            # Create dedicated conflict logs
            log_conflicts(
                conflicts=conflicts,
                emails=state["emails"],
                events=state["calendar_events"],
                log_dir="logs"
            )
        except Exception as log_error:
            logger.warning(f"Failed to log conflict analysis: {log_error}")
        
    except Exception as e:
        logger.error(f"Error detecting conflicts: {e}")
        state["error_count"] += 1
        
    return state

def prepare_user_interaction_node(state: AgentState) -> AgentState:
    """Prepare summary for user interaction"""
    logger.info("Preparing user interaction...")
    
    try:
        # Use directly imported notification or import if needed
        if notification is None:
            from services import notification as notification_service
        else:
            notification_service = notification
        prepare_user_summary = notification_service.prepare_user_summary
        
        summary = prepare_user_summary(
            important_items=state["important_items"],
            conflicts=state["conflicts"]
        )
        
        # Create user interaction record
        interaction = UserInteraction(
            interaction_id=f"interaction_{datetime.now().timestamp()}",
            timestamp=datetime.now(),
            query=summary["message"],
            response="",
            action_requested=summary["action_needed"],
            status="pending"
        )
        
        state["user_interactions"].append(interaction)
        state["voice_call_scheduled"] = True
        state["current_step"] = "call_user"
        
        logger.info("User interaction prepared")
        
    except Exception as e:
        logger.error(f"Error preparing user interaction: {e}")
        state["error_count"] += 1
        
    return state

def call_user_node(state: AgentState) -> AgentState:
    """Initiate voice call to user"""
    logger.info("Initiating voice call to user...")
    
    try:
        # Use directly imported notification or import if needed
        if notification is None:
            from services import notification as notification_service
        else:
            notification_service = notification
        initiate_voice_call = notification_service.initiate_voice_call
        
        latest_interaction = state["user_interactions"][-1]
        call_result = initiate_voice_call(latest_interaction["query"])
        
        if call_result["success"]:
            state["current_step"] = "process_user_response"
            logger.info("Voice call initiated successfully")
        else:
            # Fallback to other notification methods
            logger.warning("Voice call failed, using fallback notification")
            state["current_step"] = "monitor"
            
    except Exception as e:
        logger.error(f"Error calling user: {e}")
        state["error_count"] += 1
        
    return state

def process_user_response_node(state: AgentState) -> AgentState:
    """Process user's voice response and determine actions"""
    logger.info("Processing user response...")
    
    try:
        # Use directly imported services or import if needed
        if notification is None:
            from services import notification as notification_service
        else:
            notification_service = notification
            
        if model is None:
            from services import model as model_service
        else:
            model_service = model
            
        get_user_response = notification_service.get_user_response
        parse_user_intent = model_service.parse_user_intent
        
        user_response = get_user_response()
        
        if user_response:
            # Parse user intent using LLM
            intent_analysis = parse_user_intent(user_response)
            
            # Update interaction record
            latest_interaction = state["user_interactions"][-1]
            latest_interaction["response"] = user_response
            
            # Create pending actions based on user intent
            if intent_analysis.get("actions"):
                for action in intent_analysis["actions"]:
                    state["pending_actions"].append({
                        "action_id": f"action_{datetime.now().timestamp()}",
                        "type": action["type"],
                        "parameters": action["parameters"],
                        "priority": action.get("priority", "medium"),
                        "status": "pending"
                    })
                    
            state["current_step"] = "execute_actions"
            logger.info(f"User response processed, {len(intent_analysis.get('actions', []))} actions queued")
        else:
            # No response yet, continue monitoring
            state["current_step"] = "monitor"
            
    except Exception as e:
        logger.error(f"Error processing user response: {e}")
        state["error_count"] += 1
        
    return state

def execute_actions_node(state: AgentState) -> AgentState:
    """Execute pending actions based on user requests"""
    logger.info("Executing user-requested actions...")
    
    try:
        # Use directly imported scheduler or import if needed
        if scheduler is None:
            from services import scheduler as scheduler_service
        else:
            scheduler_service = scheduler
        execute_action = scheduler_service.execute_action
        
        for action in state["pending_actions"]:
            if action["status"] == "pending":
                result = execute_action(action)
                action["status"] = "completed" if result["success"] else "failed"
                
                if result["success"]:
                    logger.info(f"Successfully executed action: {action['type']}")
                else:
                    logger.error(f"Failed to execute action: {action['type']} - {result.get('error')}")
        
        state["current_step"] = "monitor"
        state["needs_user_input"] = False
        state["voice_call_scheduled"] = False
        
    except Exception as e:
        logger.error(f"Error executing actions: {e}")
        state["error_count"] += 1
        
    return state

def monitor_node(state: AgentState) -> AgentState:
    """Continue monitoring and update system state"""
    logger.info("Returning to monitoring mode...")
    
    state["last_check"] = datetime.now()
    state["current_step"] = "fetch_emails"
    
    # Reset some state for next cycle
    state["important_items"] = []
    state["needs_user_input"] = False
    
    # Clean up old completed interactions
    state["user_interactions"] = [
        interaction for interaction in state["user_interactions"]
        if interaction["status"] == "pending" or 
        (datetime.now() - interaction["timestamp"]).days < 1
    ]
    
    return state

def should_continue(state: AgentState) -> str:
    """Determine next step in the workflow"""
    current_step = state.get("current_step", "fetch_emails")
    
    # Check for errors - stop if too many errors
    if state.get("error_count", 0) > 5:
        logger.error("Too many errors, stopping workflow")
        return END
    
    # Check if monitoring should be paused
    if not state.get("monitoring_active", True):
        return END
    
    # Handle specific step transitions
    if current_step == "detect_conflicts":
        # Check if we need user interaction
        conflicts = state.get("conflicts", [])
        important_items = state.get("important_items", [])
        
        # If we have critical conflicts or important items, prepare user interaction
        if conflicts or important_items:
            return "prepare_user_interaction"
        else:
            return "monitor"
    
    elif current_step == "process_user_response":
        # Check if we have pending actions to execute
        pending_actions = state.get("pending_actions", [])
        if pending_actions:
            return "execute_actions"
        else:
            return "monitor"
    
    elif current_step == "monitor":
        # For monitoring, we end the current iteration
        # The runner will start a new iteration
        return END
    
    return current_step

# Create the main workflow graph
def create_agent_graph() -> StateGraph:
    """Create and configure the LangGraph workflow"""
    
    # Initialize the graph
    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_node("fetch_emails", fetch_emails_node)
    workflow.add_node("fetch_calendar", fetch_calendar_node)
    workflow.add_node("analyze_emails", analyze_emails_node)
    workflow.add_node("analyze_calendar", analyze_calendar_node)
    workflow.add_node("detect_conflicts", detect_conflicts_node)
    workflow.add_node("prepare_user_interaction", prepare_user_interaction_node)
    workflow.add_node("call_user", call_user_node)
    workflow.add_node("process_user_response", process_user_response_node)
    workflow.add_node("execute_actions", execute_actions_node)
    workflow.add_node("monitor", monitor_node)
    
    # Set entry point
    workflow.set_entry_point("fetch_emails")
    
    # Add edges for the workflow
    workflow.add_edge("fetch_emails", "fetch_calendar")
    workflow.add_edge("fetch_calendar", "analyze_emails")
    workflow.add_edge("analyze_emails", "analyze_calendar")
    workflow.add_edge("analyze_calendar", "detect_conflicts")
    
    # Conditional routing from detect_conflicts
    workflow.add_conditional_edges(
        "detect_conflicts",
        should_continue,
        {
            "prepare_user_interaction": "prepare_user_interaction",
            "monitor": "monitor",
            END: END
        }
    )
    
    workflow.add_edge("prepare_user_interaction", "call_user")
    workflow.add_edge("call_user", "process_user_response")
    
    # Conditional routing from process_user_response
    workflow.add_conditional_edges(
        "process_user_response",
        should_continue,
        {
            "execute_actions": "execute_actions",
            "monitor": "monitor",
            END: END
        }
    )
    
    workflow.add_edge("execute_actions", "monitor")
    
    # Monitor node ends the iteration - no loop back
    workflow.add_conditional_edges(
        "monitor",
        should_continue,
        {
            END: END
        }
    )
    
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
        conflicts=[],
        important_items=[],
        user_interactions=[],
        pending_actions=[],
        last_check=datetime.now() - timedelta(hours=1),
        monitoring_active=True,
        error_count=0,
        current_step="fetch_emails",
        needs_user_input=False,
        voice_call_scheduled=False
    )