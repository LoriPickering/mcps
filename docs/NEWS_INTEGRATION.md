# News Integration with Trading Signals

## Overview

The MCP Trading System now includes real-time news sentiment analysis to enhance trading signals. This feature integrates Alpaca's News API with technical indicators to provide a more comprehensive market view.

## Features

### 1. Real-time News Collection
- Fetches news from Alpaca News API (Benzinga source)
- Historical news data back to 2015
- Real-time streaming capabilities
- Automatic caching to reduce API calls

### 2. Sentiment Analysis
- Uses FinBERT model optimized for financial text
- Provides sentiment scores (-1 to 1)
- Labels: POSITIVE, NEGATIVE, NEUTRAL
- Weighted by relevance and recency

### 3. Signal Enhancement
- News sentiment influences trend state interpretation
- Conflicting signals (news vs technicals) marked as "mixed"
- Strong news can confirm or contradict technical indicators
- Trending detection based on news volume

## API Response Structure

The `get_signals` response now includes a `news` field:

```json
{
  "ready": true,
  "symbol": "AAPL",
  "trend_state": "bullish",
  "news": {
    "enabled": true,
    "sentiment": {
      "symbol": "AAPL",
      "sentiment_score": 0.6,
      "sentiment_label": "POSITIVE",
      "news_count": 15,
      "positive_count": 10,
      "negative_count": 2,
      "neutral_count": 3,
      "avg_relevance": 0.75,
      "trending": true,
      "latest_headlines": [
        "Apple announces record iPhone sales",
        "Analysts upgrade Apple price target"
      ]
    }
  }
}
```

## Trend State Adjustment Logic

The system adjusts trend state based on news sentiment:

| Technical Trend | News Sentiment | Score > 0.5 | Result |
|----------------|----------------|-------------|---------|
| Bullish | Positive | Yes | Bullish (confirmed) |
| Bearish | Negative | Yes | Bearish (confirmed) |
| Bullish | Negative | Yes | Mixed (conflict) |
| Bearish | Positive | Yes | Mixed (conflict) |
| Mixed | Positive | Yes | Bullish (news decides) |
| Mixed | Negative | Yes | Bearish (news decides) |

## Configuration

### Required Environment Variables
```bash
ALPACA_API_KEY=your_alpaca_api_key
ALPACA_SECRET_KEY=your_alpaca_secret_key
```

### Dependencies
- `alpaca-py`: Alpaca API client
- `transformers`: For sentiment analysis
- `torch`: Required by transformers
- `sentencepiece`: For some tokenizers

## Usage Examples

### Python Integration
```python
from servers.trading.news_collector import NewsCollector

# Initialize collector
collector = NewsCollector()

# Get aggregated sentiment for last 24 hours
sentiment = collector.get_aggregated_sentiment("AAPL", hours_back=24)
print(f"Sentiment: {sentiment['sentiment_label']} ({sentiment['sentiment_score']:.2f})")
print(f"News count: {sentiment['news_count']}")
print(f"Trending: {sentiment['trending']}")

# Get historical news
news = collector.get_historical_news(
    ["AAPL", "TSLA"],
    start=datetime.now(timezone.utc) - timedelta(days=7),
    limit=10
)
```

### MCP Tool Usage
```javascript
// Via Claude Desktop or MCP client
const result = await mcp.call('get_signals', {
  symbol: 'AAPL',
  timeframe: '1min'
});

console.log(`Trend: ${result.trend_state}`);
console.log(`News sentiment: ${result.news.sentiment.sentiment_label}`);
console.log(`News score: ${result.news.sentiment.sentiment_score}`);
```

## Caching

News data is cached locally to reduce API calls:
- Cache location: `data/news/`
- Cache duration: 1 hour
- Format: JSON files per symbol

## Limitations

1. **API Rate Limits**: Alpaca News API has rate limits
2. **Model Loading**: First sentiment analysis may be slow due to model loading
3. **Language**: Only English news is processed
4. **Source**: Currently only Benzinga news (via Alpaca)

## Future Enhancements

- [ ] Additional news sources
- [ ] Custom sentiment models for specific sectors
- [ ] News event detection (earnings, FDA approvals, etc.)
- [ ] News-based alerts and notifications
- [ ] Historical backtesting with news data
- [ ] Multi-language support

## Testing

Run the news integration tests:
```bash
pytest tests/test_news_integration.py -v
```

For testing with real API:
```bash
# Requires ALPACA_API_KEY and ALPACA_SECRET_KEY
pytest tests/test_news_integration.py::TestNewsIntegration::test_news_collector_integration -v
```

## Troubleshooting

### News Not Available
If news data shows as unavailable:
1. Check API keys are set correctly
2. Verify Alpaca account has data access
3. Check network connectivity
4. Review logs for API errors

### Slow Performance
If sentiment analysis is slow:
1. First run downloads the model (one-time)
2. Consider using GPU if available
3. Reduce news limit parameter
4. Use caching effectively

### Conflicting Signals
When technical and news signals conflict:
1. System marks trend as "mixed"
2. Consider both signals in decision
3. Strong news (|score| > 0.5) has more weight
4. Check latest headlines for context