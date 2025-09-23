# Trading Signals Server

Real-time market data and technical indicators via Alpaca Markets.

## Files

- `ta_server_full.py` - Main data collector (WebSocket + storage)
- `mcp_server_integrated.py` - MCP interface for AI assistants
- `legacy/` - Archived legacy server implementations

## Usage

```bash
# Start data collection (run this continuously)
make run

# Test MCP server manually
make run-trading-mcp
```

## Data Flow

1. Alpaca WebSocket → `ta_server_full.py` → Parquet files
2. AI Assistant → `mcp_server_integrated.py` → Read parquet → Return signals

## Configuration

- Symbols: `watchlist.txt`
- API Keys: `.env`
- Storage: `data/` directory