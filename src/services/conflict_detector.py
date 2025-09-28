"""
Conflict detection service for the AI Voice Agent
Identifies scheduling conflicts, travel time issues, and priority conflicts
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

def detect_all_conflicts(emails: List[Dict], calendar_events: List[Dict]) -> List[Dict[str, Any]]:
    """
    Detect all types of conflicts between emails and calendar events
    
    Args:
        emails: List of EmailData dictionaries
        calendar_events: List of CalendarEvent dictionaries
    
    Returns:
        List of Conflict dictionaries
    """
    conflicts = []
    
    # Detect scheduling conflicts
    scheduling_conflicts = detect_scheduling_conflicts(calendar_events)
    conflicts.extend(scheduling_conflicts)
    
    # Detect travel time conflicts  
    travel_conflicts = detect_travel_time_conflicts(calendar_events)
    conflicts.extend(travel_conflicts)
    
    # Detect priority conflicts between important emails and events
    priority_conflicts = detect_priority_conflicts(emails, calendar_events)
    conflicts.extend(priority_conflicts)
    
    logger.info(f"Detected {len(conflicts)} total conflicts")
    return conflicts

def detect_scheduling_conflicts(calendar_events: List[Dict]) -> List[Dict[str, Any]]:
    """Detect overlapping calendar events"""
    conflicts = []
    
    # Sort events by start time
    sorted_events = sorted(calendar_events, key=lambda e: e['start_time'])
    
    for i, event1 in enumerate(sorted_events):
        for j, event2 in enumerate(sorted_events[i+1:], i+1):
            try:
                # Normalize datetime objects to handle timezone issues
                # Remove timezone info if present
                event1_start = event1['start_time'].replace(tzinfo=None) if hasattr(event1['start_time'], 'tzinfo') and event1['start_time'].tzinfo else event1['start_time']
                event1_end = event1['end_time'].replace(tzinfo=None) if hasattr(event1['end_time'], 'tzinfo') and event1['end_time'].tzinfo else event1['end_time']
                event2_start = event2['start_time'].replace(tzinfo=None) if hasattr(event2['start_time'], 'tzinfo') and event2['start_time'].tzinfo else event2['start_time']
                event2_end = event2['end_time'].replace(tzinfo=None) if hasattr(event2['end_time'], 'tzinfo') and event2['end_time'].tzinfo else event2['end_time']
                
                # Check if events overlap
                if (event1_start < event2_end and 
                    event2_start < event1_end):
                    
                    severity = determine_conflict_severity(event1, event2)
                    
                    conflict = {
                        'conflict_id': f"schedule_{event1['id']}_{event2['id']}",
                        'type': 'scheduling',
                        'events_involved': [event1['id'], event2['id']],
                        'emails_involved': [],
                        'severity': severity,
                        'suggested_action': f"Reschedule '{event2['title']}' to avoid overlap with '{event1['title']}'",
                        'user_decision': None,
                        'details': {
                            'event1': event1['title'],
                            'event2': event2['title'], 
                            'overlap_start': max(event1_start, event2_start),
                            'overlap_end': min(event1_end, event2_end)
                        }
                    }
                    conflicts.append(conflict)
            except Exception as e:
                logger.error(f"Error checking conflict between events: {str(e)}")
                
                # Don't attempt to create conflict if exception - it may cause more errors
                # Simply log it and continue
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
                logger.error(f"Skipping conflict detection for events {event1.get('id', 'unknown')} and {event2.get('id', 'unknown')}")
    
    return conflicts

def detect_travel_time_conflicts(calendar_events: List[Dict]) -> List[Dict[str, Any]]:
    """Detect insufficient travel time between events"""
    conflicts = []
    
    # Sort events by start time
    try:
        sorted_events = sorted(calendar_events, key=lambda e: e['start_time'])
        
        for i, event1 in enumerate(sorted_events[:-1]):
            try:
                event2 = sorted_events[i + 1]
                
                # Normalize datetime objects for comparison
                event1_end = event1['end_time'].replace(tzinfo=None) if hasattr(event1['end_time'], 'tzinfo') and event1['end_time'].tzinfo else event1['end_time']
                event2_start = event2['start_time'].replace(tzinfo=None) if hasattr(event2['start_time'], 'tzinfo') and event2['start_time'].tzinfo else event2['start_time']
                
                # Calculate time between events
                time_gap = (event2_start - event1_end).total_seconds() / 60
                
                # Check if different locations require travel time
                location1 = str(event1.get('location', '')).strip()
                location2 = str(event2.get('location', '')).strip()
                
                if location1 and location2 and location1 != location2:
                    # Estimate travel time (simplified logic)
                    estimated_travel = estimate_travel_time(location1, location2)
                    
                    if time_gap < estimated_travel:
                        severity = 'high' if time_gap < estimated_travel * 0.5 else 'medium'
                        
                        conflict = {
                            'conflict_id': f"travel_{event1['id']}_{event2['id']}",
                            'type': 'travel_time',
                            'events_involved': [event1['id'], event2['id']],
                            'emails_involved': [],
                            'severity': severity,
                            'suggested_action': f"Allow {estimated_travel} minutes for travel between '{event1['title']}' and '{event2['title']}'",
                            'user_decision': None,
                            'details': {
                                'from_event': event1['title'],
                                'to_event': event2['title'],
                                'from_location': location1,
                                'to_location': location2,
                                'available_time': time_gap,
                                'required_time': estimated_travel
                            }
                        }
                        conflicts.append(conflict)
            except Exception as e:
                logger.error(f"Error checking travel time between events: {e}")
    except Exception as e:
        logger.error(f"Error in travel time conflict detection: {e}")
    
    return conflicts

def detect_priority_conflicts(emails: List[Dict], calendar_events: List[Dict]) -> List[Dict[str, Any]]:
    """Detect conflicts between high-priority emails requiring action and scheduled events"""
    conflicts = []
    
    # Find urgent emails that need immediate action
    urgent_emails = [
        email for email in emails 
        if (email.get('importance_score', 0) > 0.7 or 
            email.get('urgency') in ['high', 'critical']) and 
        email.get('requires_action', False)
    ]
    
    # Find important events happening soon
    now = datetime.now()
    soon_threshold = now + timedelta(hours=2)
    
    upcoming_events = [
        event for event in calendar_events
        if now <= event['start_time'] <= soon_threshold and
        (event.get('importance_score', 0) > 0.7 or 
         event.get('urgency') in ['high', 'critical'] or 
         event.get('requires_action', False))
    ]
    
    for email in urgent_emails:
        for event in upcoming_events:
            # Check if the urgent email action might conflict with the event
            time_until_event = (event['start_time'] - now).total_seconds() / 60
            
            if time_until_event < 30:  # Less than 30 minutes
                conflict = {
                    'conflict_id': f"priority_{email['id']}_{event['id']}",
                    'type': 'priority',
                    'events_involved': [event['id']],
                    'emails_involved': [email['id']],
                    'severity': 'critical' if time_until_event < 15 else 'high',
                    'suggested_action': f"Handle urgent email from {email['sender']} before attending '{event['title']}'",
                    'user_decision': None,
                    'details': {
                        'email_subject': email['subject'],
                        'email_sender': email['sender'],
                        'email_importance': email.get('importance_score', 0),
                        'email_urgency': email.get('urgency', 'medium'),
                        'email_action_type': email.get('action_type', 'review'),
                        'event_title': event['title'],
                        'event_importance': event.get('importance_score', 0),
                        'event_urgency': event.get('urgency', 'medium'),
                        'time_until_event': time_until_event
                    }
                }
                conflicts.append(conflict)
    
    return conflicts

def determine_conflict_severity(event1: Dict, event2: Dict) -> str:
    """Determine the severity of a scheduling conflict"""
    # Check for complete overlap
    overlap_duration = min(event1['end_time'], event2['end_time']) - max(event1['start_time'], event2['start_time'])
    event1_duration = event1['end_time'] - event1['start_time']
    event2_duration = event2['end_time'] - event2['start_time']
    
    # Calculate overlap percentage
    overlap_pct1 = overlap_duration / event1_duration
    overlap_pct2 = overlap_duration / event2_duration
    max_overlap_pct = max(overlap_pct1, overlap_pct2)
    
    # Determine severity based on overlap and importance
    if max_overlap_pct > 0.8:
        return 'critical'
    elif max_overlap_pct > 0.5:
        return 'high'
    elif max_overlap_pct > 0.2:
        return 'medium'
    else:
        return 'low'

def estimate_travel_time(location1: str, location2: str) -> int:
    """
    Estimate travel time between two locations (simplified implementation)
    Returns estimated time in minutes
    """
    # Simplified logic - in a real implementation, you might use Google Maps API
    
    # Check for keywords that indicate travel time
    location1_lower = location1.lower()
    location2_lower = location2.lower()
    
    # Same building/floor
    if any(word in location1_lower and word in location2_lower 
           for word in ['room', 'floor', 'building']):
        return 5
    
    # Different buildings but same area
    if any(word in location1_lower and word in location2_lower
           for word in ['campus', 'office', 'center', 'complex']):
        return 15
    
    # Different areas in same city
    if any(word in location1_lower and word in location2_lower
           for word in ['street', 'avenue', 'road', 'blvd']):
        return 30
    
    # Default for different locations
    return 45

def get_conflict_recommendations(conflict: Dict[str, Any]) -> List[str]:
    """Get specific recommendations for resolving a conflict"""
    recommendations = []
    
    if conflict['type'] == 'scheduling':
        recommendations.extend([
            "Move one event to a different time slot",
            "Shorten the duration of one or both events",
            "Delegate attendance to another team member",
            "Convert one meeting to asynchronous communication"
        ])
    
    elif conflict['type'] == 'travel_time':
        recommendations.extend([
            "Reschedule one event to allow travel time",
            "Change one meeting to virtual/remote",
            "Move the meeting location closer",
            "Use faster transportation method"
        ])
    
    elif conflict['type'] == 'priority':
        recommendations.extend([
            "Handle urgent email before the meeting",
            "Delegate email response to team member",
            "Postpone meeting if email is more critical",
            "Quick response to email, detailed follow-up later"
        ])
    
    return recommendations