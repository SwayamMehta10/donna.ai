
from google_auth import authenticate_google
from googleapiclient.errors import HttpError
from datetime import datetime, timedelta
import pytz
from mylogger import logging

def google_calender(service, calendar_id='primary', time_min=None, time_max=None, max_results=20):
    """Fetch upcoming events from the calendar with debugging."""
    try:
        # Use MDT timezone explicitly
        mst = pytz.timezone('America/Denver')  # MDT is active in September
        now = mst.localize(datetime.now()).isoformat()
        print(f"Current time (MDT): {now}")
        
        # Default to today 00:00 to 7 days ahead
        if not time_min:
            time_min = mst.localize(datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)).isoformat()
            print(f"Default timeMin: {time_min}")
        if not time_max:
            time_max = (mst.localize(datetime.now()) + timedelta(days=30)).isoformat()
            print(f"Default timeMax: {time_max}")
        
        print(f"Fetching events from {time_min} to {time_max} for calendar {calendar_id}")
        events_result = service.events().list(
            calendarId=calendar_id,
            timeMin=time_min,
            timeMax=time_max,
            maxResults=max_results,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])
        if not events:
            print('No upcoming events found.')
            return []
        
        event_list = []
        print(f'Found {len(events)} upcoming events:')
        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            end = event['end'].get('dateTime', event['end'].get('date'))
            summary = event.get('summary', 'No Summary')
            print(f'- Summary: {summary}')
            print(f'  Start: {start}')
            print(f'  End: {end}')
            print()
            event_list.append({'id': event['id'], 'summary': summary, 'start': start, 'end': end})
        
        return event_list
        
    except HttpError as error:
        print(f'An error occurred: {error}')
        return []

if __name__ == '__main__':
    service = authenticate_google('calendar', version='v3')
    google_calender(service)