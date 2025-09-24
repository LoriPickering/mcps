# MCP Server Architecture & Sharing Guide

## 📍 Where Everything Lives

### Main MCP Server
- **Location**: `/Users/loripickering/Projects/mcps/servers/trading/mcp_server_integrated.py`
- **Config**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Status**: Currently RUNNING (PID 83244 as of now)

### Supporting Modules
```
/servers/trading/
├── mcp_server_integrated.py      # Main MCP server
├── news_collector.py              # News sentiment analysis
├── macro_events_tracker.py        # Fed/economic events
├── darpa_events_monitor.py        # DARPA frontier tech tracking
└── legacy/
    └── mcp_server.py             # Original version
```

### Data Storage
```
/data/
├── stocks/
│   ├── 1min/      # 20 parquet files
│   ├── 5min/
│   ├── 15min/
│   └── 1hour/
├── crypto/
└── darpa_alerts.json  # High-importance DARPA alerts
```

## 🔄 How MCP Servers Run

### 1. **Claude Desktop Mode** (Current)
- **Trigger**: Claude Desktop starts the server when needed
- **Lifecycle**: Request → Start → Process → Response → May stay running
- **Data Collection**: Only when requested (not continuous)

### 2. **Daemon Mode** (Optional)
```bash
# Run continuously in background
python darpa_monitor_daemon.py

# Collects data every:
- DARPA events: 30 minutes
- Ticker prices: 4 hours
- Saves alerts to: data/darpa_alerts.json
```

### 3. **Manual Mode**
```bash
# Run the MCP server directly
python servers/trading/mcp_server_integrated.py

# Test specific functions
python test_darpa_availability.py
```

## 🌐 Sharing with Other Agents

### Option 1: REST API Wrapper (For ChatGPT/Other Apps)

Create `mcp_rest_api.py`:

```python
#!/usr/bin/env python3
"""REST API wrapper for MCP server - share with any agent"""

from flask import Flask, jsonify, request
from flask_cors import CORS
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from servers.trading.mcp_server_integrated import MCPServer

app = Flask(__name__)
CORS(app)  # Allow cross-origin requests
server = MCPServer()

@app.route('/api/signals/<symbol>')
def get_signals(symbol):
    """Get trading signals for a symbol"""
    timeframe = request.args.get('timeframe', '1min')
    result = server.get_signals(symbol, timeframe)
    return jsonify(result)

@app.route('/api/watchlist')
def get_watchlist():
    """Get current watchlist"""
    result = server.get_watchlist()
    return jsonify(result)

@app.route('/api/darpa/events')
def get_darpa_events():
    """Get DARPA frontier tech events"""
    hours_back = int(request.args.get('hours_back', 24))
    source = request.args.get('source', 'all')
    result = server.get_darpa_events(hours_back, source)
    return jsonify(result)

@app.route('/api/macro/events')
def get_macro_events():
    """Get macro economic events"""
    hours_ahead = int(request.args.get('hours_ahead', 48))
    min_importance = request.args.get('min_importance', 'medium')
    result = server.get_macro_events(hours_ahead, min_importance)
    return jsonify(result)

@app.route('/api/tickers/check', methods=['POST'])
def check_tickers():
    """Check ticker availability"""
    symbols = request.json.get('symbols', [])
    result = server.check_ticker_availability(symbols)
    return jsonify(result)

if __name__ == '__main__':
    print("🚀 MCP REST API running on http://localhost:5000")
    print("\nEndpoints:")
    print("  GET  /api/signals/<symbol>?timeframe=5min")
    print("  GET  /api/watchlist")
    print("  GET  /api/darpa/events?hours_back=24")
    print("  GET  /api/macro/events?hours_ahead=48")
    print("  POST /api/tickers/check")
    app.run(host='0.0.0.0', port=5000, debug=True)
```

### Option 2: Direct Python Import (For Local Models)

```python
# For use in other Python apps
from mcps.servers.trading.mcp_server_integrated import MCPServer

server = MCPServer()
signals = server.get_signals("IONQ", "5min")
```

### Option 3: WebSocket Server (Real-time Updates)

```python
# Create websocket_server.py for real-time streaming
import asyncio
import websockets
import json
from mcp_server_integrated import MCPServer

async def handler(websocket, path):
    server = MCPServer()

    while True:
        # Send updates every 30 seconds
        watchlist = server.get_watchlist()
        await websocket.send(json.dumps(watchlist))
        await asyncio.sleep(30)

start_server = websockets.serve(handler, "localhost", 8765)
asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()
```

### Option 4: Export to Standard MCP Format

Your MCP server already follows the MCP protocol. To use with other MCP-compatible tools:

1. **For other MCP clients**, share the config:
```json
{
  "mcpServers": {
    "trading-signals": {
      "command": "/path/to/python",
      "args": ["/path/to/mcp_server_integrated.py"],
      "env": {
        "ALPACA_API_KEY": "your_key",
        "ALPACA_SECRET_KEY": "your_secret"
      }
    }
  }
}
```

2. **For ChatGPT Desktop** (when it supports MCP):
   - Copy the same config format
   - Point to your Python interpreter and script

### Option 5: Scheduled Data Export

```bash
# Add to crontab for automatic data export
*/30 * * * * python export_signals.py > /shared/signals.json
```

## 🔐 Security Notes

When sharing with other agents:

1. **API Keys**: Never share your Alpaca keys directly
2. **Use Environment Variables**: Load from `.env` file
3. **Add Authentication**: Implement API keys for REST endpoints
4. **Rate Limiting**: Prevent abuse of shared endpoints
5. **Read-Only Access**: Only expose GET endpoints publicly

## 📊 Current Data Collection Status

- **Historical Data**: 20 stocks have 1-minute data stored
- **Real-time Data**: Available on-demand via Alpaca API
- **DARPA Events**: Not continuously collected (need daemon)
- **News/Sentiment**: Fetched on-demand

## 🚀 Quick Start for Sharing

1. **Install Flask** (for REST API):
```bash
pip install flask flask-cors
```

2. **Start REST API**:
```bash
python mcp_rest_api.py
```

3. **Test from any agent**:
```bash
curl http://localhost:5000/api/signals/IONQ
```

4. **Use from ChatGPT**:
```
"Call http://localhost:5000/api/darpa/events to get DARPA events"
```

## Summary

- Your MCP server is at `/servers/trading/mcp_server_integrated.py`
- It's currently running (triggered by Claude Desktop)
- Data is NOT continuously collected unless daemon is running
- Can be shared via REST API, WebSocket, or direct Python import
- Compatible with any agent that can make HTTP requests