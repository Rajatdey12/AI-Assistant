"""
Calendar Integration Stub for Chiku (Phase 2)

Placeholder for calendar/schedule queries. Real implementation coming in MVP 2.
"""

import logging
from typing import List, Dict
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


def get_schedule(days: int = 7) -> List[Dict]:
    """
    Get upcoming schedule.
    Currently returns mock data for demo.
    
    Real implementation will integrate with:
    - Google Calendar API
    - Outlook/Office 365
    - Apple Calendar
    """
    
    # Mock schedule
    schedule = [
        {
            "time": "2:00 PM",
            "event": "Team sync meeting",
            "duration": "1 hour"
        },
        {
            "time": "4:00 PM",
            "event": "Project review",
            "duration": "30 minutes"
        }
    ]
    
    return schedule


def add_event(title: str, description: str, date: str, time: str) -> Dict:
    """Mock: Add calendar event"""
    return {"status": "mock", "message": f"Would add: {title}"}


def upcoming_events(hours: int = 24) -> List[Dict]:
    """Mock: Get upcoming events in next N hours"""
    return get_schedule()


if __name__ == "__main__":
    print("Testing Calendar Integration (Stub)...")
    schedule = get_schedule()
    for event in schedule:
        print(f"  {event['time']}: {event['event']} ({event['duration']})")
