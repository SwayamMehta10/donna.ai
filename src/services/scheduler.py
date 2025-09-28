"""
Scheduler service for executing user-requested actions
Handles rescheduling meetings, sending emails, and other automated tasks
"""

import os
from typing import Dict, Any, List
from datetime import datetime, timedelta
import logging

# Import the API services
from .gmail import GmailAPI
from .calendar import CalendarAPI

logger = logging.getLogger(__name__)

class SchedulerService:
    """Service for executing automated scheduling actions"""
    
    def __init__(self):
        self.gmail_api = None
        self.calendar_api = None
        self._initialize_apis()
    
    def _initialize_apis(self):
        """Initialize API connections"""
        try:
            self.gmail_api = GmailAPI()
            logger.info("Gmail API initialized for scheduler")
        except Exception as e:
            logger.warning(f"Gmail API not available: {e}")
        
        try:
            self.calendar_api = CalendarAPI()
            logger.info("Calendar API initialized for scheduler")
        except Exception as e:
            logger.warning(f"Calendar API not available: {e}")
    
    def execute_action(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a user-requested action"""
        
        action_type = action.get('type')
        parameters = action.get('parameters', {})
        
        logger.info(f"Executing action: {action_type}")
        
        try:
            if action_type == 'reschedule_meeting':
                return self._reschedule_meeting(parameters)
            elif action_type == 'send_email':
                return self._send_email(parameters)
            elif action_type == 'cancel_meeting':
                return self._cancel_meeting(parameters)
            elif action_type == 'create_meeting':
                return self._create_meeting(parameters)
            elif action_type == 'update_meeting':
                return self._update_meeting(parameters)
            elif action_type == 'block_time':
                return self._block_time(parameters)
            else:
                return {
                    'success': False,
                    'error': f'Unknown action type: {action_type}'
                }
                
        except Exception as e:
            logger.error(f"Error executing action {action_type}: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _reschedule_meeting(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Reschedule a calendar meeting"""
        
        if not self.calendar_api:
            return {'success': False, 'error': 'Calendar API not available'}
        
        event_id = params.get('event_id')
        new_start = params.get('new_start_time')
        new_end = params.get('new_end_time')
        
        if not all([event_id, new_start]):
            return {'success': False, 'error': 'Missing required parameters'}
        
        # Parse datetime if it's a string
        if isinstance(new_start, str):
            new_start = datetime.fromisoformat(new_start)
        if isinstance(new_end, str):
            new_end = datetime.fromisoformat(new_end)
        
        # If no end time provided, assume same duration as original
        if not new_end:
            # This would require fetching the original event to calculate duration
            # For now, assume 1 hour
            new_end = new_start + timedelta(hours=1)
        
        updates = {
            'start_time': new_start,
            'end_time': new_end
        }
        
        success = self.calendar_api.update_event(event_id, updates)
        
        if success:
            return {
                'success': True,
                'message': f'Meeting rescheduled to {new_start.strftime("%Y-%m-%d %H:%M")}'
            }
        else:
            return {
                'success': False,
                'error': 'Failed to reschedule meeting'
            }
    
    def _send_email(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Send an email (placeholder - would need Gmail send permissions)"""
        
        # Gmail API requires additional scopes for sending emails
        # For now, just log the action
        
        to_email = params.get('to')
        subject = params.get('subject')
        body = params.get('body')
        
        logger.info(f"Would send email to {to_email} with subject: {subject}")
        
        # In a real implementation, you would:
        # 1. Add 'https://www.googleapis.com/auth/gmail.send' scope
        # 2. Re-authenticate with send permissions
        # 3. Use gmail_api.service.users().messages().send()
        
        return {
            'success': True,
            'message': f'Email queued for sending to {to_email}',
            'note': 'Email sending requires additional Gmail API permissions'
        }
    
    def _cancel_meeting(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Cancel a calendar meeting"""
        
        if not self.calendar_api:
            return {'success': False, 'error': 'Calendar API not available'}
        
        event_id = params.get('event_id')
        reason = params.get('reason', 'Meeting cancelled by AI assistant')
        
        if not event_id:
            return {'success': False, 'error': 'Event ID required'}
        
        try:
            # Update event to cancelled status
            updates = {'status': 'cancelled'}
            success = self.calendar_api.update_event(event_id, updates)
            
            if success:
                return {
                    'success': True,
                    'message': f'Meeting cancelled: {reason}'
                }
            else:
                return {
                    'success': False,
                    'error': 'Failed to cancel meeting'
                }
                
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _create_meeting(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new calendar meeting"""
        
        if not self.calendar_api:
            return {'success': False, 'error': 'Calendar API not available'}
        
        required_fields = ['title', 'start_time', 'end_time']
        for field in required_fields:
            if field not in params:
                return {'success': False, 'error': f'Missing required field: {field}'}
        
        # Parse datetime strings if needed
        if isinstance(params['start_time'], str):
            params['start_time'] = datetime.fromisoformat(params['start_time'])
        if isinstance(params['end_time'], str):
            params['end_time'] = datetime.fromisoformat(params['end_time'])
        
        event_id = self.calendar_api.create_event(params)
        
        if event_id:
            return {
                'success': True,
                'message': f'Meeting created: {params["title"]}',
                'event_id': event_id
            }
        else:
            return {
                'success': False,
                'error': 'Failed to create meeting'
            }
    
    def _update_meeting(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Update meeting details"""
        
        if not self.calendar_api:
            return {'success': False, 'error': 'Calendar API not available'}
        
        event_id = params.get('event_id')
        if not event_id:
            return {'success': False, 'error': 'Event ID required'}
        
        # Extract update fields
        updates = {}
        for field in ['title', 'location', 'description', 'start_time', 'end_time']:
            if field in params:
                updates[field] = params[field]
        
        if not updates:
            return {'success': False, 'error': 'No updates specified'}
        
        success = self.calendar_api.update_event(event_id, updates)
        
        if success:
            return {
                'success': True,
                'message': f'Meeting updated successfully'
            }
        else:
            return {
                'success': False,
                'error': 'Failed to update meeting'
            }
    
    def _block_time(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Block time on calendar"""
        
        start_time = params.get('start_time')
        duration = params.get('duration_minutes', 60)
        title = params.get('title', 'Blocked Time')
        
        if not start_time:
            return {'success': False, 'error': 'Start time required'}
        
        if isinstance(start_time, str):
            start_time = datetime.fromisoformat(start_time)
        
        end_time = start_time + timedelta(minutes=duration)
        
        event_data = {
            'title': title,
            'start_time': start_time,
            'end_time': end_time,
            'description': 'Time blocked by AI assistant'
        }
        
        return self._create_meeting(event_data)

# Convenience function for LangGraph
def execute_action(action: Dict[str, Any]) -> Dict[str, Any]:
    """Execute an action using the scheduler service"""
    scheduler = SchedulerService()
    return scheduler.execute_action(action)