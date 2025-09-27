from google_auth import authenticate_gmail
from googleapiclient.errors import HttpError

def fetch_emails(service, sender=None, is_read=None, is_promotional=False, is_starred=False, is_important=False, max_results=10):
    """Fetch emails based on filters like sender, read/unread, promotions, starred, or important."""
    query = []
    label_ids = ['INBOX']  # Default to inbox

    # Build query for sender
    if sender:
        query.append(f'from:{sender}')

    # Build query for read/unread
    if is_read is True:
        query.append('is:read')
    elif is_read is False:
        query.append('is:unread')
        label_ids.append('UNREAD')  # Optional: Use label for efficiency

    # Promotional emails
    if is_promotional:
        query.append('category:promotions')
        label_ids.append('CATEGORY_PROMOTIONS')

    # Starred emails
    if is_starred:
        query.append('is:starred')
        label_ids.append('STARRED')

    # Important emails
    if is_important:
        query.append('is:important')
        label_ids.append('IMPORTANT')

    # Combine query
    q = ' '.join(query) if query else None

    try:
        # List messages with filters
        results = service.users().messages().list(
            userId='me',
            labelIds=label_ids if label_ids else None,
            q=q,
            maxResults=max_results
        ).execute()
        
        messages = results.get('messages', [])
        if not messages:
            print('No messages found.')
            return []
        
        email_list = []
        print(f'Found {len(messages)} messages:')
        for msg in messages:
            # Get full message details
            msg_data = service.users().messages().get(userId='me', id=msg['id']).execute()
            
            # Extract headers
            headers = msg_data['payload']['headers']
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
            sender_header = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown Sender')
            
            # Snippet is a preview of the body
            snippet = msg_data['snippet']
            
            print(f'- ID: {msg["id"]}')
            print(f'  Subject: {subject}')
            print(f'  From: {sender_header}')
            print(f'  Preview: {snippet[:100]}...')
            print()
            
            # Store details (optional: return as list of dicts)
            email_list.append({
                'id': msg['id'],
                'subject': subject,
                'from': sender_header,
                'snippet': snippet
            })
        
        return email_list
        
    except HttpError as error:
        print(f'An error occurred: {error}')
        return []

# Legacy function (for backward compatibility)
def list_and_read_messages(service, max_results=5):
    return fetch_emails(service, max_results=max_results)

if __name__ == '__main__':
    service = authenticate_gmail()
    # Example usage: Fetch unread emails from a specific sender
    fetch_emails(service, sender='website@huggingface.co', is_read=False)