# MCP Chart Signals API Specification v1.0

## 1. Tool Contract (Exact I/O)

### Available Methods

#### get_signals
```typescript
get_signals(symbol: string, timeframe: "1min" | "5min" | "15min" | "1hour") -> SignalResponse
```

**Request:**
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "get_signals",
    "arguments": {
      "symbol": "AAPL",
      "timeframe": "1min"
    }
  }
}
```

**Response Schema:**
```json
{
  "ready": true,
  "symbol": "AAPL",
  "asset_type": "stock",  // "stock" | "crypto"
  "tf": "1min",
  "snapshot": {
    "price": 245.52,
    "ema9": 245.48,
    "ma10": 245.51,
    "macd": 0.4406,
    "signal": 0.4511,
    "hist": -0.0105,
    "rsi": 60.28,
    "bb_upper": 246.10,
    "bb_middle": 245.50,
    "bb_lower": 244.90,
    "time": "2025-09-19T18:59:00+00:00"
  },
  "crossings": {
    "macd_cross_up": false,
    "macd_cross_dn": false,
    "ema_support_lost": false,
    "ema_reclaim": false,
    "rsi_overbought": false,
    "rsi_oversold": false,
    "bb_squeeze": false,
    "bb_breakout_up": false,
    "bb_breakout_dn": false
  }
}
```

**Error Response (insufficient data):**
```json
{
  "ready": false,
  "reason": "insufficient bars (need 35+)"
}
```

#### get_watchlist
```typescript
get_watchlist() -> WatchlistResponse
```

**Response:**
```json
{
  "watchlist": {
    "stocks": [
      {
        "symbol": "AAPL",
        "price": 245.52,
        "rsi": 60.28,
        "signals": ["macd_cross_up"]
      }
    ],
    "crypto": [
      {
        "symbol": "BTC/USD",
        "price": 98234.50,
        "rsi": 72.1,
        "signals": ["rsi_overbought", "bb_breakout_up"]
      }
    ]
  },
  "timestamp": "2025-09-19T19:00:00+00:00",
  "market_hours": {
    "stocks": "9:30 AM - 4:00 PM ET (weekdays)",
    "crypto": "24/7"
  }
}
```

#### check_market_status
```typescript
check_market_status() -> MarketStatusResponse
```

**Response:**
```json
{
  "stocks": {
    "open": true,
    "session": "regular",  // "premarket" | "regular" | "afterhours" | "closed"
    "next_open": "Tomorrow 9:30 AM ET",
    "current_time_et": "3:00 PM ET"
  },
  "crypto": {
    "open": true,
    "note": "24/7 trading"
  },
  "timestamp": "2025-09-19T19:00:00+00:00"
}
```

#### get_storage_info
```typescript
get_storage_info() -> StorageInfoResponse
```

**Response:**
```json
{
  "data_directory": "/Users/loripickering/Projects/mcps/data",
  "stored_symbols": {
    "stocks": ["AAPL", "TSLA", "NVDA"],
    "crypto": ["BTC_USD", "ETH_USD"]
  },
  "total_size_mb": 124.5
}
```

## 2. Symbol & Timeframe Normalization

### Symbol Format
- **Stocks**: Standard tickers (e.g., "AAPL", "TSLA", "SPY")
- **Crypto**: Alpaca format with slash (e.g., "BTC/USD", "ETH/USD")
- **File storage**: Crypto slashes replaced with underscores (e.g., "BTC_USD_2025-09.parquet")

### Supported Timeframes
- `1min` - 1 minute bars (primary, real-time from Alpaca)
- `5min` - 5 minute bars (aggregated from 1min)
- `15min` - 15 minute bars (aggregated from 1min)
- `1hour` - 1 hour bars (aggregated from 1min)

### Time Conventions
- **All timestamps**: UTC with timezone info (ISO 8601)
- **Bar timestamp**: Represents bar OPEN time
- **Example**: `2025-09-19T18:59:00+00:00` = bar from 18:59:00 to 18:59:59

## 3. Deterministic Crossing Logic

### MACD Crossing
- Computed on **closed bars only**
- `macd_cross_up`: `prev["macd"] <= prev["signal"] AND last["macd"] > last["signal"]`
- `macd_cross_dn`: `prev["macd"] >= prev["signal"] AND last["macd"] < last["signal"]`

### RSI Levels
- `rsi_overbought`: `last["rsi"] >= 70` (inclusive)
- `rsi_oversold`: `last["rsi"] <= 30` (inclusive)

### EMA Support
- `ema_support_lost`: `prev["close"] >= prev["ema9"] AND last["close"] < last["ema9"]`
- `ema_reclaim`: `prev["close"] <= prev["ema9"] AND last["close"] > last["ema9"]`
- Based on **close price** vs EMA, not intrabar

### Bollinger Bands
- `bb_squeeze`: `(bb_upper - bb_lower) / bb_middle < 0.04`
- `bb_breakout_up`: `last["close"] > last["bb_upper"]`
- `bb_breakout_dn`: `last["close"] < last["bb_lower"]`

## 4. Indicator Parameters

- **EMA**: 9 periods
- **SMA**: 10 periods
- **MACD**: Fast=12, Slow=26, Signal=9
- **RSI**: 14 periods
- **Bollinger Bands**: 20 periods, 2 standard deviations

## 5. Error Handling

### Standard Errors
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "error": {
    "code": -32001,
    "message": "Insufficient data",
    "data": {
      "symbol": "AAPL",
      "bars_available": 10,
      "bars_needed": 35
    }
  }
}
```

