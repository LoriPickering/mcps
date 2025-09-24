#!/usr/bin/env python3
"""
DARPA Events Monitor for Frontier Tech Investments
Tracks government contracts, research publications, and signal events
for DARPA-style investments in quantum, biotech, defense, and frontier tech
"""

import os
import json
import logging
import requests
import feedparser
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict, field
from pathlib import Path
import asyncio
import re
from enum import Enum

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get project root
PROJECT_ROOT = Path(__file__).parent.parent.parent.absolute()
DARPA_CACHE_DIR = PROJECT_ROOT / "data" / "darpa_events"
DARPA_CACHE_DIR.mkdir(parents=True, exist_ok=True)


class EventSource(Enum):
    """Sources for DARPA-related events"""
    DARPA_NEWS = "darpa_news"
    DOD_CONTRACTS = "dod_contracts"
    ARXIV = "arxiv"
    NATURE = "nature"
    SCIENCE = "science"
    USPTO = "uspto"
    SEC_FILINGS = "sec_filings"
    GITHUB = "github"
    GOOGLE_SCHOLAR = "google_scholar"


class SignalType(Enum):
    """Types of signal events from the DARPA document"""
    CONTRACT_AWARD = "contract_award"
    RESEARCH_PUBLICATION = "research_publication"
    PATENT_FILING = "patent_filing"
    PARTNERSHIP = "partnership"
    FUNDING_ROUND = "funding_round"
    ACQUISITION = "acquisition"
    FIELD_TEST = "field_test"
    MILESTONE = "milestone"
    REGULATORY = "regulatory"


