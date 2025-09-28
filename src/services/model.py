"""
LLM integration module for the AI Voice Agent
Handles communication with free LLM services (Ollama, Groq, etc.)
"""

import os
import json
import aiohttp
import asyncio
import time
from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)

class LLMService:
    """Service for interacting with free LLM providers"""
    
    def __init__(self):
        self.provider = os.getenv('LLM_PROVIDER', 'groq')
        self.model = os.getenv('LLM_MODEL', 'llama-3.1-8b-instant')
        self.api_url = os.getenv('LLM_API_URL', 'http://localhost:11434')
        self.api_key = os.getenv('LLM_API_KEY', '')
        
        # Rate limiter for Groq API (6000 tokens per minute = ~100 tokens per second)
        self.last_call_time = 0
        self.min_interval = 1.0  # Minimum 1 second between calls
        self.max_retries = 3     # Maximum retries on rate limit errors
        
        logger.info(f"LLM Service initialized: {self.provider} - {self.model}")
    
    async def analyze_email(self, email_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze a single email for importance and required actions"""
        
        prompt = f"""
        Analyze this email and provide a JSON response with the following fields:
        - importance_score: float (0.0 to 1.0, where 1.0 is most important)
        - requires_action: boolean
        - action_type: string (one of: "reply", "schedule", "urgent", "delegate", "archive", null)
        - urgency: string (one of: "low", "medium", "high", "critical")
        - summary: string (brief summary of email content)
        - suggested_action: string (what action to take, if any)
        
        Email Details:
        From: {email_data.get('sender', 'Unknown')}
        Subject: {email_data.get('subject', 'No Subject')}
        Body: {email_data.get('body', '')[:500]}...
        
        Consider factors like:
        - Sender importance (boss, client, family)
        - Subject urgency keywords (urgent, asap, deadline)
        - Content requesting meetings, decisions, or immediate response
        - Time-sensitive information
        """
        
        response = await self._call_llm(prompt)
        
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            # Fallback parsing if JSON is malformed
            return self._parse_email_fallback(email_data, response)
    
    async def analyze_calendar_event(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze a calendar event for importance"""
        
        prompt = f"""
        Analyze this calendar event and provide a JSON response with:
        - importance_score: float (0.0 to 1.0)
        - requires_action: boolean
        - action_type: string (one of: "prepare", "attend", "present", "organize", null)
        - urgency: string ("low", "medium", "high", "critical")
        - summary: string (brief description)
        - suggested_action: string (any recommendations)
        
        Event Details:
        Title: {event_data.get('title', 'Untitled')}
        Start: {event_data.get('start_time', '')}
        Duration: {(event_data.get('end_time', event_data.get('start_time', '')) - event_data.get('start_time', '')).total_seconds() / 3600 if event_data.get('end_time') and event_data.get('start_time') else 'Unknown'} hours
        Attendees: {len(event_data.get('attendees', []))} people
        Location: {event_data.get('location', 'Not specified')}
        Description: {event_data.get('description', '')[:200]}...
        
        Consider:
        - Meeting with executives, clients, or large groups
        - Recurring vs one-time meetings
        - External vs internal attendees
        - Meeting location and travel requirements
        - Keywords in title/description like "URGENT", "CRITICAL", "Review"
        """
        
        response = await self._call_llm(prompt)
        
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            return self._parse_calendar_fallback(event_data, response)
    
    async def parse_user_intent(self, user_response: str) -> Dict[str, Any]:
        """Parse user response for actions and intent"""
        
        prompt = f"""
        Parse this user response and extract actionable items. Provide JSON with:
        - intent: string (main intent: "reschedule", "cancel", "confirm", "delegate", "more_info")
        - confidence: float (0.0 to 1.0)
        - actions: array of action objects with:
          - type: string (action type)
          - parameters: object (action parameters)
          - priority: string ("low", "medium", "high")
        
        User Response: "{user_response}"
        
        Examples of actions:
        - reschedule_meeting: {{"event_id": "...", "new_time": "..."}}
        - send_email: {{"to": "...", "subject": "...", "body": "..."}}
        - cancel_meeting: {{"event_id": "...", "reason": "..."}}
        - create_reminder: {{"text": "...", "time": "..."}}
        """
        
        response = await self._call_llm(prompt)
        
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            return self._parse_intent_fallback(user_response)
    
    async def _call_llm(self, prompt: str) -> str:
        """Call the configured LLM service"""
        
        if self.provider == 'ollama':
            return await self._call_ollama(prompt)
        elif self.provider == 'groq':
            return await self._call_groq(prompt)
        elif self.provider == 'openai-compatible':
            return await self._call_openai_compatible(prompt)
        else:
            raise ValueError(f"Unknown LLM provider: {self.provider}")
    
    async def _call_ollama(self, prompt: str) -> str:
        """Call Ollama API"""
        
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.api_url}/api/generate",
                    json=payload,
                    timeout=60
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result.get('response', '')
                    else:
                        raise Exception(f"Ollama API error: {response.status}")
                        
        except Exception as e:
            logger.error(f"Ollama API call failed: {e}")
            raise
    
    async def _call_groq(self, prompt: str) -> str:
        """Call Groq API with rate limiting"""
        
        if not self.api_key:
            raise ValueError("Groq API key not provided")
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "model": self.model or "llama-3.1-8b-instant",
            "temperature": 0.1,
            # Use a smaller max_tokens value to stay within rate limits
            "max_tokens": 800
        }
        
        # Implement rate limiting
        current_time = time.time()
        time_since_last_call = current_time - self.last_call_time
        if time_since_last_call < self.min_interval:
            wait_time = self.min_interval - time_since_last_call
            logger.info(f"Rate limiting: Waiting {wait_time:.2f}s before next Groq API call")
            await asyncio.sleep(wait_time)
        
        # Update last call time
        self.last_call_time = time.time()
        
        # Try with retries
        for attempt in range(self.max_retries + 1):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        "https://api.groq.com/openai/v1/chat/completions",
                        headers=headers,
                        json=payload,
                        timeout=60
                    ) as response:
                        if response.status == 200:
                            result = await response.json()
                            return result['choices'][0]['message']['content']
                        elif response.status == 429:  # Rate limit error
                            error_text = await response.text()
                            logger.warning(f"Groq API rate limit hit (attempt {attempt+1}/{self.max_retries+1}): {error_text}")
                            
                            if attempt < self.max_retries:
                                # Exponential backoff with jitter
                                backoff_time = (2 ** attempt) + (0.1 * attempt)
                                logger.info(f"Backing off for {backoff_time:.2f}s before retry")
                                await asyncio.sleep(backoff_time)
                                continue
                            else:
                                raise Exception(f"Groq API rate limit exceeded after {self.max_retries} retries")
                        else:
                            error_text = await response.text()
                            raise Exception(f"Groq API error: {response.status} - {error_text}")
            except aiohttp.ClientError as e:
                logger.error(f"Groq API network error (attempt {attempt+1}/{self.max_retries+1}): {e}")
                if attempt < self.max_retries:
                    await asyncio.sleep(1)
                    continue
                raise
            except Exception as e:
                logger.error(f"Groq API call failed: {e}")
                raise
    
    async def _call_openai_compatible(self, prompt: str) -> str:
        """Call OpenAI-compatible API"""
        
        headers = {
            "Content-Type": "application/json"
        }
        
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        payload = {
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "model": self.model,
            "temperature": 0.1
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.api_url}/v1/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=60
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result['choices'][0]['message']['content']
                    else:
                        error_text = await response.text()
                        raise Exception(f"API error: {response.status} - {error_text}")
                        
        except Exception as e:
            logger.error(f"OpenAI-compatible API call failed: {e}")
            raise
    
    def _parse_email_fallback(self, email_data: Dict, response: str) -> Dict[str, Any]:
        """Fallback email parsing when JSON parsing fails"""
        
        # Simple heuristic-based analysis
        subject = email_data.get('subject', '').lower()
        sender = email_data.get('sender', '').lower()
        body = email_data.get('body', '').lower()
        
        # Check for urgency keywords
        urgent_keywords = ['urgent', 'asap', 'immediate', 'emergency', 'deadline']
        importance_score = 0.3  # baseline
        
        if any(keyword in subject or keyword in body for keyword in urgent_keywords):
            importance_score += 0.4
        
        if 'meeting' in body or 'schedule' in body:
            importance_score += 0.2
        
        # Check sender patterns (simplified)
        if any(domain in sender for domain in ['boss', 'ceo', 'director']):
            importance_score += 0.3
        
        return {
            'importance_score': min(importance_score, 1.0),
            'requires_action': importance_score > 0.6,
            'action_type': 'reply' if importance_score > 0.6 else None,
            'urgency': 'high' if importance_score > 0.8 else 'medium' if importance_score > 0.5 else 'low',
            'summary': f"Email from {email_data.get('sender', 'unknown')} about {subject[:50]}",
            'suggested_action': 'Review and respond' if importance_score > 0.6 else None
        }
    
    def _parse_calendar_fallback(self, event_data: Dict, response: str) -> Dict[str, Any]:
        """Fallback calendar parsing"""
        
        attendee_count = len(event_data.get('attendees', []))
        title = event_data.get('title', '').lower()
        description = event_data.get('description', '').lower()
        
        importance_score = 0.4  # baseline
        
        if attendee_count > 5:
            importance_score += 0.3
        
        requires_action = False
        action_type = None
        
        # Check for urgent keywords
        urgent_keywords = ['urgent', 'critical', 'important', 'deadline', 'executive']
        if any(word in title or word in description for word in urgent_keywords):
            importance_score += 0.4
            requires_action = True
            action_type = 'prepare'
        
        if any(word in title for word in ['meeting', 'review', 'standup', 'sync']):
            importance_score += 0.2
            requires_action = True
            action_type = 'attend'
        
        if 'present' in title or 'presentation' in title:
            importance_score += 0.3
            requires_action = True
            action_type = 'present'
        
        return {
            'importance_score': min(importance_score, 1.0),
            'requires_action': requires_action,
            'action_type': action_type,
            'urgency': 'high' if importance_score > 0.8 else 'medium' if importance_score > 0.5 else 'low',
            'summary': f"Meeting: {event_data.get('title', 'Untitled')} with {attendee_count} attendees",
            'suggested_action': 'Prepare meeting materials' if requires_action else None
        }
    
    def _parse_intent_fallback(self, user_response: str) -> Dict[str, Any]:
        """Fallback intent parsing"""
        
        response_lower = user_response.lower()
        
        # Simple keyword matching
        if any(word in response_lower for word in ['reschedule', 'move', 'change time']):
            return {
                'intent': 'reschedule',
                'confidence': 0.7,
                'actions': [{
                    'type': 'reschedule_meeting',
                    'parameters': {},
                    'priority': 'medium'
                }]
            }
        
        if any(word in response_lower for word in ['cancel', 'delete', 'remove']):
            return {
                'intent': 'cancel',
                'confidence': 0.7,
                'actions': [{
                    'type': 'cancel_meeting',
                    'parameters': {},
                    'priority': 'medium'
                }]
            }
        
        return {
            'intent': 'unclear',
            'confidence': 0.3,
            'actions': []
        }