### Error Codes
- `-32001`: Insufficient data
- `-32002`: Invalid symbol
- `-32003`: Invalid timeframe
- `-32004`: Market data unavailable
- `-32601`: Method not found

## 6. Real-time Notifications (Future)

### Alert Subscription (Planned)
```json
{
  "method": "subscribe_alerts",
  "params": {
    "symbol": "AAPL",
    "timeframe": "1min",
    "conditions": [
      {"type": "macd_cross", "direction": "up"},
      {"type": "rsi_oversold"}
    ],
    "throttle_ms": 5000
  }
}
```

### Alert Notification Format (Planned)
```json
{
  "jsonrpc": "2.0",
  "method": "signals.alert",
  "params": {
    "subscription_id": "sub_123",
    "symbol": "AAPL",
    "timeframe": "1min",
    "triggered": ["macd_cross_up"],
    "snapshot": {
      "price": 245.52,
      "macd": 0.45,
      "signal": 0.44,
      "rsi": 31.2
    },
    "timestamp": "2025-09-19T19:00:00+00:00"
  }
}
```

## 7. Version & Capabilities

### get_capabilities (Current)
```json
{
  "version": "1.0.0",
  "protocol": "2025-06-18",
  "indicators": ["EMA9", "SMA10", "MACD(12,26,9)", "RSI14", "BB(20,2)"],
  "timeframes": ["1min", "5min", "15min", "1hour"],
  "asset_types": ["stocks", "crypto"],
  "data_source": "Alpaca Markets",
  "storage": "parquet",
  "max_bars_in_memory": 3000
}
```

## 8. Security & Architecture

- **Protocol**: JSON-RPC 2.0 over stdio (local only)
- **No HTTP exposure** for MCP server
- **Credentials**: Stored in environment variables
- **Data flow**: Alpaca WebSocket → Memory buffer → Parquet files
- **FastAPI server**: Separate process on port 8742 (optional, for webhooks)

## 9. Current Watchlist

### Stocks (20)
SPY, QQQ, IWM, AAPL, MSFT, GOOGL, AMZN, META, NVDA, TSLA, BBAI, RIOT, NVDX, SMR, APLD, SOUN, SERV, ACHR, BITQ, UEC

### Crypto (2)
BTC/USD, ETH/USD

## 10. Implementation Notes

### Data Availability
- **Stocks**: Market hours (9:30 AM - 4:00 PM ET) + extended hours
- **Crypto**: 24/7 continuous
- **Min bars needed**: 35 for all indicators
- **Storage**: Last 3000 bars in memory per symbol

### Aggregation
- 1min bars are primary (from Alpaca)
- Larger timeframes aggregated using pandas resample:
  - Open: first
  - High: max
  - Low: min
  - Close: last
  - Volume: sum

### File Paths
- Stocks: `data/stocks/1min/{SYMBOL}_{YYYY-MM}.parquet`
- Crypto: `data/crypto/1min/{SYMBOL_USD}_{YYYY-MM}.parquet`

---

## Quick Start for ChatGPT

1. **Test connection:**
```json
{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"check_market_status","arguments":{}}}
```

2. **Get signals:**
```json
{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"get_signals","arguments":{"symbol":"AAPL","timeframe":"1min"}}}
```

3. **Check watchlist:**
```json
{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"get_watchlist","arguments":{}}}
```