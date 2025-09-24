#!/usr/bin/env python3
"""Debug why SAM.gov events aren't showing"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from servers.trading.darpa_events_monitor import DARPAEventsMonitor

print("🔍 Testing DARPAEventsMonitor.fetch_darpa_news() directly\n")

monitor = DARPAEventsMonitor()

# Call the method directly
events = monitor.fetch_darpa_news()

print(f"✅ Fetched {len(events)} events from SAM.gov\n")

if events:
    for i, event in enumerate(events[:5], 1):
        print(f"{i}. {event.title[:60]}...")
        print(f"   Source: {event.source}")
        print(f"   Type: {event.signal_type}")
        print(f"   Date: {event.datetime}")
        print(f"   Companies: {event.companies}")
        print()
else:
    print("❌ No events returned - checking why...")

    # Try calling the API directly within the module
    import requests

    url = "https://sam.gov/api/prod/sgs/v1/search/"
    params = {
        'index': 'opp',
        'q': 'DARPA',
        'page': 0,
        'sort': '-modifiedDate',
        'size': 5
    }

    response = requests.get(url, params=params, timeout=10)
    if response.status_code == 200:
        data = response.json()
        if '_embedded' in data and 'results' in data['_embedded']:
            print(f"✅ API works - {len(data['_embedded']['results'])} results")
            print("Issue must be in the event creation logic")
    else:
        print(f"❌ API failed: {response.status_code}")