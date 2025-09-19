# MCP Chart Signals Project Summary

## Project Overview
Real-time trading indicators and signals server using Model Context Protocol (MCP) for AI assistants, with Alpaca Markets integration for live market data.

## Current Architecture

### Files Structure
```
mcps/
├── ta_server_full.py      # Main FastAPI server with Alpaca real-time data
├── mcp_server.py          # MCP protocol wrapper for Claude Desktop
├── watchlist.txt          # Stock/crypto symbols to monitor
├── .env                   # Alpaca API credentials
├── data/                  # Historical data storage
│   ├── stocks/1min/*.parquet
│   └── crypto/1min/*.parquet
└── pyproject.toml         # Dependencies
```

### Key Components

1. **Data Collection (ta_server_full.py)**
   - Connects to Alpaca WebSocket for real-time bars
   - Handles both stocks and 24/7 crypto
   - Stores data in parquet files for ML training
   - Maintains in-memory buffer for real-time signals
   - Auto-subscribes from watchlist.txt on startup

2. **MCP Integration (mcp_server.py)**
   - JSON-RPC protocol over stdin/stdout
   - Exposes tools: get_signals, get_watchlist, check_market_status
   - Connected to Claude Desktop

3. **Technical Indicators**
   - EMA (9), SMA (10)
   - MACD (12,26,9)
   - RSI (14)
   - Bollinger Bands (20,2)
   - Signal crossings detection

## Current Status

### Working
- ✅ Real-time stock data (market hours + after-hours)
- ✅ 24/7 crypto data (BTC/USD, ETH/USD)
- ✅ Parquet storage for historical data
- ✅ MCP server connected to Claude Desktop
- ✅ 18 symbols streaming successfully

### Watchlist
**Stocks**: SPY, QQQ, IWM, AAPL, MSFT, GOOGL, AMZN, META, NVDA, TSLA, BBAI, RIOT, NVDX, SMR, APLD, SOUN, SERV, ACHR, BITQ, UEC

**Crypto**: BTC, ETH

### Issues Fixed
- Crypto symbol format (BTCUSD → BTC/USD for Alpaca)
- Parquet file paths for crypto (/ in symbol names)
- MCP protocol version matching

## API Keys
Using Alpaca Paper Trading API (credentials in .env)

## Dependencies
- alpaca-py (market data)
- pandas, pandas-ta (technical analysis)
- fastapi, uvicorn (web server)
- pyarrow (parquet storage)
- mcp (Model Context Protocol)

## How to Run
```bash
# Install dependencies
make install

# Run full server with data collection
make run

# Server runs on http://localhost:8742
# MCP server auto-starts via Claude Desktop
```

## Next Steps
- Integrate real Alpaca data into MCP server (currently using mock data)
- Add more sophisticated trading signals
- Implement backtesting capabilities
- Add position management tools