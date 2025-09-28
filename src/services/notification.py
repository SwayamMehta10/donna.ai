"""
Notification service for voice calls and user interactions
Handles calling users and managing responses
"""

import os
from typing import Dict, Any, Optional
from datetime import datetime
import logging

# Import voice/phone services
try:
    from twilio.rest import Client as TwilioClient
    TWILIO_AVAILABLE = True
except ImportError:
    TWILIO_AVAILABLE = False

logger = logging.getLogger(__name__)

class NotificationService:
    """Service for handling user notifications and voice calls"""
    
    def __init__(self):
        self.twilio_client = None
        self.user_phone = os.getenv('USER_PHONE_NUMBER')
        self.from_phone = os.getenv('TWILIO_PHONE_NUMBER')
        
        if TWILIO_AVAILABLE:
            account_sid = os.getenv('TWILIO_ACCOUNT_SID')
            auth_token = os.getenv('TWILIO_AUTH_TOKEN')
            
            if account_sid and auth_token:
                self.twilio_client = TwilioClient(account_sid, auth_token)
                logger.info("Twilio client initialized")
            else:
                logger.warning("Twilio credentials not found in environment")
        else:
            logger.warning("Twilio not available - install with: pip install twilio")
    
    def prepare_user_summary(self, important_items: list, conflicts: list) -> Dict[str, Any]:
        """Prepare a summary for user notification"""
        
        # Count critical items
        critical_conflicts = [c for c in conflicts if c['severity'] == 'critical']
        high_priority_items = [i for i in important_items if i.get('urgency') == 'high']
        
        # Create message
        message_parts = []
        
        if critical_conflicts:
            message_parts.append(f"You have {len(critical_conflicts)} critical scheduling conflicts")
        
        if high_priority_items:
            message_parts.append(f"You have {len(high_priority_items)} high-priority items requiring attention")
        
        if len(conflicts) > len(critical_conflicts):
            other_conflicts = len(conflicts) - len(critical_conflicts)
            message_parts.append(f"You have {other_conflicts} other scheduling issues")
        
        if not message_parts:
            message_parts.append("Your schedule looks good, but I wanted to check in")
        
        message = "Hello! " + ", and ".join(message_parts) + ". "
        
        # Add specific details
        if critical_conflicts:
            first_conflict = critical_conflicts[0]
            message += f"Most urgent: {first_conflict['suggested_action']}. "
        
        if high_priority_items:
            first_item = high_priority_items[0]
            message += f"Priority item: {first_item['summary']}. "
        
        message += "How would you like me to help you?"
        
        return {
            'message': message,
            'action_needed': 'user_input_required' if (critical_conflicts or high_priority_items) else 'informational',
            'summary': {
                'total_conflicts': len(conflicts),
                'critical_conflicts': len(critical_conflicts),
                'high_priority_items': len(high_priority_items)
            }
        }
    
    def initiate_voice_call(self, message: str) -> Dict[str, Any]:
        """Initiate a voice call to the user"""
        
        if not self.twilio_client:
            return {
                'success': False,
                'error': 'Voice calling not configured',
                'fallback_used': 'console_notification'
            }
        
        if not self.user_phone or not self.from_phone:
            return {
                'success': False,
                'error': 'Phone numbers not configured',
                'fallback_used': 'console_notification'
            }
        
        try:
            # Create TwiML for the call
            twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
            <Response>
                <Say voice="alice">{message}</Say>
                <Record timeout="30" transcribe="true" transcribeCallback="/voice/transcription" />
            </Response>"""
            
            # Make the call
            call = self.twilio_client.calls.create(
                twiml=twiml,
                to=self.user_phone,
                from_=self.from_phone
            )
            
            logger.info(f"Voice call initiated: {call.sid}")
            
            return {
                'success': True,
                'call_sid': call.sid,
                'message': 'Voice call initiated successfully'
            }
            
        except Exception as e:
            logger.error(f"Failed to initiate voice call: {e}")
            
            # Fallback to console notification
            self._console_notification(message)
            
            return {
                'success': False,
                'error': str(e),
                'fallback_used': 'console_notification'
            }
    
    def _console_notification(self, message: str):
        """Fallback notification method"""
        print("\n" + "=" * 60)
        print("📞 VOICE AGENT NOTIFICATION")
        print("=" * 60)
        print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Message: {message}")
        print("=" * 60)
        print("NOTE: This would normally be delivered as a voice call")
        print("Configure Twilio credentials for actual voice calling")
        print("=" * 60 + "\n")
    
    def send_sms_notification(self, message: str) -> Dict[str, Any]:
        """Send SMS notification as alternative to voice call"""
        
        if not self.twilio_client:
            return {'success': False, 'error': 'SMS not configured'}
        
        try:
            message_obj = self.twilio_client.messages.create(
                body=message,
                from_=self.from_phone,
                to=self.user_phone
            )
            
            logger.info(f"SMS sent: {message_obj.sid}")
            
            return {
                'success': True,
                'message_sid': message_obj.sid,
                'message': 'SMS sent successfully'
            }
            
        except Exception as e:
            logger.error(f"Failed to send SMS: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_user_response(self) -> Optional[str]:
        """Get user response from voice call or input"""
        
        # In a real implementation, this would:
        # 1. Check for transcribed voice responses from Twilio
        # 2. Poll for SMS responses
        # 3. Check web interface for user input
        
        # For now, simulate getting input
        try:
            # Check if there's pending input (this would be replaced with actual voice/SMS checking)
            response = input("Enter your response (or press Enter to skip): ").strip()
            return response if response else None
            
        except (EOFError, KeyboardInterrupt):
            return None
    
    def check_voice_response(self, call_sid: str) -> Optional[str]:
        """Check for transcribed voice response from a call"""
        
        if not self.twilio_client:
            return None
        
        try:
            # Get call details
            call = self.twilio_client.calls.get(call_sid).fetch()
            
            # Check for recordings
            recordings = self.twilio_client.recordings.list(call_sid=call_sid)
            
            for recording in recordings:
                # In a real implementation, you'd process the transcription
                # For now, return a placeholder
                return "User response would be transcribed here"
            
            return None
            
        except Exception as e:
            logger.error(f"Error checking voice response: {e}")
            return None

# Convenience functions for the LangGraph nodes
def prepare_user_summary(important_items: list, conflicts: list) -> Dict[str, Any]:
    """Prepare summary for user interaction"""
    service = NotificationService()
    return service.prepare_user_summary(important_items, conflicts)

def initiate_voice_call(message: str) -> Dict[str, Any]:
    """Initiate voice call to user"""
    service = NotificationService()
    return service.initiate_voice_call(message)

def get_user_response() -> Optional[str]:
    """Get user response"""
    service = NotificationService()
    return service.get_user_response()