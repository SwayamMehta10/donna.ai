"""
Data logging utilities for debugging the AI Voice Agent
Creates detailed logs of fetched emails and calendar events
"""

import json
import os
from datetime import datetime
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

def log_fetched_emails(emails: List[Dict[str, Any]], log_dir: str = "logs"):
    """Log fetched emails to a JSON file for debugging"""
    try:
        # Ensure logs directory exists
        os.makedirs(log_dir, exist_ok=True)
        
        # Create filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = os.path.join(log_dir, f"fetched_emails_{timestamp}.json")
        
        # Prepare data for logging
        log_data = {
            "fetch_time": datetime.now().isoformat(),
            "total_emails": len(emails),
            "emails": []
        }
        
        for email in emails:
            email_log = {
                "id": email.get("id", "unknown"),
                "subject": email.get("subject", "No Subject"),
                "sender": email.get("sender", "Unknown Sender"),
                "timestamp": email.get("timestamp", "").isoformat() if hasattr(email.get("timestamp", ""), 'isoformat') else str(email.get("timestamp", "")),
                "body_preview": email.get("body", "")[:200] + "..." if len(email.get("body", "")) > 200 else email.get("body", ""),
                "body_length": len(email.get("body", "")),
                "importance_score": email.get("importance_score", 0.0),
                "requires_action": email.get("requires_action", False),
                "action_type": email.get("action_type")
            }
            log_data["emails"].append(email_log)
        
        # Write to file
        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump(log_data, f, indent=2, ensure_ascii=False, default=str)
        
        logger.info(f"📧 Logged {len(emails)} emails to: {log_file}")
        print(f"📧 EMAIL LOG: {len(emails)} emails logged to {log_file}")
        
        # Also create a simple text summary
        summary_file = os.path.join(log_dir, f"email_summary_{timestamp}.txt")
        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write(f"=== EMAIL FETCH SUMMARY ===\n")
            f.write(f"Fetch Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Total Emails: {len(emails)}\n\n")
            
            for i, email in enumerate(emails, 1):
                f.write(f"Email #{i}:\n")
                f.write(f"  From: {email.get('sender', 'Unknown')}\n")
                f.write(f"  Subject: {email.get('subject', 'No Subject')}\n")
                f.write(f"  Time: {email.get('timestamp', 'Unknown')}\n")
                f.write(f"  Body Preview: {email.get('body', '')[:100]}...\n")
                f.write("-" * 50 + "\n")
        
        print(f"📄 EMAIL SUMMARY: {summary_file}")
        
    except Exception as e:
        logger.error(f"Error logging emails: {e}")
        print(f"❌ Error logging emails: {e}")

