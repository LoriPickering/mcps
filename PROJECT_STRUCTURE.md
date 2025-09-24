# Project Structure - MCP Trading System

## 📁 Directory Organization

```
mcps/
├── 📊 data/                    # All data storage
│   ├── stocks/                 # Historical stock data (parquet files)
│   │   ├── 1min/
│   │   ├── 5min/
│   │   ├── 15min/
│   │   └── 1hour/
│   ├── crypto/                 # Cryptocurrency data
│   ├── darpa_events/           # DARPA event cache
│   ├── events/                 # Economic events data
│   └── news/                   # News sentiment data
│
├── 📚 docs/                    # Documentation
│   ├── reference/              # Reference materials
│   │   └── DARPA_like_investments.pdf
│   ├── ARCHITECTURE.md         # System architecture
│   ├── MCP_SERVER_ARCHITECTURE.md
│   ├── DARPA_MONITORING_STATUS.md
│   ├── MACRO_EVENTS_STATUS.md
│   └── ...                     # Other documentation
│
├── 🛠️ scripts/                  # Utility scripts
│   ├── monitoring/             # Monitoring daemons
│   │   └── darpa_monitor_daemon.py
│   ├── data_collection/        # Data collection scripts
│   │   └── collect_darpa_historical.py
│   ├── mcp_rest_api.py         # REST API wrapper
│   └── run_tests.py            # Test runner
│
├── 🖥️ servers/                  # MCP servers
│   └── trading/
│       ├── mcp_server_integrated.py    # Main MCP server
│       ├── news_collector.py           # News integration
│       ├── macro_events_tracker.py     # Fed/economic events
│       ├── darpa_events_monitor.py     # DARPA monitoring
│       └── legacy/                      # Old versions
│
├── 🧪 tests/                   # Test suite
│   ├── api/                    # API tests
│   │   └── test_rest_api.py
│   ├── darpa/                  # DARPA-specific tests
│   │   ├── test_darpa_availability.py
│   │   ├── test_darpa_feeds.py
│   │   └── test_darpa_with_sam.py
│   ├── integration/            # Integration tests
│   │   ├── test_mcp_darpa_integration.py
│   │   └── test_alpaca_quotes.py
│   └── unit tests...           # Unit tests
│
├── 📋 portfolio/               # Portfolio data
│   └── Holdings-22Sept2025.csv
│
├── 📝 Root Files (Clean!)
│   ├── README.md               # Project overview
│   ├── Makefile               # Build/test commands
│   ├── pyproject.toml         # Python project config
│   ├── watchlist.txt          # Stocks to monitor
│   ├── .env                   # API keys (private)
│   └── .gitignore             # Git ignore rules
```

## 🚀 Quick Start Commands

### Run the MCP Server (for Claude Desktop)
```bash
# Already configured in Claude Desktop config
# Runs automatically when Claude needs it
```

### Run REST API (for sharing with other agents)
```bash
python scripts/mcp_rest_api.py
```

### Run DARPA Monitor Daemon
```bash
python scripts/monitoring/darpa_monitor_daemon.py
```

### Collect Historical Data
```bash
python scripts/data_collection/collect_darpa_historical.py
```

### Run Tests
```bash
make test
# or
python scripts/run_tests.py
```

## 📊 Data Locations

- **Stock Data**: `data/stocks/[timeframe]/[SYMBOL]_[YYYY-MM].parquet`
- **DARPA Alerts**: `data/darpa_alerts.json`
- **Watchlist**: `watchlist.txt` (root)
- **Portfolio**: `portfolio/Holdings-22Sept2025.csv`

## 🔧 Configuration

- **API Keys**: `.env` file (never commit!)
- **Claude Desktop**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Python Dependencies**: `pyproject.toml`

## 📡 Server Endpoints

### MCP Protocol (Claude Desktop)
- Configured automatically via JSON-RPC

### REST API (Other Agents)
- `GET /api/signals/<symbol>` - Trading signals
- `GET /api/watchlist` - Watchlist with prices
- `GET /api/darpa/events` - DARPA frontier tech events
- `GET /api/macro/events` - Fed/economic events
- `POST /api/tickers/check` - Check ticker availability

## 🧪 Testing

```bash
# Run all tests
make test

# Run specific test category
pytest tests/darpa/
pytest tests/integration/
pytest tests/api/
```

## 📚 Documentation

- [Architecture Overview](docs/ARCHITECTURE.md)
- [MCP Server Guide](docs/MCP_SERVER_ARCHITECTURE.md)
- [DARPA Monitoring](docs/DARPA_MONITORING_STATUS.md)
- [Trading Roadmap](docs/TRADING_SYSTEM_ROADMAP.md)

## 🎯 Current Features

✅ **Trading Signals** - MACD, RSI, Bollinger Bands, VWAP
✅ **DARPA Monitoring** - Government contracts, research papers
✅ **Macro Events** - Fed speeches, economic data releases
✅ **News Sentiment** - FinBERT analysis of market news
✅ **Real-time Quotes** - All DARPA/frontier tech tickers
✅ **REST API** - Share with any HTTP client

## 🔮 Roadmap

- [ ] Backtesting framework
- [ ] Portfolio optimization
- [ ] Automated trading execution
- [ ] Advanced ML predictions
- [ ] Multi-asset correlation analysis