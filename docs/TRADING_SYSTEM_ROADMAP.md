# Trading System Development Roadmap

## Overview
Evolution path from current MCP signal server to full automated trading system with news integration and paper trading capabilities.

## Phase 1: Alert System Design

### Buy Signal Alerts

#### Current Triggers (Already Implemented)
- MACD golden cross (bullish)
- RSI oversold bounce (< 30 → rising)
- EMA reclaim (price crosses back above EMA9)
- Bollinger Band squeeze → breakout

#### Enhanced Buy Signals to Add
- **Volume Confirmation**: 2x average volume spike
- **Multi-Timeframe Alignment**: 1min + 5min + 15min all bullish
- **Momentum Divergence**: Price making lower lows, RSI making higher lows
- **Support Level Detection**: Bounce from key price levels
- **Market Context**: Only buy when SPY/QQQ trending up

### Sell Signal Planning (Exit Strategy)

#### Target Levels
- **Resistance Targets**: Previous highs, psychological levels ($100, $150)
- **Fibonacci Extensions**: 1.618x, 2.618x from entry
- **ATR-Based**: 2-3x Average True Range from entry
- **Percentage Targets**: Fixed 5%, 10%, 20% gain levels

#### Stop Loss Rules
- **Initial Stop**: Below support level or -2% from entry
- **Trailing Stop**: Follow EMA9 or 2x ATR below high
- **Time Stop**: Exit if no positive movement in X bars
- **Volatility Stop**: Widen in high volatility, tighten in low

#### Exit Indicators to Monitor
- MACD bearish divergence forming
- RSI entering overbought (>70) and turning down
- Volume declining on advances (exhaustion)
- Bollinger Band walking → mean reversion likely
- Negative news or sentiment shift

## Phase 2: Paper Trading Bot Architecture

### Core Components

#### 1. Position Manager
```python
class Position:
    - symbol: str
    - entry_price: float
    - entry_time: datetime
    - quantity: int
    - strategy_id: str
    - stop_loss: float
    - take_profit: float
    - current_pnl: float
```

**Features:**
- Track open positions with entry details
- Real-time P&L calculation
- Position sizing (Kelly Criterion, fixed %, volatility-based)
- Risk management (max positions, sector exposure limits)
- Trail stop management

#### 2. Strategy Engine
```python
class Strategy:
    - evaluate_entry(symbol, data) -> Signal
    - evaluate_exit(position, data) -> Signal
    - get_position_size(capital, volatility) -> float
    - backtest(historical_data) -> Performance
```

**Architecture:**
- Multiple strategies running in parallel
- Each strategy votes on buy/sell decisions
- Consensus mechanism or strategy rotation based on market regime
- Strategy performance tracking and auto-adjustment

#### 3. Order Simulator
- Simulate market/limit/stop orders
- Slippage modeling (0.01% for liquid, 0.1% for less liquid)
- Commission calculation ($0 for Alpaca)
- Partial fills for large orders
- Order timing optimization

#### 4. Performance Analytics
- **Trade Metrics**: Win rate, average win/loss, profit factor
- **Risk Metrics**: Sharpe ratio, Sortino ratio, max drawdown
- **Trade Journal**: Entry/exit reasoning, market conditions
- **Strategy Comparison**: A/B testing different approaches
- **Monte Carlo Simulation**: Confidence intervals for returns

## Phase 3: Trading Strategies

### 1. Momentum Scalping
```yaml
Entry: MACD cross + RSI > 50 + Volume spike
Target: 1-2% gain
Stop: 0.5% loss
Timeframe: 1-5 minute bars
Hold Time: 5-30 minutes
```

### 2. Trend Following
```yaml
Entry: EMA9 cross EMA20 + MACD confirmation
Target: Trail with EMA20
Stop: Below EMA20 or -3%
Timeframe: 15-60 minute bars
Hold Time: Hours to days
```

### 3. Mean Reversion
```yaml
Entry: RSI < 30 + Below BB lower + Support level
Target: Middle BB or EMA20
Stop: -2% or new low
Timeframe: 5-15 minute bars
Hold Time: 30 minutes to hours
```

### 4. Volume Breakout
```yaml
Entry: Price break + 3x average volume
Target: Previous high or resistance
Stop: Below breakout level
Timeframe: 1-5 minute bars
Hold Time: Minutes to hours
```

### 5. News Catalyst
```yaml
Entry: Positive news + Technical confirmation
Target: Multi-day momentum (5-10%)
Stop: Below news day low
Timeframe: Daily bars
Hold Time: 1-5 days
```

## Phase 4: News Integration

### Data Sources

#### Free/Affordable
1. **Alpaca News API** (Already Available!)
   - Real-time from Benzinga, Polygon
   - Sentiment scores included
   - Historical for backtesting
   - No additional cost

2. **Yahoo Finance**
   - RSS feeds per symbol
   - Earnings calendars
   - SEC filings
   - Free but delayed

3. **NewsAPI.org**
   - $0-450/month
   - Multiple sources
   - Good coverage
   - RESTful API

4. **Social Media**
   - Reddit API (wallstreetbets, stocks)
   - Twitter/X API (filtered streams)
   - Stocktwits API
   - High noise but early signals

#### Premium Options
- **Benzinga Pro**: ~$177/month, real-time squawk
- **Refinitiv**: Enterprise pricing
- **Bloomberg**: $2000+/month

### News Processing Pipeline

```
Collection → Deduplication → NLP Processing → Event Classification → Signal Generation
     ↓             ↓               ↓                  ↓                    ↓
  Raw Storage  Remove Dups  Sentiment Score  Earnings/M&A/FDA    Buy/Sell/Hold
```

### Event Categories

