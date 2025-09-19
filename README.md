# MCP Servers Collection

Personal MCP (Model Context Protocol) servers for AI assistants.

## Quick Start

```bash
# Clone and setup
git clone git@github.com:LoriPickering/mcps.git
cd mcps
make quickstart

# Configure Alpaca API keys
cp .env.example .env
# Edit .env with your keys from https://app.alpaca.markets/

# Start trading data collector
make run
```

## Available Servers

### 1. Trading Signals Server (`servers/trading/`)
Real-time market indicators and signals via Alpaca Markets.

**Features:**
- Technical indicators (EMA, MACD, RSI, Bollinger Bands, VWAP)
- 24/7 crypto + stock market data
- Signal detection and alerts
- Historical data storage for ML training

**MCP Tools:**
- `get_signals` - Get indicators for any symbol
- `get_watchlist` - Monitor your portfolio
- `check_market_status` - Market hours info

## Setup for AI Assistants

### Claude Desktop
```json
// ~/Library/Application Support/Claude/claude_desktop_config.json
{
  "mcpServers": {
    "chart-signals": {
      "command": "/path/to/mcps/.venv/bin/python",
      "args": ["/path/to/mcps/servers/trading/mcp_server_integrated.py"]
    }
  }
}
```

### ChatGPT / Other
See [docs/MCP_API_SPEC.md](docs/MCP_API_SPEC.md) for JSON-RPC protocol details.

## Project Structure

```
mcps/
├── servers/           # MCP servers
│   └── trading/       # Trading signals server
├── data/              # Historical market data (gitignored)
├── docs/              # Documentation
├── scripts/           # Utilities
├── watchlist.txt      # Symbols to monitor
└── Makefile           # Common commands
```

## Commands

- `make run` - Start data collection
- `make install` - Install dependencies
- `make clean` - Remove cache/temp files

## Adding New Servers

1. Create `servers/your-server/`
2. Implement MCP protocol (see existing examples)
3. Update this README

## License

MIT - Personal use