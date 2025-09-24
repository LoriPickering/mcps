#!/usr/bin/env python3
"""
Macro Events Tracker for Trading System
Monitors Fed speeches, FOMC meetings, economic data releases, and geopolitical events
"""

import os
import json
import logging
import requests
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict, field
from pathlib import Path
import pandas as pd
import asyncio
from enum import Enum

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get project root
PROJECT_ROOT = Path(__file__).parent.parent.parent.absolute()
EVENTS_CACHE_DIR = PROJECT_ROOT / "data" / "events"
EVENTS_CACHE_DIR.mkdir(parents=True, exist_ok=True)


class EventImportance(Enum):
    """Event importance levels"""
    CRITICAL = "critical"  # Fed meetings, major geopolitical events
    HIGH = "high"         # Fed speeches, CPI/NFP releases
    MEDIUM = "medium"     # Other economic data
    LOW = "low"           # Minor events


class EventCategory(Enum):
    """Event categories"""
    FED = "fed"                    # Federal Reserve events
    CENTRAL_BANK = "central_bank"  # Other central banks
    ECONOMIC_DATA = "economic_data"  # Economic indicators
    EARNINGS = "earnings"           # Earnings releases
    GEOPOLITICAL = "geopolitical"  # Wars, elections, etc.
    MARKET_HOURS = "market_hours"  # Market open/close, holidays