#### High Impact (Immediate Action)
- **Earnings**: Beat/miss, guidance change
- **FDA/Regulatory**: Approvals, rejections
- **M&A**: Acquisitions, buyouts, mergers
- **Legal**: Lawsuits, SEC investigations

#### Medium Impact (Monitor)
- **Analyst Changes**: Upgrades/downgrades
- **Insider Trading**: Buys/sells by executives
- **Product Launches**: New products, partnerships
- **Market Share**: Competitive wins/losses

#### Sentiment Indicators
- **Positive Momentum**: Multiple positive articles
- **Risk Flags**: Clustered negative news
- **Social Buzz**: Trending on Reddit/Twitter
- **Institutional**: 13F filings, large trades

### Integration with Signals

```python
def enhanced_buy_signal(symbol):
    technical_signal = get_signals(symbol)
    news_context = get_news_context(symbol, hours=24)

    if technical_signal['bullish']:
        if news_context['sentiment'] < -0.5:
            return "AVOID - Negative news override"
        elif news_context['sentiment'] > 0.5:
            return "STRONG BUY - News + technical alignment"
        else:
            return "BUY - Technical signal confirmed"
    return "HOLD"
```

## Implementation Timeline

### Month 1: Enhanced Alerts
- [ ] Add alert storage (SQLite)
- [ ] Implement alert conditions
- [ ] Create notification system (Discord/Telegram)
- [ ] Add news sentiment from Alpaca

### Month 2: Paper Trading
- [ ] Build position manager
- [ ] Create order simulator
- [ ] Implement basic strategies
- [ ] Add performance tracking

### Month 3: News Integration
- [ ] Connect Alpaca news API
- [ ] Add sentiment analysis
- [ ] Create event detection
- [ ] Correlate news with price

### Month 4: Strategy Development
- [ ] Backtest framework
- [ ] Strategy optimization
- [ ] Walk-forward analysis
- [ ] A/B testing system

### Month 5: Risk Management
- [ ] Position sizing algorithms
- [ ] Portfolio risk metrics
- [ ] Circuit breakers
- [ ] Drawdown protection

### Month 6: Production Ready
- [ ] Live trading connection
- [ ] Real-time dashboard
- [ ] Monitoring and alerts
- [ ] Performance reporting

## Risk Management Framework

### Position Sizing Methods
1. **Fixed Fractional**: 2% of capital per trade
2. **Kelly Criterion**: f = (p*b - q) / b
3. **Volatility Based**: Size = Risk$ / (ATR * multiplier)
4. **Risk Parity**: Equal risk contribution

### Portfolio Controls
- Maximum 10 concurrent positions
- Maximum 30% in one sector
- Maximum 5% in one position
- Correlation limits between positions
- Daily loss limit: -5%
- Weekly loss limit: -10%

### Circuit Breakers
- Pause after 3 consecutive losses
- Stop trading after -5% daily loss
- Reduce size by 50% in drawdown > 10%
- Increase size by 25% after 5 consecutive wins
- Time-based breaks (no trading first/last 15 min)

## Data Storage Enhancement

```
data/
├── market/
│   ├── stocks/
│   │   ├── 1min/
│   │   ├── 5min/
│   │   └── daily/
│   └── crypto/
├── news/
│   ├── raw/
│   │   ├── alpaca/
│   │   ├── yahoo/
│   │   └── social/
│   ├── processed/
│   │   ├── sentiment/
│   │   └── events/
│   └── correlations/
├── trades/
│   ├── paper/
│   │   ├── positions.db
│   │   └── orders.db
│   └── live/
└── analytics/
    ├── backtest_results/
    ├── strategy_performance/
    └── risk_metrics/
```

## New MCP Tools to Add

```python
# Alert Management
set_alert(symbol, condition, threshold, action)
get_alerts(active_only=True)
check_alerts() -> triggered_alerts[]

# Paper Trading
execute_paper_trade(symbol, side, quantity, strategy_id)
get_positions() -> positions[]
get_paper_performance() -> metrics{}

# News Integration
get_news_context(symbol, hours_back=24)
get_market_sentiment() -> sentiment_scores{}
get_earnings_calendar(days_ahead=7)

# Strategy Management
backtest_strategy(strategy_id, start_date, end_date)
get_strategy_performance(strategy_id)
optimize_parameters(strategy_id, param_ranges)

# Risk Management
get_portfolio_risk() -> risk_metrics{}
check_risk_limits() -> violations[]
calculate_position_size(symbol, strategy_id)
```

## Success Metrics

### Phase 1 (Alerts)
- Alert accuracy > 70%
- False positive rate < 20%
- Response time < 1 second

### Phase 2 (Paper Trading)
- Sharpe ratio > 1.5
- Win rate > 55%
- Max drawdown < 15%

### Phase 3 (With News)
- News-enhanced signals +20% better
- Avoid 90% of bad news events
- Catch 50% of positive catalysts

### Phase 4 (Live Trading)
- Consistent profitability
- Risk-adjusted returns > SPY
- Minimal manual intervention

## Key Decisions Needed

1. **Trading Style**: Scalping vs Swing vs Position trading?
2. **Universe**: Fixed watchlist vs dynamic scanning?
3. **Risk Level**: Conservative (base hits) vs Aggressive (home runs)?
4. **Automation Level**: Full auto vs semi-auto with confirmations?
5. **Capital Allocation**: Equal weight vs risk-based vs momentum-based?

## Next Steps

1. Review and prioritize features
2. Set up development environment for paper trading
3. Create database schema for alerts and positions
4. Begin Alpaca news API integration
5. Build first basic strategy for testing

---

*This document is a living roadmap and will be updated as the system evolves.*