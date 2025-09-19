# Alpaca Setup Guide for MCP Chart Signals

## Quick Start

### 1. Get Alpaca API Keys

1. Sign up at [Alpaca Markets](https://app.alpaca.markets/signup)
2. After login, go to the API section
3. **For testing (recommended):** Generate Paper Trading API keys
4. **For live trading:** Generate Live Trading API keys (use with extreme caution!)

### 2. Configure Environment

Create a `.env` file in the project root:

```bash
cp .env.example .env
```

Edit `.env` and add your Alpaca credentials:

```env
ALPACA_API_KEY=your_api_key_here
ALPACA_SECRET_KEY=your_secret_key_here
ALPACA_BASE_URL=https://paper-api.alpaca.markets  # or https://api.alpaca.markets for live
```

### 3. Install Dependencies

```bash
make install
# or
uv pip install -e .
```

### 4. Run the Server

```bash
make run
# or
python ta_server_alpaca.py
```

## Using the Server

### Subscribe to Symbols

Once the server is running, subscribe to real-time data:

```bash
curl -X POST http://localhost:8742/subscribe \
  -H "Content-Type: application/json" \
  -d '{"symbols": ["AAPL", "TSLA", "SPY"]}'
```

### Check Status

```bash
curl http://localhost:8742/status
```

### MCP Tools Available

The server exposes two MCP tools:

1. **get_signals(symbol, timeframe)** - Get technical indicators and crossing signals
   - Parameters:
     - symbol: Stock ticker (e.g., "AAPL")
     - timeframe: "1Min", "5Min", "15Min", or "1Hour"
   - Returns: Price, indicators (EMA, MA, MACD, RSI), and signal crossings

2. **get_watchlist()** - Get all subscribed symbols with their latest signals
   - Returns: List of symbols with current price, RSI, and active signals

## How It Works

1. **Real-time Data**: Alpaca streams live market data via WebSocket
2. **Indicator Calculation**: Server calculates technical indicators on incoming bars
3. **Signal Detection**: Identifies key events (MACD crossings, RSI levels, EMA breaks)
4. **MCP Integration**: Exposes indicators as tools for LLMs to analyze

## Important Notes

- **Market Hours**: Real-time data only available during market hours (9:30 AM - 4:00 PM ET)
- **Extended Hours**: Configure Alpaca subscription for pre/post-market data if needed
- **Rate Limits**: Free tier has limits on concurrent connections
- **Paper Trading**: Always test with paper trading before using real money

## Troubleshooting

- **No data received**: Check if markets are open
- **Authentication failed**: Verify API keys in .env file
- **Connection errors**: Ensure you're using the correct BASE_URL for your API keys