@dataclass
class MacroEvent:
    """Structured macro event"""
    id: str
    title: str
    category: EventCategory
    importance: EventImportance
    datetime: datetime
    description: str
    impact: str  # Expected market impact
    source: str
    country: str = "US"
    actual: Optional[str] = None
    forecast: Optional[str] = None
    previous: Optional[str] = None
    speakers: List[str] = field(default_factory=list)
    affected_assets: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class MacroEventsTracker:
    """Tracks macroeconomic events and their market impact"""

    def __init__(self):
        """Initialize the macro events tracker"""
        self.events_cache: Dict[str, List[MacroEvent]] = {}
        self.fed_calendar_url = "https://www.federalreserve.gov/json/calendar.json"

        # Common headers for web requests
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Accept': 'application/json, text/plain, */*',
        }

        # Key economic indicators to track
        self.key_indicators = [
            "CPI", "PPI", "NFP", "GDP", "PCE", "ISM", "PMI",
            "Retail Sales", "Housing Starts", "Consumer Confidence",
            "Initial Jobless Claims", "FOMC Minutes"
        ]

        # Fed officials to track
        self.fed_officials = [
            "Powell", "Barkin", "Bostic", "Bowman", "Cook", "Goolsbee",
            "Jefferson", "Kashkari", "Kugler", "Logan", "Musalem", "Schmid",
            "Waller", "Williams"
        ]

        logger.info("MacroEventsTracker initialized")

    def fetch_fed_calendar(self) -> List[MacroEvent]:
        """
        Fetch Federal Reserve calendar events

        Returns:
            List of Fed events
        """
        events = []

        try:
            logger.info("Fetching Federal Reserve calendar...")
            response = requests.get(self.fed_calendar_url, headers=self.headers, timeout=10)
            response.raise_for_status()

            # Handle potential BOM in response
            text = response.text
            if text.startswith('\ufeff'):
                text = text[1:]

            data = json.loads(text)
            fed_events = data.get('events', [])

            logger.info(f"Fed calendar returned {len(fed_events)} events")

            # Debug: log first event if available
            if fed_events and len(fed_events) > 0:
                logger.debug(f"Sample event: {fed_events[0]}")

            for event_data in fed_events:
                try:
                    # Parse Fed event
                    event = self._parse_fed_event(event_data)
                    if event:
                        events.append(event)
                except Exception as e:
                    logger.error(f"Error parsing Fed event: {e}")

            logger.info(f"Fetched {len(events)} Fed events")

        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching Fed calendar: {e}")
        except Exception as e:
            logger.error(f"Unexpected error fetching Fed calendar: {e}")

        return events

    def _parse_fed_event(self, event_data: Dict) -> Optional[MacroEvent]:
        """Parse a Fed calendar event"""
        try:
            # Extract event details
            title = event_data.get('title', 'Fed Event')

            # Fed calendar uses 'month' and 'days' fields
            month_str = event_data.get('month', '')
            days_str = event_data.get('days', '')
            time_str = event_data.get('time', '')

            # Parse datetime from Fed format (e.g., month: "2025-12", days: "10")
            if month_str and days_str:
                # Handle single day or range (e.g., "10" or "10-11")
                day = days_str.split('-')[0].strip()

                # If month_str doesn't have a year (old format), skip this event
                if '-' not in month_str:
                    logger.debug(f"Skipping event with old date format: {month_str}")
                    return None

                # Combine into datetime string
                datetime_str = f"{month_str}-{day.zfill(2)}"
                if time_str:
                    # Clean time (e.g., "2:30 p.m." -> "14:30")
                    time_str = self._parse_fed_time(time_str)
                    datetime_str = f"{datetime_str} {time_str}"

                event_datetime = self._parse_datetime(datetime_str)
            else:
                return None

            # Determine importance
            importance = self._determine_fed_importance(title)

            # Identify speakers
            speakers = self._extract_speakers(title, event_data.get('description', ''))

            # Create event
            event = MacroEvent(
                id=f"fed_{event_datetime.strftime('%Y%m%d_%H%M')}_{hash(title) % 1000}",
                title=title,
                category=EventCategory.FED,
                importance=importance,
                datetime=event_datetime,
                description=event_data.get('summary', event_data.get('description', '')),
                impact=self._assess_fed_impact(title, importance),
                source="Federal Reserve",
                speakers=speakers,
                affected_assets=["SPY", "DXY", "TLT", "GLD"],  # Major affected assets
                metadata={
                    'location': event_data.get('location', ''),
                    'event_type': event_data.get('type', ''),
                    'link': event_data.get('link', ''),
                    'month': event_data.get('month', ''),
                    'days': event_data.get('days', '')
                }
            )

            return event

        except Exception as e:
            logger.error(f"Error parsing Fed event: {e}")
            return None

    def _determine_fed_importance(self, title: str) -> EventImportance:
        """Determine importance of Fed event"""
        title_lower = title.lower()

        # Critical events
        if any(keyword in title_lower for keyword in ["fomc", "federal open market", "rate decision"]):
            return EventImportance.CRITICAL

        # High importance
        if any(keyword in title_lower for keyword in ["powell", "chair", "testimony", "semiannual"]):
            return EventImportance.HIGH

        # Check for other Fed officials
        for official in self.fed_officials:
            if official.lower() in title_lower:
                return EventImportance.HIGH if "powell" in official.lower() else EventImportance.MEDIUM

        return EventImportance.MEDIUM

    def _assess_fed_impact(self, title: str, importance: EventImportance) -> str:
        """Assess market impact of Fed event"""
        if importance == EventImportance.CRITICAL:
            return "Major volatility expected across all markets"
        elif importance == EventImportance.HIGH:
            if "powell" in title.lower():
                return "High volatility expected in bonds and equities"
            return "Moderate volatility expected, watch for policy hints"
        else:
            return "Limited immediate impact, monitor for policy signals"

    def _extract_speakers(self, title: str, description: str) -> List[str]:
        """Extract speaker names from event text"""
        speakers = []
        text = f"{title} {description}".lower()

        for official in self.fed_officials:
            if official.lower() in text:
                speakers.append(official)

        return speakers

    def fetch_economic_calendar(self, days_ahead: int = 7) -> List[MacroEvent]:
        """
        Fetch economic calendar events

        Note: This is a placeholder for integration with economic calendar APIs
        like TradingEconomics, Investing.com, or others
        """
        events = []

        # For now, create some example high-impact events
        # In production, this would fetch from actual APIs

        upcoming_events = [
            {
                'title': 'US CPI (YoY)',
                'datetime': datetime.now(timezone.utc) + timedelta(days=2, hours=8, minutes=30),
                'importance': EventImportance.HIGH,
                'forecast': '3.2%',
                'previous': '3.7%',
                'impact': 'High volatility expected if significantly different from forecast'
            },
            {
                'title': 'US Non-Farm Payrolls',
                'datetime': datetime.now(timezone.utc) + timedelta(days=5, hours=8, minutes=30),
                'importance': EventImportance.HIGH,
                'forecast': '180K',
                'previous': '150K',
                'impact': 'Major market mover, affects Fed policy expectations'
            },
            {
                'title': 'FOMC Minutes',
                'datetime': datetime.now(timezone.utc) + timedelta(days=3, hours=14),
                'importance': EventImportance.HIGH,
                'impact': 'Watch for hawkish/dovish language changes'
            }
        ]

        for event_data in upcoming_events:
            event = MacroEvent(
                id=f"econ_{event_data['title'].replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}",
                title=event_data['title'],
                category=EventCategory.ECONOMIC_DATA,
                importance=event_data['importance'],
                datetime=event_data['datetime'],
                description=f"Economic data release: {event_data['title']}",
                impact=event_data['impact'],
                source="Economic Calendar",
                forecast=event_data.get('forecast'),
                previous=event_data.get('previous'),
                affected_assets=["SPY", "DXY", "VIX"]
            )
            events.append(event)

        return events

    def fetch_geopolitical_events(self) -> List[MacroEvent]:
        """
        Fetch geopolitical events that could impact markets

        This would integrate with news APIs to detect:
        - Elections
        - Military conflicts
        - Trade disputes
        - Sanctions
        - Major policy changes
        """
        events = []

        # Placeholder for geopolitical event detection
        # In production, this would analyze news feeds for key events

        return events

    def get_upcoming_events(
        self,
        hours_ahead: int = 48,
        categories: Optional[List[EventCategory]] = None,
        min_importance: EventImportance = EventImportance.MEDIUM
    ) -> List[MacroEvent]:
        """
        Get upcoming macro events

        Args:
            hours_ahead: Hours to look ahead
            categories: Filter by categories
            min_importance: Minimum importance level

        Returns:
            List of upcoming events sorted by datetime
        """
        all_events = []

        # Fetch from various sources
        all_events.extend(self.fetch_fed_calendar())
        all_events.extend(self.fetch_economic_calendar())
        all_events.extend(self.fetch_geopolitical_events())

        # Filter by time window
        cutoff_time = datetime.now(timezone.utc) + timedelta(hours=hours_ahead)
        current_time = datetime.now(timezone.utc)

        filtered_events = [
            event for event in all_events
            if current_time <= event.datetime <= cutoff_time
        ]

        # Filter by categories if specified
        if categories:
            filtered_events = [
                event for event in filtered_events
                if event.category in categories
            ]

        # Filter by importance
        importance_levels = {
            EventImportance.LOW: 0,
            EventImportance.MEDIUM: 1,
            EventImportance.HIGH: 2,
            EventImportance.CRITICAL: 3
        }

        min_level = importance_levels[min_importance]
        filtered_events = [
            event for event in filtered_events
            if importance_levels[event.importance] >= min_level
        ]

        # Sort by datetime
        filtered_events.sort(key=lambda x: x.datetime)

        return filtered_events

    def get_today_events(self) -> Dict[str, List[MacroEvent]]:
        """
        Get today's events organized by time period

        Returns:
            Dict with 'pre_market', 'regular_hours', 'after_hours' events
        """
        today = datetime.now(timezone.utc).date()
        today_events = self.get_upcoming_events(hours_ahead=24)

        # Filter for today only
        today_events = [
            event for event in today_events
            if event.datetime.date() == today
        ]

        # Organize by market session (ET times)
        pre_market = []   # Before 9:30 AM ET
        regular = []      # 9:30 AM - 4:00 PM ET
        after_hours = []  # After 4:00 PM ET

        for event in today_events:
            # Convert to ET (UTC-5 or UTC-4 for DST)
            et_hour = event.datetime.hour - 5  # Simplified, adjust for DST

            if et_hour < 9.5:
                pre_market.append(event)
            elif et_hour < 16:
                regular.append(event)
            else:
                after_hours.append(event)

        return {
            'pre_market': pre_market,
            'regular_hours': regular,
            'after_hours': after_hours
        }

    def assess_market_impact(self, events: List[MacroEvent]) -> Dict[str, Any]:
        """
        Assess combined market impact of multiple events

        Returns:
            Assessment of likely market behavior
        """
        if not events:
            return {
                'volatility_expectation': 'normal',
                'risk_level': 'low',
                'recommended_action': 'normal trading',
                'event_count': 0,
                'critical_events': 0,
                'high_impact_events': 0,
                'risk_windows': []
            }

        # Count high-impact events
        critical_count = sum(1 for e in events if e.importance == EventImportance.CRITICAL)
        high_count = sum(1 for e in events if e.importance == EventImportance.HIGH)

        # Assess overall impact
        if critical_count > 0:
            volatility = 'extreme'
            risk = 'very high'
            action = 'reduce position sizes, widen stops'
        elif high_count >= 2:
            volatility = 'high'
            risk = 'high'
            action = 'be cautious, consider hedging'
        elif high_count == 1:
            volatility = 'elevated'
            risk = 'medium'
            action = 'monitor closely, normal position sizes'
        else:
            volatility = 'normal'
            risk = 'low'
            action = 'normal trading'

        # Identify key risk windows
        risk_windows = []
        for event in events:
            if event.importance in [EventImportance.CRITICAL, EventImportance.HIGH]:
                risk_windows.append({
                    'time': event.datetime.strftime('%Y-%m-%d %H:%M UTC'),
                    'event': event.title,
                    'impact': event.impact
                })

        return {
            'volatility_expectation': volatility,
            'risk_level': risk,
            'recommended_action': action,
            'event_count': len(events),
            'critical_events': critical_count,
            'high_impact_events': high_count,
            'risk_windows': risk_windows
        }

    def get_powell_schedule(self) -> List[MacroEvent]:
        """
        Get Jerome Powell's speaking schedule

        Returns:
            List of Powell's scheduled appearances
        """
        all_events = self.fetch_fed_calendar()

        powell_events = [
            event for event in all_events
            if 'powell' in event.title.lower() or 'Powell' in event.speakers
        ]

        return powell_events

    def _parse_fed_time(self, time_str: str) -> str:
        """Parse Fed time format (e.g., '2:30 p.m.' -> '14:30')"""
        try:
            time_str = time_str.strip().lower()

            # Remove periods
            time_str = time_str.replace('.', '')

            # Parse time parts
            is_pm = 'pm' in time_str or 'p.m' in time_str
            is_am = 'am' in time_str or 'a.m' in time_str

            # Remove am/pm indicators
            time_str = time_str.replace('pm', '').replace('p.m', '')
            time_str = time_str.replace('am', '').replace('a.m', '')
            time_str = time_str.strip()

            # Split hours and minutes
            if ':' in time_str:
                parts = time_str.split(':')
                hours = int(parts[0])
                minutes = int(parts[1]) if len(parts) > 1 else 0
            else:
                hours = int(time_str)
                minutes = 0

            # Convert to 24-hour format
            if is_pm and hours != 12:
                hours += 12
            elif is_am and hours == 12:
                hours = 0

            return f"{hours:02d}:{minutes:02d}"

        except Exception as e:
            logger.warning(f"Could not parse time: {time_str} - {e}")
            return "12:00"  # Default to noon

    def _parse_datetime(self, datetime_str: str) -> datetime:
        """Parse various datetime formats"""
        # Clean up the string
        datetime_str = datetime_str.strip()

        # Try common formats
        formats = [
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%d %H:%M',
            '%Y-%m-%d',
            '%Y/%m/%d %H:%M',
            '%Y/%m/%d',
            '%m/%d/%Y %H:%M',
            '%m/%d/%Y',
            '%m/%d/%y %H:%M',
            '%m/%d/%y',
            '%B %d, %Y',
            '%B %d, %Y %H:%M',
            '%b %d, %Y',
            '%b %d, %Y %H:%M',
            '%d %B %Y',
            '%d %b %Y'
        ]

        for fmt in formats:
            try:
                dt = datetime.strptime(datetime_str, fmt)
                # Add timezone if not present
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt
            except ValueError:
                continue

        # Try ISO format
        try:
            dt = datetime.fromisoformat(datetime_str)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except:
            pass

        # Default to now if parsing fails
        logger.warning(f"Could not parse datetime: {datetime_str}")
        return datetime.now(timezone.utc)

    def save_to_cache(self, events: List[MacroEvent]):
        """Save events to cache"""
        cache_file = EVENTS_CACHE_DIR / f"events_{datetime.now().strftime('%Y%m%d')}.json"

        data = {
            'updated_at': datetime.now(timezone.utc).isoformat(),
            'events': [
                {
                    **asdict(event),
                    'datetime': event.datetime.isoformat(),
                    'category': event.category.value,
                    'importance': event.importance.value
                }
                for event in events
            ]
        }

        with open(cache_file, 'w') as f:
            json.dump(data, f, indent=2)

        logger.info(f"Saved {len(events)} events to cache")

    def load_from_cache(self) -> Optional[List[MacroEvent]]:
        """Load events from cache"""
        cache_file = EVENTS_CACHE_DIR / f"events_{datetime.now().strftime('%Y%m%d')}.json"

        if not cache_file.exists():
            return None

        try:
            with open(cache_file, 'r') as f:
                data = json.load(f)

            # Check if cache is recent (within 1 hour)
            updated_at = datetime.fromisoformat(data['updated_at'])
            if (datetime.now(timezone.utc) - updated_at).total_seconds() > 3600:
                return None

            # Convert back to MacroEvent objects
            events = []
            for event_data in data['events']:
                event_data['datetime'] = datetime.fromisoformat(event_data['datetime'])
                event_data['category'] = EventCategory(event_data['category'])
                event_data['importance'] = EventImportance(event_data['importance'])
                events.append(MacroEvent(**event_data))

            logger.info(f"Loaded {len(events)} events from cache")
            return events

        except Exception as e:
            logger.error(f"Error loading cache: {e}")
            return None


def main():
    """Test the macro events tracker"""
    tracker = MacroEventsTracker()

    print("\n=== Upcoming Macro Events ===")
    events = tracker.get_upcoming_events(hours_ahead=72)

    for event in events[:10]:  # Show first 10
        print(f"\n{event.datetime.strftime('%Y-%m-%d %H:%M')} - {event.title}")
        print(f"  Category: {event.category.value}")
        print(f"  Importance: {event.importance.value}")
        print(f"  Impact: {event.impact}")
        if event.speakers:
            print(f"  Speakers: {', '.join(event.speakers)}")

    print("\n=== Today's Events ===")
    today_events = tracker.get_today_events()

    for period, events in today_events.items():
        print(f"\n{period.replace('_', ' ').title()}: {len(events)} events")
        for event in events:
            print(f"  - {event.datetime.strftime('%H:%M')} {event.title}")

    print("\n=== Market Impact Assessment ===")
    assessment = tracker.assess_market_impact(tracker.get_upcoming_events(hours_ahead=24))

    print(f"Volatility Expectation: {assessment['volatility_expectation']}")
    print(f"Risk Level: {assessment['risk_level']}")
    print(f"Recommended Action: {assessment['recommended_action']}")

    if assessment['risk_windows']:
        print("\nRisk Windows:")
        for window in assessment['risk_windows']:
            print(f"  - {window['time']}: {window['event']}")

    print("\n=== Powell Speaking Schedule ===")
    powell_events = tracker.get_powell_schedule()

    if powell_events:
        for event in powell_events[:3]:  # Show next 3
            print(f"\n{event.datetime.strftime('%Y-%m-%d %H:%M')} - {event.title}")
            print(f"  Impact: {event.impact}")
    else:
        print("No upcoming Powell speeches found")


if __name__ == "__main__":
    main()