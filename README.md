# MCP Chart Signals

Real-time trading indicators and signals via Model Context Protocol (MCP).

## Features

- Real-time market data from Alpaca Markets
- Technical indicators: EMA, MA, MACD, RSI
- Signal detection for trading decisions
- MCP tools for LLM integration

## Quick Start

1. Set up Alpaca API credentials in `.env`:
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

2. Install dependencies:
   ```bash
   make quickstart
   ```

3. Run the server:
   ```bash
   make run
   ```

4. Subscribe to symbols:
   ```bash
   curl -X POST http://localhost:8742/subscribe \
     -H "Content-Type: application/json" \
     -d '{"symbols": ["AAPL", "TSLA", "SPY"]}'
   ```

See [ALPACA_SETUP.md](ALPACA_SETUP.md) for detailed setup instructions.

## MCP Tools

- `get_signals(symbol, timeframe)` - Get indicators and crossing signals
- `get_watchlist()` - Get all subscribed symbols with latest signals

## License

MIT