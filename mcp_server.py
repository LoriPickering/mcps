#!/usr/bin/env python3
"""
MCP Server for Chart Signals
This implements the proper MCP protocol for Claude Desktop
"""

import json
import sys
import asyncio
from typing import Dict, Any, List, Optional
import logging
from datetime import datetime, timezone

# Set up logging
logging.basicConfig(level=logging.DEBUG, filename='/tmp/mcp_chart_signals.log')
logger = logging.getLogger(__name__)

# Import our existing functionality
import os
from dotenv import load_dotenv
import pandas as pd

load_dotenv()

# Simple in-memory storage for demo
MARKET_DATA = {}

class MCPServer:
    """MCP Server that communicates via stdin/stdout"""

    def __init__(self):
        self.running = True
        logger.info("MCP Server initialized")

    async def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming JSON-RPC request"""
        method = request.get("method")
        params = request.get("params", {})
        request_id = request.get("id")

        logger.info(f"Handling request: {method}")

        # Handle MCP protocol methods
        if method == "initialize":
            # Use the protocol version requested by Claude
            requested_version = params.get("protocolVersion", "2025-06-18")
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "protocolVersion": requested_version,
                    "capabilities": {
                        "tools": {}
                    },
                    "serverInfo": {
                        "name": "chart-signals",
                        "version": "1.0.0"
                    }
                }
            }

        elif method == "tools/list":
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "tools": [
                        {
                            "name": "get_signals",
                            "description": "Get trading signals for a symbol",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "symbol": {
                                        "type": "string",
                                        "description": "Stock or crypto symbol"
                                    },
                                    "timeframe": {
                                        "type": "string",
                                        "enum": ["1min", "5min", "15min", "1hour"],
                                        "default": "1min"
                                    }
                                },
                                "required": ["symbol"]
                            }
                        },
                        {
                            "name": "get_watchlist",
                            "description": "Get current watchlist with prices",
                            "inputSchema": {
                                "type": "object",
                                "properties": {}
                            }
                        },
                        {
                            "name": "check_market_status",
                            "description": "Check if markets are open",
                            "inputSchema": {
                                "type": "object",
                                "properties": {}
                            }
                        }
                    ]
                }
            }

        elif method == "tools/call":
            tool_name = params.get("name")
            tool_args = params.get("arguments", {})

            logger.info(f"Calling tool: {tool_name} with args: {tool_args}")

            if tool_name == "get_signals":
                result = self.get_signals(tool_args.get("symbol"), tool_args.get("timeframe", "1min"))
            elif tool_name == "get_watchlist":
                result = self.get_watchlist()
            elif tool_name == "check_market_status":
                result = self.check_market_status()
            else:
                result = {"error": f"Unknown tool: {tool_name}"}

            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(result, indent=2)
                        }
                    ]
                }
            }

        else:
            # Unknown method
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32601,
                    "message": f"Method not found: {method}"
                }
            }

    def get_signals(self, symbol: str, timeframe: str) -> Dict[str, Any]:
        """Get trading signals for a symbol"""
        # This is a simplified version - in production, connect to your real data
        return {
            "symbol": symbol,
            "timeframe": timeframe,
            "price": 100.50,
            "signals": {
                "rsi": 45.2,
                "macd": "bullish",
                "ema9": 99.8,
                "recommendation": "hold"
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    def get_watchlist(self) -> Dict[str, Any]:
        """Get watchlist with current data"""
        # Read from watchlist.txt if it exists
        watchlist = []
        try:
            with open("watchlist.txt", "r") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        watchlist.append(line.upper())
        except:
            watchlist = ["AAPL", "TSLA", "BTC", "ETH"]

        return {
            "watchlist": watchlist,
            "count": len(watchlist),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    def check_market_status(self) -> Dict[str, Any]:
        """Check market status"""
        now = datetime.now(timezone.utc)
        hour = now.hour
        weekday = now.weekday()

        # Simple market hours check (9:30 AM - 4:00 PM ET, Mon-Fri)
        stock_market_open = (14 <= hour < 21) and (weekday < 5)  # UTC times

        return {
            "stocks": {
                "open": stock_market_open,
                "next_open": "Monday 9:30 AM ET" if weekday >= 5 else "Tomorrow 9:30 AM ET"
            },
            "crypto": {
                "open": True,
                "note": "24/7 trading"
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    async def run(self):
        """Main loop to handle stdin/stdout communication"""
        logger.info("MCP Server starting main loop")

        reader = asyncio.StreamReader()
        protocol = asyncio.StreamReaderProtocol(reader)
        await asyncio.get_event_loop().connect_read_pipe(lambda: protocol, sys.stdin)

        while self.running:
            try:
                # Read line from stdin
                line = await reader.readline()
                if not line:
                    break

                # Parse JSON-RPC request
                line_str = line.decode('utf-8').strip()
                if not line_str:
                    continue

                logger.info(f"Received: {line_str}")

                try:
                    request = json.loads(line_str)
                except json.JSONDecodeError as e:
                    logger.error(f"JSON decode error: {e}")
                    continue

                # Handle request
                response = await self.handle_request(request)

                # Send response
                response_str = json.dumps(response)
                logger.info(f"Sending: {response_str}")

                print(response_str, flush=True)

            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                error_response = {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {
                        "code": -32603,
                        "message": str(e)
                    }
                }
                print(json.dumps(error_response), flush=True)

async def main():
    server = MCPServer()
    await server.run()

if __name__ == "__main__":
    logger.info("Starting MCP Chart Signals Server")
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}")