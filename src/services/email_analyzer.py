"""
Email Analysis using Gemini AI
Intelligently analyzes email importance, urgency, and extracts key information
"""

import os
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import json

try:
    import google.generativeai as genai
except ImportError:
    genai = None
    logging.warning("google-generativeai not installed. Install with: pip install google-generativeai")

logger = logging.getLogger(__name__)


class EmailAnalyzer:
    """Analyzes emails using Gemini AI to extract importance and actionable insights"""

    def __init__(self, api_key: str = None):
        """Initialize Gemini AI client"""
        self.api_key = api_key or os.getenv('GEMINI_API_KEY')

        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not found in environment variables")

        if genai is None:
            raise ImportError("google-generativeai package not installed")

        # Configure Gemini
        genai.configure(api_key=self.api_key)

        # Use Gemini 2.5 Flash for speed and efficiency (latest stable model)
        self.model = genai.GenerativeModel('gemini-2.5-flash')
        logger.info("EmailAnalyzer initialized with Gemini 2.5 Flash")

    def analyze_emails(self, emails: List[Dict[str, Any]], max_emails: int = 50) -> Dict[str, Any]:
        """
        Analyze a batch of emails and identify top 5 most important ones

        Args:
            emails: List of email dictionaries with subject, sender, body, timestamp
            max_emails: Maximum number of emails to analyze (to stay within token limits)

        Returns:
            Dictionary with analyzed emails and top 5 important ones
        """
        if not emails:
            return {
                "analyzed_emails": [],
                "top_5_important": [],
                "summary": "No emails to analyze"
            }

        # Limit to max_emails to avoid token limits
        emails_to_analyze = emails[:max_emails]

        try:
            # Create the analysis prompt
            prompt = self._create_analysis_prompt(emails_to_analyze)

            # Call Gemini API
            logger.info(f"Analyzing {len(emails_to_analyze)} emails with Gemini...")
            response = self.model.generate_content(prompt)

            # Parse the response
            analysis_result = self._parse_analysis_response(response.text, emails_to_analyze)

            logger.info(f"Successfully analyzed {len(emails_to_analyze)} emails")
            return analysis_result

        except Exception as e:
            logger.error(f"Error analyzing emails with Gemini: {e}")
            return self._fallback_analysis(emails_to_analyze)

    def _create_analysis_prompt(self, emails: List[Dict[str, Any]]) -> str:
        """Create a detailed prompt for email analysis"""

        # Format emails for the prompt
        email_list = []
        for idx, email in enumerate(emails, 1):
            sender = email.get('sender', 'Unknown')
            subject = email.get('subject', 'No Subject')
            body = email.get('body', '')[:500]  # Limit body to 500 chars
            timestamp = email.get('timestamp', datetime.now())

            # Format timestamp
            if isinstance(timestamp, datetime):
                time_str = timestamp.strftime('%Y-%m-%d %H:%M')
            else:
                time_str = str(timestamp)

            email_list.append(f"""
EMAIL {idx}:
From: {sender}
Subject: {subject}
Date: {time_str}
Body Preview: {body}
---""")

        emails_text = "\n".join(email_list)

        prompt = f"""You are an intelligent email assistant analyzing emails for importance and urgency.

Analyze the following {len(emails)} emails and provide a structured JSON response.

EMAILS TO ANALYZE:
{emails_text}

ANALYSIS TASK:
For each email, determine:
1. Importance score (0-10): How important is this email?
2. Urgency level (low/medium/high/critical): How urgent is a response?
3. Requires action (true/false): Does this need the user to do something?
4. Action type: One of [reply, schedule, review, urgent_response, follow_up, none]
5. Brief summary (1-2 sentences): Key points from the email
6. Suggested action: What should the user do?

IMPORTANCE SCORING CRITERIA:
- 9-10: Critical business decisions, legal matters, urgent deadlines, CEO/VIP emails
- 7-8: Important meetings, project updates, client requests, time-sensitive matters
- 5-6: Regular work communications, team updates, non-urgent requests
- 3-4: FYI emails, newsletters, automated notifications
- 1-2: Spam, promotional emails, irrelevant content

URGENCY CRITERIA:
- critical: Needs immediate response (within 1 hour)
- high: Needs response today
- medium: Needs response within 2-3 days
- low: No time pressure

Respond ONLY with valid JSON in this exact format:
{{
  "emails": [
    {{
      "email_index": 1,
      "importance_score": 8,
      "urgency": "high",
      "requires_action": true,
      "action_type": "reply",
      "summary": "Brief summary here",
      "suggested_action": "Reply to confirm attendance by EOD"
    }}
  ],
  "top_5_indices": [3, 1, 7, 2, 5],
  "overall_summary": "Brief overview of the most important themes across all emails"
}}

Provide the JSON now:"""

        return prompt

    def _parse_analysis_response(self, response_text: str, original_emails: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Parse Gemini's JSON response and merge with original emails"""

        try:
            # Extract JSON from response (handle markdown code blocks)
            response_text = response_text.strip()
            if response_text.startswith('```json'):
                response_text = response_text[7:]
            if response_text.startswith('```'):
                response_text = response_text[3:]
            if response_text.endswith('```'):
                response_text = response_text[:-3]

            response_text = response_text.strip()

            # Parse JSON
            analysis_data = json.loads(response_text)

            # Merge analysis with original emails
            analyzed_emails = []
            for email_analysis in analysis_data.get('emails', []):
                idx = email_analysis.get('email_index', 1) - 1

                if 0 <= idx < len(original_emails):
                    email = original_emails[idx].copy()
                    email.update({
                        'importance_score': email_analysis.get('importance_score', 5),
                        'urgency': email_analysis.get('urgency', 'medium'),
                        'requires_action': email_analysis.get('requires_action', False),
                        'action_type': email_analysis.get('action_type', 'none'),
                        'summary': email_analysis.get('summary', email.get('subject', '')),
                        'suggested_action': email_analysis.get('suggested_action', None)
                    })
                    analyzed_emails.append(email)

            # Get top 5 important emails
            top_5_indices = analysis_data.get('top_5_indices', [])
            top_5_important = []
            for idx in top_5_indices[:5]:
                if 1 <= idx <= len(analyzed_emails):
                    top_5_important.append(analyzed_emails[idx - 1])

            # If we didn't get top 5 from AI, sort by importance score
            if len(top_5_important) < 5:
                sorted_emails = sorted(analyzed_emails, key=lambda x: x.get('importance_score', 0), reverse=True)
                top_5_important = sorted_emails[:5]

            return {
                "analyzed_emails": analyzed_emails,
                "top_5_important": top_5_important,
                "overall_summary": analysis_data.get('overall_summary', ''),
                "total_analyzed": len(analyzed_emails),
                "high_priority_count": sum(1 for e in analyzed_emails if e.get('importance_score', 0) >= 7),
                "requires_action_count": sum(1 for e in analyzed_emails if e.get('requires_action', False))
            }

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Gemini JSON response: {e}")
            logger.debug(f"Response text: {response_text[:500]}")
            return self._fallback_analysis(original_emails)
        except Exception as e:
            logger.error(f"Error parsing analysis response: {e}")
            return self._fallback_analysis(original_emails)

    def _fallback_analysis(self, emails: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Fallback analysis when AI fails - use simple heuristics"""

        logger.warning("Using fallback heuristic analysis")

        analyzed_emails = []
        for email in emails:
            # Simple heuristics
            subject = email.get('subject', '').lower()
            sender = email.get('sender', '').lower()
            body = email.get('body', '').lower()

            # Calculate importance based on keywords
            importance_score = 5  # Default
            urgency = 'medium'
            requires_action = False

            # High priority keywords
            high_priority_keywords = ['urgent', 'important', 'asap', 'critical', 'deadline', 'ceo', 'president']
            action_keywords = ['please', 'review', 'approve', 'respond', 'confirm', 'rsvp']

            if any(kw in subject or kw in body for kw in high_priority_keywords):
                importance_score = 8
                urgency = 'high'
                requires_action = True

            if any(kw in subject or kw in body for kw in action_keywords):
                requires_action = True
                importance_score = max(importance_score, 6)

            analyzed_email = email.copy()
            analyzed_email.update({
                'importance_score': importance_score,
                'urgency': urgency,
                'requires_action': requires_action,
                'action_type': 'review' if requires_action else 'none',
                'summary': email.get('subject', 'No subject'),
                'suggested_action': 'Review and respond' if requires_action else None
            })
            analyzed_emails.append(analyzed_email)

        # Sort by importance and get top 5
        sorted_emails = sorted(analyzed_emails, key=lambda x: x.get('importance_score', 0), reverse=True)
        top_5_important = sorted_emails[:5]

        return {
            "analyzed_emails": analyzed_emails,
            "top_5_important": top_5_important,
            "overall_summary": f"Analyzed {len(emails)} emails using heuristic fallback",
            "total_analyzed": len(analyzed_emails),
            "high_priority_count": sum(1 for e in analyzed_emails if e.get('importance_score', 0) >= 7),
            "requires_action_count": sum(1 for e in analyzed_emails if e.get('requires_action', False))
        }


# Quick test function
async def test_analyzer():
    """Test the email analyzer"""

    # Load environment variables
    from dotenv import load_dotenv
    from pathlib import Path

    # Load .env from project root
    env_path = Path(__file__).resolve().parent.parent.parent / '.env'
    load_dotenv(dotenv_path=env_path)

    print(f"Loading .env from: {env_path}")
    print(f"API Key present: {bool(os.getenv('GEMINI_API_KEY'))}")

    # Sample test emails
    test_emails = [
        {
            "id": "1",
            "subject": "URGENT: Server outage needs immediate attention",
            "sender": "ops@company.com",
            "body": "Production server is down. Need immediate response.",
            "timestamp": datetime.now()
        },
        {
            "id": "2",
            "subject": "Weekly newsletter - January 2024",
            "sender": "newsletter@marketing.com",
            "body": "Check out our latest updates and news...",
            "timestamp": datetime.now()
        },
        {
            "id": "3",
            "subject": "Meeting reminder: Q1 Planning",
            "sender": "ceo@company.com",
            "body": "Please confirm your attendance for tomorrow's strategic planning meeting.",
            "timestamp": datetime.now()
        }
    ]

    try:
        analyzer = EmailAnalyzer()
        result = analyzer.analyze_emails(test_emails)

        print("\n" + "="*50)
        print("EMAIL ANALYSIS RESULTS")
        print("="*50)
        print(f"\nTotal analyzed: {result['total_analyzed']}")
        print(f"High priority: {result['high_priority_count']}")
        print(f"Requires action: {result['requires_action_count']}")

        print("\nTOP 5 IMPORTANT EMAILS:")
        for idx, email in enumerate(result['top_5_important'], 1):
            print(f"\n{idx}. {email['subject']}")
            print(f"   From: {email['sender']}")
            print(f"   Importance: {email.get('importance_score', 0)}/10")
            print(f"   Urgency: {email.get('urgency', 'unknown')}")
            print(f"   Summary: {email.get('summary', '')}")
            if email.get('suggested_action'):
                print(f"   Action: {email['suggested_action']}")

        return result

    except Exception as e:
        print(f"Test failed: {e}")
        return None


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_analyzer())
