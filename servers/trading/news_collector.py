#!/usr/bin/env python3
"""
News Collector Module for Trading System
Fetches and processes news from Alpaca News API with sentiment analysis
"""

import os
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict
import asyncio
from pathlib import Path

# Alpaca SDK imports
try:
    from alpaca.data.historical.news import NewsClient
except ImportError:
    # Fallback for older versions
    from alpaca.data import NewsClient
from alpaca.data.requests import NewsRequest
from alpaca.data.live import StockDataStream

# For sentiment analysis
from transformers import pipeline

# Data processing
import pandas as pd
import numpy as np

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get project root
PROJECT_ROOT = Path(__file__).parent.parent.parent.absolute()
NEWS_CACHE_DIR = PROJECT_ROOT / "data" / "news"
NEWS_CACHE_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class NewsItem:
    """Structured news item with sentiment"""
    symbol: str
    headline: str
    summary: str
    author: str
    created_at: datetime
    updated_at: datetime
    url: str
    id: str
    source: str
    sentiment_score: float = 0.0
    sentiment_label: str = "NEUTRAL"
    relevance_score: float = 0.0


class NewsCollector:
    """Collects and processes news from Alpaca API"""

    def __init__(self, api_key: str = None, secret_key: str = None):
        """Initialize with Alpaca credentials"""
        self.api_key = api_key or os.getenv("ALPACA_API_KEY")
        self.secret_key = secret_key or os.getenv("ALPACA_SECRET_KEY")

        # Initialize News client with API keys
        if self.api_key and self.secret_key:
            try:
                self.client = NewsClient(self.api_key, self.secret_key)
                logger.info("News client initialized with API keys")
            except Exception as e:
                logger.error(f"Failed to initialize News client: {e}")
                self.client = None
        else:
            logger.warning("API keys not found - news features disabled")
            self.client = None

        # Initialize sentiment analyzer (lazy loaded)
        self._sentiment_pipeline = None

        # Cache for news items
        self.news_cache: Dict[str, List[NewsItem]] = {}

        logger.info("NewsCollector initialized (client available: %s)", self.client is not None)

    @property
    def sentiment_pipeline(self):
        """Lazy load sentiment analysis pipeline"""
        if self._sentiment_pipeline is None:
            try:
                # Use a financial-specific model if available
                self._sentiment_pipeline = pipeline(
                    "sentiment-analysis",
                    model="ProsusAI/finbert",
                    device=-1  # CPU
                )
                logger.info("Loaded FinBERT sentiment model")
            except:
                # Fallback to general sentiment model
                self._sentiment_pipeline = pipeline(
                    "sentiment-analysis",
                    device=-1  # CPU
                )
                logger.info("Loaded default sentiment model")
        return self._sentiment_pipeline

    def get_historical_news(
        self,
        symbols: List[str],
        start: datetime = None,
        end: datetime = None,
        limit: int = 50
    ) -> Dict[str, List[NewsItem]]:
        """
        Fetch historical news for symbols

        Args:
            symbols: List of stock symbols
            start: Start datetime (default: 7 days ago)
            end: End datetime (default: now)
            limit: Maximum news items per symbol

        Returns:
            Dict mapping symbols to lists of NewsItems
        """
        if start is None:
            start = datetime.now(timezone.utc) - timedelta(days=7)
        if end is None:
            end = datetime.now(timezone.utc)

        results = {}

        for symbol in symbols:
            try:
                # Check cache first
                cached_news = self.load_from_cache(symbol)
                if cached_news is not None:
                    logger.info(f"Using cached news for {symbol}: {len(cached_news)} items")
                    results[symbol] = cached_news
                    continue

                # Check if client is available
                if self.client is None:
                    logger.warning("Alpaca client not available - cannot fetch news")
                    results[symbol] = []
                    continue

                # Create news request
                logger.debug(f"Requesting news for {symbol} from {start} to {end}")
                request = NewsRequest(
                    symbols=symbol,
                    start=start,
                    end=end,
                    limit=limit,
                    sort="DESC"
                )

                # Fetch news
                news_data = self.client.get_news(request)

                # Process each news item
                news_items = []
                for item in news_data:
                    news_item = self._process_news_item(item, symbol)
                    if news_item:
                        news_items.append(news_item)

                # Save to cache if we got data
                if news_items:
                    self.save_to_cache(symbol, news_items)

                results[symbol] = news_items
                logger.info(f"Fetched {len(news_items)} news items for {symbol}")

            except Exception as e:
                logger.error(f"Error fetching news for {symbol}: {e}")
                logger.error(f"Error type: {type(e).__name__}")
                # Try to use cache as fallback
                cached_news = self.load_from_cache(symbol)
                if cached_news:
                    logger.info(f"Using stale cache for {symbol} due to API error")
                    results[symbol] = cached_news
                else:
                    results[symbol] = []

        return results

    def _process_news_item(self, item: Any, symbol: str) -> Optional[NewsItem]:
        """Process raw news item from Alpaca"""
        try:
            # Handle both object and tuple formats from Alpaca
            if isinstance(item, tuple) and len(item) >= 2:
                # Item is a tuple (symbol, news_object)
                item = item[1] if len(item) > 1 else item[0]

            # Extract text for sentiment analysis
            text = f"{item.headline}. {item.summary[:200] if item.summary else ''}"

            # Analyze sentiment
            sentiment = self._analyze_sentiment(text)

            # Create NewsItem
            news_item = NewsItem(
                symbol=symbol,
                headline=item.headline,
                summary=item.summary or "",
                author=item.author or "Unknown",
                created_at=item.created_at,
                updated_at=item.updated_at,
                url=item.url or "",
                id=item.id,
                source="Benzinga",  # Alpaca news is from Benzinga
                sentiment_score=sentiment['score'],
                sentiment_label=sentiment['label'],
                relevance_score=self._calculate_relevance(item, symbol)
            )

            return news_item

        except Exception as e:
            logger.error(f"Error processing news item: {e}")
            return None

    def _analyze_sentiment(self, text: str) -> Dict[str, Any]:
        """
        Analyze sentiment of text

        Returns:
            Dict with 'label' (POSITIVE/NEGATIVE/NEUTRAL) and 'score' (0-1)
        """
        try:
            # Truncate text if too long
            text = text[:512]

            # Get sentiment
            results = self.sentiment_pipeline(text)
            result = results[0]

            # Map FinBERT labels if using that model
            label_map = {
                'positive': 'POSITIVE',
                'negative': 'NEGATIVE',
                'neutral': 'NEUTRAL'
            }

            label = result['label'].upper()
            if label.lower() in label_map:
                label = label_map[label.lower()]

            # Convert score to -1 to 1 range for negative/positive
            score = result['score']
            if label == 'NEGATIVE':
                score = -score
            elif label == 'NEUTRAL':
                score = 0

            return {
                'label': label,
                'score': score
            }

        except Exception as e:
            logger.error(f"Sentiment analysis error: {e}")
            return {'label': 'NEUTRAL', 'score': 0.0}

    def _calculate_relevance(self, item: Any, symbol: str) -> float:
        """
        Calculate relevance score for news item

        Simple heuristic based on:
        - Symbol mentions in headline/summary
        - Recency of news
        - Source reliability
        """
        score = 0.5  # Base score

        try:
            # Check symbol mentions
            text = f"{item.headline} {item.summary or ''}"
            if symbol.upper() in text.upper():
                score += 0.2

            # Check recency (newer = more relevant)
            age_hours = (datetime.now(timezone.utc) - item.created_at).total_seconds() / 3600
            if age_hours < 1:
                score += 0.3
            elif age_hours < 6:
                score += 0.2
            elif age_hours < 24:
                score += 0.1

            # Cap at 1.0
            score = min(1.0, score)

        except Exception as e:
            logger.error(f"Relevance calculation error: {e}")

        return score

    def get_aggregated_sentiment(
        self,
        symbol: str,
        hours_back: int = 24
    ) -> Dict[str, Any]:
        """
        Get aggregated sentiment for a symbol over time period

        Returns:
            Dict with aggregated metrics
        """
        start = datetime.now(timezone.utc) - timedelta(hours=hours_back)
        news = self.get_historical_news([symbol], start=start, limit=100)

        if not news.get(symbol):
            return {
                'symbol': symbol,
                'sentiment_score': 0.0,
                'sentiment_label': 'NEUTRAL',
                'news_count': 0,
                'positive_count': 0,
                'negative_count': 0,
                'neutral_count': 0,
                'avg_relevance': 0.0,
                'trending': False
            }

        items = news[symbol]

        # Aggregate metrics
        sentiment_scores = [item.sentiment_score for item in items]
        relevance_scores = [item.relevance_score for item in items]

        positive_count = sum(1 for item in items if item.sentiment_label == 'POSITIVE')
        negative_count = sum(1 for item in items if item.sentiment_label == 'NEGATIVE')
        neutral_count = sum(1 for item in items if item.sentiment_label == 'NEUTRAL')

        # Weight by relevance
        weighted_sentiment = sum(
            item.sentiment_score * item.relevance_score
            for item in items
        ) / max(sum(relevance_scores), 1)

        # Determine overall sentiment
        if weighted_sentiment > 0.2:
            label = 'POSITIVE'
        elif weighted_sentiment < -0.2:
            label = 'NEGATIVE'
        else:
            label = 'NEUTRAL'

        # Check if trending (high news volume)
        trending = len(items) > 10

        return {
            'symbol': symbol,
            'sentiment_score': weighted_sentiment,
            'sentiment_label': label,
            'news_count': len(items),
            'positive_count': positive_count,
            'negative_count': negative_count,
            'neutral_count': neutral_count,
            'avg_relevance': np.mean(relevance_scores),
            'trending': trending,
            'latest_headlines': [item.headline for item in items[:3]]
        }

    def save_to_cache(self, symbol: str, news_items: List[NewsItem]):
        """Save news items to cache file"""
        cache_file = NEWS_CACHE_DIR / f"{symbol}_news.json"

        data = {
            'symbol': symbol,
            'updated_at': datetime.now(timezone.utc).isoformat(),
            'items': [asdict(item) for item in news_items]
        }

        # Convert datetime objects to strings
        for item in data['items']:
            item['created_at'] = item['created_at'].isoformat()
            item['updated_at'] = item['updated_at'].isoformat()

        with open(cache_file, 'w') as f:
            json.dump(data, f, indent=2)

        logger.info(f"Saved {len(news_items)} news items to cache for {symbol}")

    def load_from_cache(self, symbol: str) -> Optional[List[NewsItem]]:
        """Load news items from cache"""
        cache_file = NEWS_CACHE_DIR / f"{symbol}_news.json"

        if not cache_file.exists():
            return None

        try:
            with open(cache_file, 'r') as f:
                data = json.load(f)

            # Check if cache is recent (within 1 hour)
            updated_at = datetime.fromisoformat(data['updated_at'])
            if (datetime.now(timezone.utc) - updated_at).total_seconds() > 3600:
                return None

            # Convert back to NewsItem objects
            items = []
            for item_data in data['items']:
                item_data['created_at'] = datetime.fromisoformat(item_data['created_at'])
                item_data['updated_at'] = datetime.fromisoformat(item_data['updated_at'])
                items.append(NewsItem(**item_data))

            logger.info(f"Loaded {len(items)} news items from cache for {symbol}")
            return items

        except Exception as e:
            logger.error(f"Error loading cache for {symbol}: {e}")
            return None

    async def stream_news_async(self, symbols: List[str], callback):
        """
        Stream real-time news for symbols (async)

        Args:
            symbols: List of symbols to monitor
            callback: Async function to call with news items
        """
        stream = StockDataStream(self.api_key, self.secret_key)

        async def news_handler(data):
            """Handle incoming news"""
            try:
                # Process news item
                for symbol in symbols:
                    if symbol in str(data):
                        news_item = self._process_news_item(data, symbol)
                        if news_item:
                            await callback(news_item)
            except Exception as e:
                logger.error(f"Error handling news stream: {e}")

        # Subscribe to news
        for symbol in symbols:
            stream.subscribe_news(news_handler, symbol)

        # Run stream
        await stream.run()


