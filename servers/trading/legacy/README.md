# Legacy Trading Server Files

This directory contains archived legacy versions of the trading server implementations.

## Archived Files

- **ta_server.py** - Original webhook version using ring buffer for TradingView webhooks
- **ta_server_alpaca.py** - Stocks-only version with Alpaca real-time data
- **mcp_server.py** - Basic MCP example with mock data

## Active Files

The current maintained versions are in the parent directory:
- `ta_server_full.py` - Main data collector (WebSocket + storage)
- `mcp_server_integrated.py` - MCP interface for AI assistants

These legacy files are kept for reference only.