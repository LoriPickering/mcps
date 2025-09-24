#!/usr/bin/env python3
"""
DARPA Monitor Daemon - Automated collection and monitoring
Run this as a background service to continuously monitor DARPA events
"""

import os
import sys
import time
import json
import schedule
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv

# Setup paths
PROJECT_ROOT = Path(__file__).parent.absolute()
sys.path.insert(0, str(PROJECT_ROOT))

# Load environment
load_dotenv(PROJECT_ROOT / ".env")

from servers.trading.mcp_server_integrated import MCPServer
from servers.trading.darpa_events_monitor import DARPAEventsMonitor

# Configuration
CHECK_INTERVAL_MINUTES = 30  # Check for new events every 30 minutes
TICKER_CHECK_HOURS = 4      # Check ticker prices every 4 hours
ALERT_LOG = PROJECT_ROOT / "data" / "darpa_alerts.json"

class DARPAMonitorDaemon:
    def __init__(self):
        self.server = MCPServer()
        self.monitor = DARPAEventsMonitor()
        self.last_events = {}
        self.high_importance_alerts = []

        # Ensure alert log directory exists
        ALERT_LOG.parent.mkdir(parents=True, exist_ok=True)

    def check_darpa_events(self):
        """Check for new DARPA events and alert on high-importance ones"""
        print(f"\n[{datetime.now()}] Checking DARPA events...")

        try:
            # Get events from all sources
            events_result = self.server.get_darpa_events(hours_back=24, source="all")

            if events_result['status'] == 'success':
                new_count = 0
                high_importance_count = 0

                for event in events_result['events']:
                    event_id = f"{event['source']}_{event['datetime']}"

                    # Check if this is a new event
                    if event_id not in self.last_events:
                        new_count += 1
                        self.last_events[event_id] = event

                        # Alert on high-importance events
                        if event['importance'] == 'high':
                            high_importance_count += 1
                            self.alert_high_importance(event)

                        # Check if event mentions specific tickers
                        if event.get('companies'):
                            self.check_ticker_impact(event)

                print(f"  ✅ Found {events_result['total_events']} events")
                print(f"  📢 {new_count} new events ({high_importance_count} high importance)")

                if events_result.get('mentioned_tickers'):
                    print(f"  🎯 Tickers mentioned: {', '.join(events_result['mentioned_tickers'][:5])}")

        except Exception as e:
            print(f"  ❌ Error checking events: {e}")

    def check_ticker_prices(self):
        """Check prices for DARPA tickers"""
        print(f"\n[{datetime.now()}] Checking DARPA ticker prices...")

        darpa_tickers = ['IONQ', 'QBTS', 'DNA', 'KTOS', 'AVAV', 'BBAI', 'SMR']

        try:
            result = self.server.check_ticker_availability(darpa_tickers)

            if result['status'] == 'success':
                significant_movers = []

                for ticker, info in result['results'].items():
                    if info['available']:
                        # Check for significant price movements (implement your logic)
                        # For now, just track the prices
                        print(f"  • {ticker}: ${info['last_price']:.2f}")

                        # You could add logic here to detect significant moves
                        # e.g., compare with previous prices, check volume spikes, etc.

        except Exception as e:
            print(f"  ❌ Error checking prices: {e}")

    def alert_high_importance(self, event):
        """Log high-importance events for review"""
        alert = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'event': event,
            'alerted': True
        }

        self.high_importance_alerts.append(alert)

        # Save to file
        try:
            if ALERT_LOG.exists():
                with open(ALERT_LOG, 'r') as f:
                    alerts = json.load(f)
            else:
                alerts = []

            alerts.append(alert)

            with open(ALERT_LOG, 'w') as f:
                json.dump(alerts, f, indent=2, default=str)

            print(f"  🚨 HIGH IMPORTANCE: {event['title'][:60]}...")
            print(f"     Domain: {event.get('technology_domain', 'unknown')}")
            if event.get('companies'):
                print(f"     Tickers: {', '.join(event['companies'])}")

        except Exception as e:
            print(f"  ❌ Error saving alert: {e}")

    def check_ticker_impact(self, event):
        """Check if an event might impact specific tickers"""
        if not event.get('companies'):
            return

        print(f"  💡 Event impacts tickers: {', '.join(event['companies'])}")

        # You could add logic here to:
        # 1. Fetch current signals for these tickers
        # 2. Check if there's unusual volume
        # 3. Alert if combined with technical signals

    def run_once(self):
        """Run all checks once"""
        print("=" * 60)
        print("🚀 DARPA MONITOR - MANUAL RUN")
        print("=" * 60)

        self.check_darpa_events()
        self.check_ticker_prices()

        print("\n" + "=" * 60)
        print("✅ Check complete")
        print("=" * 60)

    def run_daemon(self):
        """Run as a continuous daemon"""
        print("=" * 60)
        print("🤖 DARPA MONITOR DAEMON STARTED")
        print("=" * 60)
        print(f"Event check interval: {CHECK_INTERVAL_MINUTES} minutes")
        print(f"Ticker check interval: {TICKER_CHECK_HOURS} hours")
        print(f"Alert log: {ALERT_LOG}")
        print("\nPress Ctrl+C to stop\n")

        # Schedule jobs
        schedule.every(CHECK_INTERVAL_MINUTES).minutes.do(self.check_darpa_events)
        schedule.every(TICKER_CHECK_HOURS).hours.do(self.check_ticker_prices)

        # Run once immediately
        self.check_darpa_events()
        self.check_ticker_prices()

        # Keep running
        try:
            while True:
                schedule.run_pending()
                time.sleep(60)  # Check every minute for scheduled tasks
        except KeyboardInterrupt:
            print("\n🛑 Daemon stopped by user")
            print(f"Processed {len(self.last_events)} total events")
            print(f"Generated {len(self.high_importance_alerts)} high-importance alerts")

def main():
    daemon = DARPAMonitorDaemon()

    if len(sys.argv) > 1 and sys.argv[1] == '--once':
        # Run once and exit
        daemon.run_once()
    else:
        # Run as daemon
        daemon.run_daemon()

if __name__ == "__main__":
    main()