@dataclass
class DARPAEvent:
    """A DARPA-related signal event"""
    id: str
    title: str
    source: EventSource
    signal_type: SignalType
    companies: List[str]  # Tickers or company names
    technology_domain: str
    description: str
    url: str
    datetime: datetime
    importance: str  # high, medium, low
    financial_impact: Optional[str] = None
    contract_value: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class DARPAEventsMonitor:
    """Monitors DARPA-style frontier tech signal events"""

    def __init__(self):
        """Initialize the DARPA events monitor"""
        self.events_cache: Dict[str, List[DARPAEvent]] = {}

        # Tracked companies and their domains with research keywords
        self.tracked_companies = {
            # Quantum
            "IONQ": {"name": "IonQ", "domain": "quantum_computing",
                     "keywords": ["trapped ion", "quantum gate", "quantum circuit", "ion trap"]},
            "QBTS": {"name": "D-Wave", "domain": "quantum_computing",
                     "keywords": ["quantum annealing", "adiabatic quantum", "quantum optimization"]},
            "RGTI": {"name": "Rigetti", "domain": "quantum_computing",
                     "keywords": ["superconducting qubit", "quantum cloud", "forest sdk"]},
            "QUBT": {"name": "Quantum Computing Inc", "domain": "quantum_computing",
                     "keywords": ["quantum optimization", "qatalyst", "quantum software"]},

            # Biotech/Synthetic Biology
            "DNA": {"name": "Ginkgo Bioworks", "domain": "synthetic_biology",
                    "keywords": ["synthetic biology", "bioengineering", "cell programming", "metabolic engineering"]},

            # Defense/Space
            "KRMN": {"name": "Karman Holdings", "domain": "space_defense"},
            "KTOS": {"name": "Kratos Defense", "domain": "defense_autonomy"},
            "AVAV": {"name": "AeroVironment", "domain": "uav_robotics"},
            "MRCY": {"name": "Mercury Systems", "domain": "defense_tech"},

            # AI/Autonomy
            "BBAI": {"name": "BigBear.ai", "domain": "ai_defense"},

            # Private but trackable
            "ANDURIL": {"name": "Anduril Industries", "domain": "defense_autonomy", "private": True}
        }

        # Signal event keywords to monitor
        self.signal_keywords = {
            "quantum_networking": [
                "quantum communication", "quantum internet", "entanglement",
                "quantum repeater", "transduction", "photonic link"
            ],
            "quantum_sensing": [
                "quantum sensor", "quantum metrology", "quantum radar",
                "quantum gravimeter", "quantum magnetometer"
            ],
            "synthetic_biology": [
                "DARPA Living Foundries", "bioengineering", "CRISPR",
                "gene editing", "biosynthesis", "biomanufacturing"
            ],
            "metamaterials": [
                "metamaterial", "electromagnetic cloak", "negative index",
                "photonic crystal", "metasurface"
            ],
            "autonomy": [
                "drone swarm", "autonomous vehicle", "UAV", "UUV",
                "collaborative autonomy", "multi-agent"
            ]
        }

        # RSS feeds and APIs to monitor
        self.feeds = {
            "darpa_news": "https://www.darpa.mil/rss",
            "dod_contracts": "https://www.defense.gov/DesktopModules/ArticleCS/RSS.ashx?ContentType=1&Site=945&max=10",
            "arxiv_quantum": "http://arxiv.org/rss/quant-ph",
            "arxiv_cs": "http://arxiv.org/rss/cs.AI"
        }

        logger.info("DARPAEventsMonitor initialized")

    def fetch_darpa_news(self) -> List[DARPAEvent]:
        """Fetch DARPA opportunities from SAM.gov"""
        events = []

        try:
            # Use SAM.gov API for DARPA opportunities
            import requests
            url = "https://sam.gov/api/prod/sgs/v1/search/"
            params = {
                'index': 'opp',
                'q': 'DARPA',
                'page': 0,
                'sort': '-modifiedDate',
                'size': 20
            }
            response = requests.get(url, params=params, timeout=10)

            if response.status_code == 200:
                data = response.json()
                if '_embedded' in data and 'results' in data['_embedded']:
                    logger.info(f"Found {len(data['_embedded']['results'])} SAM.gov results")
                    for item in data['_embedded']['results'][:20]:
                        # Extract opportunity details
                        title = item.get('title', 'No Title')
                        # SAM.gov uses 'descriptions' as a list
                        descriptions = item.get('descriptions', [])
                        description = descriptions[0].get('value', '') if descriptions else ''
                        content = f"{title} {description}".lower()

                        relevant_companies = []
                        relevant_domains = []

                        # Check for company mentions
                        for ticker, info in self.tracked_companies.items():
                            if info["name"].lower() in content:
                                relevant_companies.append(ticker)
                                relevant_domains.append(info["domain"])

                        # Check for keyword matches
                        for domain, keywords in self.signal_keywords.items():
                            if any(keyword.lower() in content for keyword in keywords):
                                relevant_domains.append(domain)

                        # Create event for DARPA opportunities - all items from DARPA search are relevant
                        # Since we searched for "DARPA", all results are DARPA-related
                        if True:  # Always create event since these are all DARPA results
                            # Parse the date - SAM.gov dates might be in different formats
                            try:
                                event_date = datetime.fromisoformat(item.get('modifiedDate', '').replace('Z', '+00:00'))
                            except:
                                event_date = datetime.now(timezone.utc)

                            event = DARPAEvent(
                                id=f"darpa_{item.get('_id', hash(title))}",
                                title=title[:200],
                                source=EventSource.DARPA_NEWS,
                                signal_type=SignalType.CONTRACT_AWARD if 'award' in title.lower() else SignalType.FUNDING_ROUND,
                                companies=relevant_companies,
                                technology_domain=", ".join(set(relevant_domains)) if relevant_domains else "defense_general",
                                description=description[:500] if description else "DARPA opportunity",
                                url=f"https://sam.gov/opp/{item.get('_id', item.get('solicitationNumber', ''))}/view",
                                datetime=event_date,
                                importance="high" if 'urgent' in title.lower() or len(relevant_companies) > 0 else "medium",
                                contract_value=item.get('award', {}).get('amount'),
                                metadata={
                                    'source_feed': 'SAM.gov',
                                    'opportunity_type': item.get('type', ''),
                                    'naics': item.get('naicsCode', ''),
                                    'response_deadline': item.get('responseDeadLine', '')
                                }
                            )
                            events.append(event)

        except Exception as e:
            logger.error(f"Error fetching DARPA news: {e}")

        return events

    def fetch_dod_contracts(self) -> List[DARPAEvent]:
        """Fetch DoD contract awards"""
        events = []

        try:
            feed_url = self.feeds.get("dod_contracts")
            if not feed_url:
                return events

            feed = feedparser.parse(feed_url)

            for entry in feed.entries[:20]:
                content = f"{entry.title} {entry.summary}".lower()

                # Look for contract values
                contract_value = self._extract_contract_value(content)

                relevant_companies = []
                for ticker, info in self.tracked_companies.items():
                    if info["name"].lower() in content:
                        relevant_companies.append(ticker)

                if relevant_companies or contract_value > 1000000:  # $1M+ contracts
                    event = DARPAEvent(
                        id=f"dod_{entry.get('id', hash(entry.title))}",
                        title=entry.title,
                        source=EventSource.DOD_CONTRACTS,
                        signal_type=SignalType.CONTRACT_AWARD,
                        companies=relevant_companies,
                        technology_domain=self._identify_domain(content),
                        description=entry.summary[:500],
                        url=entry.link,
                        datetime=self._parse_date(entry.get('published', '')),
                        importance="high" if contract_value > 10000000 else "medium",
                        contract_value=contract_value,
                        financial_impact=f"${contract_value:,.0f}" if contract_value else None
                    )
                    events.append(event)

        except Exception as e:
            logger.error(f"Error fetching DoD contracts: {e}")

        return events

    def fetch_arxiv_papers(self) -> List[DARPAEvent]:
        """Fetch relevant research papers from arXiv"""
        events = []

        feeds = ["arxiv_quantum", "arxiv_cs"]

        for feed_name in feeds:
            try:
                feed_url = self.feeds.get(feed_name)
                if not feed_url:
                    continue

                feed = feedparser.parse(feed_url)

                for entry in feed.entries[:10]:  # Last 10 papers
                    # Check for relevant keywords
                    content = f"{entry.title} {entry.summary}".lower()

                    relevant = False
                    domains = []
                    matched_tickers = []

                    # Check against company-specific research keywords
                    for ticker, info in self.tracked_companies.items():
                        if 'keywords' in info:
                            if any(kw.lower() in content for kw in info['keywords']):
                                matched_tickers.append(ticker)
                                domains.append(info['domain'])
                                relevant = True

                    # Also check general domain keywords
                    for domain, keywords in self.signal_keywords.items():
                        if any(keyword.lower() in content for keyword in keywords):
                            relevant = True
                            if domain not in domains:
                                domains.append(domain)

                    if relevant:
                        # Check for author affiliations with tracked companies
                        affiliated_companies = self._extract_company_affiliations(entry.get('authors', []))
                        companies = list(set(matched_tickers + affiliated_companies))

                        event = DARPAEvent(
                            id=f"arxiv_{entry.id.split('/')[-1]}",
                            title=f"Paper: {entry.title}",
                            source=EventSource.ARXIV,
                            signal_type=SignalType.RESEARCH_PUBLICATION,
                            companies=companies,
                            technology_domain=", ".join(domains),
                            description=entry.summary[:300],
                            url=entry.link,
                            datetime=self._parse_date(entry.get('published', '')),
                            importance="medium",
                            metadata={
                                'authors': entry.get('authors', []),
                                'arxiv_category': feed_name
                            }
                        )
                        events.append(event)

            except Exception as e:
                logger.error(f"Error fetching arXiv papers: {e}")

        return events

    def search_patents(self, companies: List[str]) -> List[DARPAEvent]:
        """Search for recent patent filings (placeholder for USPTO API)"""
        events = []

        # This would integrate with USPTO API
        # For now, creating placeholder structure
        logger.info(f"Patent search for {companies} - API integration needed")

        return events

    def monitor_sec_filings(self) -> List[DARPAEvent]:
        """Monitor SEC filings for tracked companies"""
        events = []

        # This would integrate with SEC EDGAR API
        # Looking for 8-K (material events), partnerships, acquisitions

        for ticker in ["IONQ", "DNA", "KTOS", "AVAV", "MRCY"]:
            # Placeholder for SEC API integration
            pass

        return events

    def get_all_events(self, hours_back: int = 168) -> List[DARPAEvent]:
        """Get all DARPA events from various sources"""
        all_events = []

        # Fetch from all sources
        all_events.extend(self.fetch_darpa_news())
        all_events.extend(self.fetch_dod_contracts())
        all_events.extend(self.fetch_arxiv_papers())

        # Filter by time
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours_back)
        filtered = [e for e in all_events if e.datetime >= cutoff]

        # Sort by datetime
        filtered.sort(key=lambda x: x.datetime, reverse=True)

        return filtered

    def get_company_events(self, ticker: str) -> List[DARPAEvent]:
        """Get events for a specific company"""
        all_events = self.get_all_events()
        return [e for e in all_events if ticker in e.companies]

    def _classify_signal_type(self, title: str) -> SignalType:
        """Classify the signal type based on title"""
        title_lower = title.lower()

        if "contract" in title_lower or "award" in title_lower:
            return SignalType.CONTRACT_AWARD
        elif "paper" in title_lower or "research" in title_lower:
            return SignalType.RESEARCH_PUBLICATION
        elif "patent" in title_lower:
            return SignalType.PATENT_FILING
        elif "partner" in title_lower or "collaboration" in title_lower:
            return SignalType.PARTNERSHIP
        elif "funding" in title_lower or "investment" in title_lower:
            return SignalType.FUNDING_ROUND
        elif "acqui" in title_lower or "merger" in title_lower:
            return SignalType.ACQUISITION
        elif "test" in title_lower or "demonstration" in title_lower:
            return SignalType.FIELD_TEST
        else:
            return SignalType.MILESTONE

    def _assess_importance(self, title: str, companies: List[str]) -> str:
        """Assess importance of an event"""
        if len(companies) > 2:
            return "high"
        elif len(companies) > 0:
            return "medium"
        else:
            return "low"

    def _extract_contract_value(self, text: str) -> float:
        """Extract contract value from text"""
        # Look for dollar amounts
        pattern = r'\$([0-9,]+(?:\.[0-9]+)?)\s*(?:million|billion)?'
        match = re.search(pattern, text, re.IGNORECASE)

        if match:
            value_str = match.group(1).replace(',', '')
            value = float(value_str)

            if "billion" in text.lower():
                value *= 1_000_000_000
            elif "million" in text.lower():
                value *= 1_000_000

            return value

        return 0

    def _identify_domain(self, text: str) -> str:
        """Identify technology domain from text"""
        domains = []

        for domain, keywords in self.signal_keywords.items():
            if any(keyword.lower() in text for keyword in keywords):
                domains.append(domain)

        return ", ".join(domains) if domains else "defense_general"

    def _extract_company_affiliations(self, authors: List) -> List[str]:
        """Extract company affiliations from author list"""
        companies = []

        # Check if any tracked companies appear in affiliations
        for author in authors:
            if isinstance(author, dict):
                affiliation = author.get('affiliation', '')
            else:
                affiliation = str(author)

            for ticker, info in self.tracked_companies.items():
                if info["name"].lower() in affiliation.lower():
                    companies.append(ticker)

        return companies

    def _parse_date(self, date_str: str) -> datetime:
        """Parse date string to datetime"""
        try:
            from dateutil import parser
            return parser.parse(date_str, default=datetime.now(timezone.utc))
        except:
            return datetime.now(timezone.utc)

    def generate_alert_summary(self) -> Dict[str, Any]:
        """Generate summary of important events"""
        events = self.get_all_events(hours_back=24)  # Last 24 hours

        high_importance = [e for e in events if e.importance == "high"]
        by_company = {}

        for event in events:
            for company in event.companies:
                if company not in by_company:
                    by_company[company] = []
                by_company[company].append(event)

        total_contract_value = sum(e.contract_value for e in events if e.contract_value)

        return {
            'total_events': len(events),
            'high_importance_count': len(high_importance),
            'companies_affected': list(by_company.keys()),
            'total_contract_value': total_contract_value,
            'top_events': [
                {
                    'title': e.title,
                    'companies': e.companies,
                    'importance': e.importance,
                    'type': e.signal_type.value
                }
                for e in high_importance[:5]
            ],
            'by_domain': self._group_by_domain(events)
        }

    def _group_by_domain(self, events: List[DARPAEvent]) -> Dict[str, int]:
        """Group events by technology domain"""
        domains = {}
        for event in events:
            domain = event.technology_domain
            domains[domain] = domains.get(domain, 0) + 1
        return domains

    def save_to_cache(self, events: List[DARPAEvent]):
        """Save events to cache"""
        cache_file = DARPA_CACHE_DIR / f"events_{datetime.now().strftime('%Y%m%d')}.json"

        data = {
            'updated_at': datetime.now(timezone.utc).isoformat(),
            'events': [
                {
                    **asdict(event),
                    'datetime': event.datetime.isoformat(),
                    'source': event.source.value,
                    'signal_type': event.signal_type.value
                }
                for event in events
            ]
        }

        with open(cache_file, 'w') as f:
            json.dump(data, f, indent=2)

        logger.info(f"Saved {len(events)} DARPA events to cache")