def log_fetched_calendar_events(events: List[Dict[str, Any]], log_dir: str = "logs"):
    """Log fetched calendar events to a JSON file for debugging"""
    try:
        # Debug logging to trace the issue
        logger.debug(f"Logging {len(events)} calendar events")
        for i, event in enumerate(events):
            logger.debug(f"Event {i+1} type: {type(event)}")
            if isinstance(event, dict):
                logger.debug(f"Event {i+1} keys: {list(event.keys())}")
                logger.debug(f"Event {i+1} attendees type: {type(event.get('attendees', []))}")
                if 'attendees' in event and isinstance(event['attendees'], list) and event['attendees']:
                    logger.debug(f"First attendee type: {type(event['attendees'][0])}")
        
        # Ensure logs directory exists
        os.makedirs(log_dir, exist_ok=True)
        
        # Create filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = os.path.join(log_dir, f"fetched_calendar_{timestamp}.json")
        
        # Prepare data for logging
        log_data = {
            "fetch_time": datetime.now().isoformat(),
            "total_events": len(events),
            "events": []
        }
        
        for event in events:
            # Handle both dictionary and string event formats
            if isinstance(event, dict):
                # Handle attendees that may be either a list of emails (strings) or a list of attendee objects
                attendees_list = event.get("attendees", [])
                if isinstance(attendees_list, list):
                    # Check the type of the first attendee to determine format
                    if attendees_list and isinstance(attendees_list[0], dict):
                        attendees_emails = [att.get("email", "unknown") for att in attendees_list]
                    else:
                        # Already a list of email strings
                        attendees_emails = attendees_list
                else:
                    attendees_emails = []
                
                event_log = {
                    "id": event.get("id", "unknown"),
                    "title": event.get("title", "No Title"),
                    "start_time": event.get("start_time", "").isoformat() if hasattr(event.get("start_time", ""), 'isoformat') else str(event.get("start_time", "")),
                    "end_time": event.get("end_time", "").isoformat() if hasattr(event.get("end_time", ""), 'isoformat') else str(event.get("end_time", "")),
                    "attendees": attendees_emails,
                    "attendee_count": len(attendees_emails),
                    "description": event.get("description", "")[:200] + "..." if len(str(event.get("description", ""))) > 200 else str(event.get("description", "")),
                    "location": event.get("location", ""),
                    "importance_score": event.get("importance_score", 0.0),
                    "requires_action": event.get("requires_action", False),
                    "action_type": event.get("action_type"),
                    "urgency": event.get("urgency", "medium"),
                    "suggested_action": event.get("suggested_action")
                }
            else:
                # For non-dict events, create a simplified log entry
                event_log = {
                    "id": "unknown",
                    "title": str(event)[:50],
                    "raw_data": str(event)
                }
            log_data["events"].append(event_log)
        
        # Write to file
        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump(log_data, f, indent=2, ensure_ascii=False, default=str)
        
        logger.info(f"📅 Logged {len(events)} calendar events to: {log_file}")
        print(f"📅 CALENDAR LOG: {len(events)} events logged to {log_file}")
        
        # Also create a simple text summary
        summary_file = os.path.join(log_dir, f"calendar_summary_{timestamp}.txt")
        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write(f"=== CALENDAR FETCH SUMMARY ===\n")
            f.write(f"Fetch Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Total Events: {len(events)}\n\n")
            
            # Process each event inside the with block to keep file open
            for i, event in enumerate(events, 1):
                try:
                    if isinstance(event, dict):
                        title = event.get('title', 'No Title')
                        start_time = event.get('start_time', 'Unknown')
                        end_time = event.get('end_time', 'Unknown')
                        attendees = event.get('attendees', [])
                        location = event.get('location', 'None')
                    else:
                        title = str(event)[:50]
                        start_time = 'Unknown'
                        end_time = 'Unknown'
                        attendees = []
                        location = 'None'
                    
                    # Handle attendees count safely
                    if isinstance(attendees, list):
                        attendee_count = len(attendees)
                    else:
                        attendee_count = 0
                        
                    f.write(f"Event #{i}:\n")
                    f.write(f"  Title: {title}\n")
                    f.write(f"  Start: {start_time}\n")
                    f.write(f"  End: {end_time}\n")
                    f.write(f"  Attendees: {attendee_count}\n")
                    f.write(f"  Location: {location}\n")
                    f.write("-" * 50 + "\n")
                except Exception as e:
                    f.write(f"Error processing event #{i}: {str(e)}\n")
                
        print(f"📄 CALENDAR SUMMARY: {summary_file}")
        
    except Exception as e:
        logger.error(f"Error logging calendar events: {str(e)}")
        logger.error(f"Event data type: {type(events)}")
        if events:
            logger.error(f"First event type: {type(events[0])}")
            if isinstance(events[0], dict):
                logger.error(f"First event keys: {list(events[0].keys())}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        print(f"❌ Error logging calendar events: {e}")

def log_analysis_results(emails: List[Dict], events: List[Dict], conflicts: List[Dict] = None, log_dir: str = "logs"):
    """Log analysis results for debugging"""
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        analysis_file = os.path.join(log_dir, f"analysis_results_{timestamp}.txt")
        
        with open(analysis_file, 'w', encoding='utf-8') as f:
            f.write(f"=== ANALYSIS RESULTS ===\n")
            f.write(f"Analysis Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            # Email Analysis Section
            f.write(f"EMAIL ANALYSIS:\n")
            high_importance_emails = [e for e in emails if e.get('importance_score', 0) > 0.7]
            requiring_action_emails = [e for e in emails if e.get('requires_action', False)]
            
            f.write(f"  Total Emails: {len(emails)}\n")
            f.write(f"  High Importance: {len(high_importance_emails)}\n")
            f.write(f"  Requiring Action: {len(requiring_action_emails)}\n\n")
            
            # List all emails with their analysis details
            f.write(f"  Detailed Email Analysis:\n")
            sorted_emails = sorted(emails, key=lambda x: x.get('importance_score', 0), reverse=True)
            
            for i, email in enumerate(sorted_emails):
                f.write(f"  {i+1}. {email.get('subject', 'No Subject')}\n")
                f.write(f"     From: {email.get('sender', 'Unknown')}\n")
                f.write(f"     Importance: {email.get('importance_score', 0):.2f}\n")
                f.write(f"     Requires Action: {email.get('requires_action', False)}\n")
                f.write(f"     Action Type: {email.get('action_type', 'None')}\n")
                f.write(f"     Urgency: {email.get('urgency', 'Not specified')}\n")
                if email.get('suggested_action'):
                    f.write(f"     Recommendation: {email.get('suggested_action')}\n")
                f.write("\n")
            
            # Calendar Analysis Section
            f.write(f"\nCALENDAR ANALYSIS:\n")
            important_events = [e for e in events if e.get('importance_score', 0) > 0.6]
            action_required_events = [e for e in events if e.get('requires_action', False)]
            
            f.write(f"  Total Events: {len(events)}\n")
            f.write(f"  Important Events: {len(important_events)}\n")
            f.write(f"  Events Requiring Action: {len(action_required_events)}\n\n")
            
            # List all events with their analysis details
            f.write(f"  Detailed Calendar Analysis:\n")
            sorted_events = sorted(events, key=lambda x: x.get('importance_score', 0), reverse=True)
            
            for i, event in enumerate(sorted_events):
                f.write(f"  {i+1}. {event.get('title', 'No Title')}\n")
                f.write(f"     Time: {event.get('start_time', 'Unknown')}\n")
                f.write(f"     Location: {event.get('location', 'Not specified')}\n")
                f.write(f"     Attendees: {len(event.get('attendees', []))}\n")
                f.write(f"     Importance: {event.get('importance_score', 0):.2f}\n")
                f.write(f"     Requires Action: {event.get('requires_action', False)}\n")
                f.write(f"     Action Type: {event.get('action_type', 'None')}\n")
                f.write(f"     Urgency: {event.get('urgency', 'Not specified')}\n")
                if event.get('suggested_action'):
                    f.write(f"     Recommendation: {event.get('suggested_action')}\n")
                f.write("\n")
            
            # Conflict Analysis Section
            if conflicts:
                f.write(f"\nCONFLICT ANALYSIS:\n")
                f.write(f"  Total Conflicts: {len(conflicts)}\n")
                
                # Categorize conflicts by type and severity
                scheduling_conflicts = [c for c in conflicts if c.get('type') == 'scheduling']
                travel_conflicts = [c for c in conflicts if c.get('type') == 'travel_time']
                priority_conflicts = [c for c in conflicts if c.get('type') == 'priority']
                critical_conflicts = [c for c in conflicts if c.get('severity', '') in ['high', 'critical']]
                
                f.write(f"  Scheduling Conflicts: {len(scheduling_conflicts)}\n")
                f.write(f"  Travel Time Conflicts: {len(travel_conflicts)}\n")
                f.write(f"  Priority Conflicts: {len(priority_conflicts)}\n")
                f.write(f"  Critical Conflicts: {len(critical_conflicts)}\n\n")
                
                # List all conflicts with their details
                f.write(f"  Detailed Conflict Analysis:\n")
                for i, conflict in enumerate(conflicts):
                    f.write(f"  {i+1}. Conflict Type: {conflict.get('type', 'Unknown')}\n")
                    f.write(f"     Severity: {conflict.get('severity', 'Unknown')}\n")
                    
                    if conflict.get('events_involved'):
                        event_titles = []
                        for event_id in conflict.get('events_involved', []):
                            for event in events:
                                if event.get('id') == event_id:
                                    event_titles.append(event.get('title', 'Unknown Event'))
                        f.write(f"     Events: {', '.join(event_titles)}\n")
                    
                    if conflict.get('emails_involved'):
                        email_subjects = []
                        for email_id in conflict.get('emails_involved', []):
                            for email in emails:
                                if email.get('id') == email_id:
                                    email_subjects.append(email.get('subject', 'Unknown Email'))
                        f.write(f"     Emails: {', '.join(email_subjects)}\n")
                    
                    f.write(f"     Suggested Action: {conflict.get('suggested_action', 'None')}\n")
                    
                    # Include additional conflict details if available
                    if conflict.get('details'):
                        for key, value in conflict.get('details', {}).items():
                            f.write(f"     {key}: {value}\n")
                    
                    f.write("\n")
        
        print(f"🔍 ANALYSIS LOG: {analysis_file}")
        
    except Exception as e:
        logger.error(f"Error logging analysis results: {e}")
        print(f"❌ Error logging analysis results: {e}")

def log_conflicts(conflicts: List[Dict], emails: List[Dict], events: List[Dict], log_dir: str = "logs"):
    """Log detected conflicts to a JSON file for debugging"""
    if not conflicts:
        logger.info("No conflicts to log")
        return
        
    try:
        # Ensure logs directory exists
        os.makedirs(log_dir, exist_ok=True)
        
        # Create filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = os.path.join(log_dir, f"detected_conflicts_{timestamp}.json")
        
        # Create a dictionary mapping IDs to titles for easy reference
        email_map = {e.get('id', 'unknown'): e.get('subject', 'No Subject') for e in emails}
        event_map = {e.get('id', 'unknown'): e.get('title', 'No Title') for e in events}
        
        # Prepare data for logging
        conflict_logs = []
        
        for conflict in conflicts:
            # Create a detailed conflict log
            conflict_log = {
                "conflict_id": conflict.get("conflict_id", "unknown"),
                "type": conflict.get("type", "unknown"),
                "severity": conflict.get("severity", "unknown"),
                "suggested_action": conflict.get("suggested_action", ""),
                "events_involved": [],
                "emails_involved": [],
                "details": conflict.get("details", {})
            }
            
            # Add event details
            for event_id in conflict.get("events_involved", []):
                if event_id in event_map:
                    conflict_log["events_involved"].append({
                        "id": event_id,
                        "title": event_map[event_id]
                    })
            
            # Add email details
            for email_id in conflict.get("emails_involved", []):
                if email_id in email_map:
                    conflict_log["emails_involved"].append({
                        "id": email_id,
                        "subject": email_map[email_id]
                    })
            
            conflict_logs.append(conflict_log)
        
        # Write to JSON file
        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "total_conflicts": len(conflicts),
                "conflicts": conflict_logs
            }, f, indent=2, ensure_ascii=False, default=str)
        
        logger.info(f"⚠️ Logged {len(conflicts)} conflicts to: {log_file}")
        print(f"⚠️ CONFLICT LOG: {len(conflicts)} conflicts logged to {log_file}")
        
        # Create a readable text summary
        summary_file = os.path.join(log_dir, f"conflict_summary_{timestamp}.txt")
        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write(f"=== CONFLICT DETECTION SUMMARY ===\n")
            f.write(f"Detection Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Total Conflicts: {len(conflicts)}\n\n")
            
            # Count by type and severity
            conflict_types = {}
            conflict_severities = {}
            
            for conflict in conflicts:
                conflict_type = conflict.get("type", "unknown")
                conflict_severity = conflict.get("severity", "unknown")
                
                conflict_types[conflict_type] = conflict_types.get(conflict_type, 0) + 1
                conflict_severities[conflict_severity] = conflict_severities.get(conflict_severity, 0) + 1
            
            f.write("CONFLICT TYPES:\n")
            for c_type, count in conflict_types.items():
                f.write(f"  {c_type}: {count}\n")
            
            f.write("\nCONFLICT SEVERITIES:\n")
            for severity, count in conflict_severities.items():
                f.write(f"  {severity}: {count}\n")
            
            f.write("\nDETAILED CONFLICTS:\n")
            for i, conflict in enumerate(conflicts):
                f.write(f"\nCONFLICT #{i+1}: {conflict.get('conflict_id')}\n")
                f.write(f"  Type: {conflict.get('type', 'unknown')}\n")
                f.write(f"  Severity: {conflict.get('severity', 'unknown')}\n")
                f.write(f"  Action: {conflict.get('suggested_action', '')}\n")
                
                # Show involved events
                if conflict.get("events_involved"):
                    f.write("  Events Involved:\n")
                    for event_id in conflict.get("events_involved", []):
                        event_title = event_map.get(event_id, "Unknown Event")
                        f.write(f"    - {event_title}\n")
                
                # Show involved emails
                if conflict.get("emails_involved"):
                    f.write("  Emails Involved:\n")
                    for email_id in conflict.get("emails_involved", []):
                        email_subject = email_map.get(email_id, "Unknown Email")
                        f.write(f"    - {email_subject}\n")
                
                # Show additional details if present
                if conflict.get("details"):
                    f.write("  Details:\n")
                    for key, value in conflict.get("details", {}).items():
                        f.write(f"    {key}: {value}\n")
        
        print(f"📄 CONFLICT SUMMARY: {summary_file}")
        
    except Exception as e:
        logger.error(f"Error logging conflicts: {e}")
        print(f"❌ Error logging conflicts: {e}")