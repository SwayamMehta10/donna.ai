"""
Email Drafting Service using Gemini AI
Generates professional email content based on user intent
"""

import os
import logging
from typing import Dict, Any, Optional
import google.generativeai as genai

logger = logging.getLogger(__name__)


class EmailDrafter:
    """Uses Gemini AI to draft professional emails"""

    def __init__(self, api_key: str = None):
        """Initialize Gemini AI client"""
        self.api_key = api_key or os.getenv('GEMINI_API_KEY')

        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not found in environment variables")

        # Configure Gemini
        genai.configure(api_key=self.api_key)

        # Use Gemini 2.5 Flash for speed
        self.model = genai.GenerativeModel('gemini-2.5-flash')
        logger.info("EmailDrafter initialized with Gemini 2.5 Flash")

    def draft_reply(self, original_email: Dict[str, Any], user_intent: str) -> str:
        """
        Draft a professional email reply using Gemini AI
        
        Args:
            original_email: Dict with 'sender', 'subject', 'body', 'timestamp'
            user_intent: User's casual description of what to communicate
                        Example: "tell him I'll be there and bring the reports"
        
        Returns:
            Professional email body text
        """
        try:
            sender = original_email.get('sender', 'the sender')
            subject = original_email.get('subject', 'your email')
            original_body = original_email.get('body', '')

            prompt = f"""You are drafting a professional email reply for a business professional.

ORIGINAL EMAIL:
From: {sender}
Subject: {subject}

{original_body}

---

USER'S INTENT (what they want to communicate, may be casual):
{user_intent}

---

TASK: Draft a professional email reply that:
1. Responds appropriately to the original email
2. Clearly communicates the user's intent
3. Uses professional business tone
4. Is concise (2-4 short paragraphs maximum)
5. Includes appropriate greeting (Dear/Hi [Name],) and closing (Best regards, etc.)
6. Sounds natural and human, not robotic

IMPORTANT:
- Extract the sender's first name from "{sender}" and use it in greeting
- Be direct and clear
- Don't be overly formal or use corporate jargon
- Keep it brief and actionable

Draft the email reply now (just the email body, no subject line):"""

            logger.info(f"Drafting reply with Gemini for email from {sender}")
            response = self.model.generate_content(prompt)
            drafted_reply = response.text.strip()
            
            logger.info("Successfully drafted email reply")
            return drafted_reply

        except Exception as e:
            logger.error(f"Error drafting reply with Gemini: {e}")
            # Fallback to simple template
            return self._fallback_reply(original_email, user_intent)

    def draft_new_email(self, recipient: str, subject: str, user_content: str) -> str:
        """
        Draft a professional new email using Gemini AI
        
        Args:
            recipient: Email address of recipient (e.g., "john.smith@company.com")
            subject: Email subject line
            user_content: User's casual description of what to write
                         Example: "ask him about the Q4 budget and if he needs anything"
        
        Returns:
            Professional email body text
        """
        try:
            # Extract recipient name from email
            recipient_name = recipient.split('@')[0].replace('.', ' ').title()

            prompt = f"""You are drafting a professional business email.

EMAIL DETAILS:
To: {recipient}
Subject: {subject}

USER WANTS TO COMMUNICATE (may be casual or incomplete):
{user_content}

---

TASK: Draft a professional email that:
1. Has appropriate greeting for {recipient_name}
2. Clearly communicates the user's message/request
3. Uses professional but friendly tone
4. Is concise (2-3 short paragraphs maximum)
5. Has appropriate closing (Best regards, Sincerely, etc.)
6. Sounds natural and human

IMPORTANT:
- Be direct and clear about the purpose
- Don't be overly formal - keep it conversational but professional
- If asking questions, make them clear and actionable
- Keep it brief

Draft the email body now (no subject line, just the email body):"""

            logger.info(f"Drafting new email with Gemini to {recipient}")
            response = self.model.generate_content(prompt)
            drafted_body = response.text.strip()
            
            logger.info("Successfully drafted new email")
            return drafted_body

        except Exception as e:
            logger.error(f"Error drafting new email with Gemini: {e}")
            # Fallback to simple template
            return self._fallback_new_email(recipient, user_content)

    def _fallback_reply(self, original_email: Dict[str, Any], user_intent: str) -> str:
        """Fallback reply template when Gemini fails"""
        sender_name = original_email.get('sender', 'there').split('<')[0].strip().split()[0]
        
        return f"""Hi {sender_name},

Thank you for your email. {user_intent}

Best regards"""

    def _fallback_new_email(self, recipient: str, user_content: str) -> str:
        """Fallback email template when Gemini fails"""
        recipient_name = recipient.split('@')[0].replace('.', ' ').title()
        
        return f"""Hi {recipient_name},

{user_content}

Best regards"""


# Test function
async def test_drafter():
    """Test the email drafter"""
    from dotenv import load_dotenv
    from pathlib import Path

    # Load .env from project root
    env_path = Path(__file__).resolve().parent.parent.parent / '.env'
    load_dotenv(dotenv_path=env_path)

    print(f"Loading .env from: {env_path}")
    print(f"API Key present: {bool(os.getenv('GEMINI_API_KEY'))}")

    # Test reply drafting
    original_email = {
        "sender": "John Smith <john.smith@company.com>",
        "subject": "Q1 Planning Meeting",
        "body": "Hi, we're scheduling the Q1 planning meeting for next week. Can you attend on Tuesday at 2pm? Please let me know."
    }

    user_intent = "tell him yes I'll be there and I'll bring the budget reports"

    try:
        drafter = EmailDrafter()
        
        print("\n" + "="*60)
        print("TEST: DRAFT REPLY")
        print("="*60)
        print(f"\nOriginal: {original_email['subject']}")
        print(f"User intent: {user_intent}")
        print("\nDrafted Reply:")
        print("-"*60)
        reply = drafter.draft_reply(original_email, user_intent)
        print(reply)
        
        print("\n" + "="*60)
        print("TEST: DRAFT NEW EMAIL")
        print("="*60)
        new_email = drafter.draft_new_email(
            recipient="jane.doe@company.com",
            subject="Budget Review",
            user_content="ask her if she's reviewed the budget and needs any clarifications"
        )
        print("\nDrafted New Email:")
        print("-"*60)
        print(new_email)

    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_drafter())
