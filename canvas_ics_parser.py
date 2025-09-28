import os
import requests
from icalendar import Calendar
from datetime import datetime, timedelta
from dateutil import tz
from dotenv import load_dotenv

load_dotenv()
ICS_URL = os.getenv("CANVAS_ICS_URL")   # put your feed URL here in a .env file
LOCAL_TZ = tz.gettz("America/Phenoix")  # change if you prefer another timezone

if not ICS_URL:
    print("Set CANVAS_ICS_URL in a .env file (CANVAS_ICS_URL='https://...')"); exit(1)

resp = requests.get(ICS_URL, timeout=15)
resp.raise_for_status()

cal = Calendar.from_ical(resp.content)

now = datetime.now(tz=LOCAL_TZ)
lookahead_days = 7
window_end = now + timedelta(days=lookahead_days)
events = []

for component in cal.walk():
    if component.name == "VEVENT":
        summary = str(component.get('summary') or "").strip()
        raw_dtstart = component.get('dtstart').dt
        raw_dtend = component.get('dtend').dt if component.get('dtend') else None
        description = str(component.get('description') or "").strip()
        url = str(component.get('url') or "").strip()

        # normalize datetimes to LOCAL_TZ
        def normalize(dt):
            if isinstance(dt, datetime):
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=tz.tzutc())
                return dt.astimezone(LOCAL_TZ)
            else:
                # all-day dates might be date objects — cast to midnight local
                return datetime(dt.year, dt.month, dt.day, tzinfo=LOCAL_TZ)

        start = normalize(raw_dtstart)
        end = normalize(raw_dtend) if raw_dtend else start

        # cheap assignment detection heuristics
        is_assignment = ("assign" in description.lower()) or ("assignment" in description.lower()) \
                        or ("due" in summary.lower()) or ("due" in description.lower())

        if now <= start <= window_end:
            events.append({
                "summary": summary,
                "start": start,
                "end": end,
                "description": description,
                "url": url,
                "is_assignment": is_assignment
            })

# pretty print
events.sort(key=lambda e: e["start"])
for e in events:
    s = e["start"].strftime("%Y-%m-%d %H:%M %Z")
    print(f"{s}  —  {e['summary']}")
    if e['is_assignment']:
        print("   → probable assignment / deadline")
    if e['url']:
        print(f"   url: {e['url']}")
    if e['description']:
        print("   " + (e['description'][:200].replace("\n", " ") + ("…" if len(e['description'])>200 else "")))
    print()

