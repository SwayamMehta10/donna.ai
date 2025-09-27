import base64
from email.mime.text import MIMEText
from google_auth import authenticate_gmail
from googleapiclient.errors import HttpError

def send_email(service, to_email, subject, body_text):
    """Send a simple text email."""
    try:
        # Create MIME message
        message = MIMEText(body_text)
        message['to'] = to_email
        message['subject'] = subject
        
        # Encode as base64url
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        
        # Send
        send_result = service.users().messages().send(
            userId='me',
            body={'raw': raw_message}
        ).execute()
        
        print(f'Email sent! Message ID: {send_result["id"]}')
        return send_result
        
    except HttpError as error:
        print(f'An error occurred: {error}')
        return None

if __name__ == '__main__':
    service = authenticate_gmail()
    send_email(service, 'recipient@example.com', 'Alert: New Email Detected!', 'You have a new important email.')