def main():
    """Test the news collector"""
    from dotenv import load_dotenv
    load_dotenv()

    collector = NewsCollector()

    # Test symbols
    symbols = ['AAPL', 'TSLA', 'NVDA']

    # Get historical news
    print("\n=== Historical News ===")
    news = collector.get_historical_news(symbols, limit=5)

    for symbol, items in news.items():
        print(f"\n{symbol}: {len(items)} news items")
        for item in items[:2]:  # Show first 2
            print(f"  - {item.headline[:80]}")
            print(f"    Sentiment: {item.sentiment_label} ({item.sentiment_score:.2f})")
            print(f"    Relevance: {item.relevance_score:.2f}")

    # Get aggregated sentiment
    print("\n=== Aggregated Sentiment ===")
    for symbol in symbols:
        sentiment = collector.get_aggregated_sentiment(symbol, hours_back=24)
        print(f"\n{symbol}:")
        print(f"  Overall: {sentiment['sentiment_label']} ({sentiment['sentiment_score']:.2f})")
        print(f"  News count: {sentiment['news_count']}")
        print(f"  Distribution: +{sentiment['positive_count']} / "
              f"-{sentiment['negative_count']} / "
              f"={sentiment['neutral_count']}")
        print(f"  Trending: {sentiment['trending']}")
        if sentiment.get('latest_headlines'):
            print(f"  Latest: {sentiment['latest_headlines'][0][:60]}...")


if __name__ == "__main__":
    main()