def main():
    """Test the DARPA events monitor"""
    monitor = DARPAEventsMonitor()

    print("\n=== DARPA Events Monitor ===")

    # Get recent events
    events = monitor.get_all_events(hours_back=168)  # Last week

    print(f"\nFound {len(events)} DARPA-related events")

    # Show sample events
    for event in events[:5]:
        print(f"\n{event.datetime.strftime('%Y-%m-%d')} - {event.title}")
        print(f"  Type: {event.signal_type.value}")
        print(f"  Companies: {', '.join(event.companies) if event.companies else 'None'}")
        print(f"  Domain: {event.technology_domain}")
        print(f"  Importance: {event.importance}")
        if event.contract_value:
            print(f"  Value: ${event.contract_value:,.0f}")

    # Generate summary
    print("\n=== Alert Summary (Last 24 Hours) ===")
    summary = monitor.generate_alert_summary()

    print(f"Total Events: {summary['total_events']}")
    print(f"High Importance: {summary['high_importance_count']}")
    print(f"Companies Affected: {', '.join(summary['companies_affected'])}")
    if summary['total_contract_value']:
        print(f"Total Contract Value: ${summary['total_contract_value']:,.0f}")

    if summary['top_events']:
        print("\nTop Events:")
        for event in summary['top_events']:
            print(f"  - {event['title']}")
            print(f"    Companies: {', '.join(event['companies'])}")


if __name__ == "__main__":
    main()