# Global LLM service instance
_llm_service = None

def get_llm_service() -> LLMService:
    """Get or create LLM service instance"""
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service

# Convenience functions for LangGraph nodes
async def analyze_email_batch(emails: List[Dict]) -> List[Dict[str, Any]]:
    """Analyze a batch of emails"""
    service = get_llm_service()
    results = []
    
    for email in emails:
        try:
            result = await service.analyze_email(email)
            results.append(result)
        except Exception as e:
            logger.error(f"Error analyzing email {email.get('id')}: {e}")
            # Provide fallback result
            results.append(service._parse_email_fallback(email, ""))
    
    return results

async def analyze_calendar_batch(events: List[Dict]) -> List[Dict[str, Any]]:
    """Analyze a batch of calendar events"""
    service = get_llm_service()
    results = []
    
    for event in events:
        try:
            result = await service.analyze_calendar_event(event)
            results.append(result)
        except Exception as e:
            logger.error(f"Error analyzing event {event.get('id')}: {e}")
            # Provide fallback result
            results.append(service._parse_calendar_fallback(event, ""))
    
    return results

async def parse_user_intent(user_response: str) -> Dict[str, Any]:
    """Parse user intent from response"""
    service = get_llm_service()
    try:
        return await service.parse_user_intent(user_response)
    except Exception as e:
        logger.error(f"Error parsing user intent: {e}")
        return service._parse_intent_fallback(user_response)