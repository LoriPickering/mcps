#!/usr/bin/env python3
"""
MCP Server for Chart Signals - Integrated with Real Alpaca Data
This implements the proper MCP protocol with real market data
"""

import json
import sys
import asyncio
from typing import Dict, Any, List, Optional, Literal
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Set up logging
logging.basicConfig(level=logging.DEBUG, filename='/tmp/mcp_chart_signals.log')
logger = logging.getLogger(__name__)

# Import data processing
import os
from dotenv import load_dotenv
import pandas as pd
import pandas_ta as ta
import numpy as np
import sys
from pathlib import Path

# Get project root (2 levels up from this file)
PROJECT_ROOT = Path(__file__).parent.parent.parent.absolute()
DATA_DIR = PROJECT_ROOT / "data"
sys.path.insert(0, str(PROJECT_ROOT))

# Load env from project root
env_path = PROJECT_ROOT / ".env"
load_dotenv(env_path)

CANDLES = {}  # In-memory cache

def ensure_data_directories():
    """Create data directory structure if needed"""
    for asset_type in ["stocks", "crypto"]:
        for timeframe in ["1min", "5min", "15min", "1hour"]:
            path = DATA_DIR / asset_type / timeframe
            path.mkdir(parents=True, exist_ok=True)

def load_from_parquet(symbol: str, timeframe: str = "1min", is_crypto: bool = False, days_back: int = 7) -> Optional[pd.DataFrame]:
    """Load historical data from parquet files"""
    all_data = []
    # Clean symbol name for filesystem (replace / with _)
    clean_symbol = symbol.replace("/", "_")

    # Check current and previous month files
    for month_offset in range(2):
        month = datetime.now() - timedelta(days=30 * month_offset)
        month_str = month.strftime("%Y-%m")
        file_path = DATA_DIR / ("crypto" if is_crypto else "stocks") / timeframe / f"{clean_symbol}_{month_str}.parquet"

        if file_path.exists():
            try:
                df = pd.read_parquet(file_path)
                all_data.append(df)
                logger.info(f"Loaded {len(df)} bars from {file_path.name}")
            except Exception as e:
                logger.error(f"Error loading {file_path}: {e}")

    if all_data:
        combined = pd.concat(all_data, ignore_index=True)
        combined = combined.drop_duplicates(subset=["time"]).sort_values("time")
        # Filter to requested days - ensure timezone-aware comparison
        combined["time"] = pd.to_datetime(combined["time"])
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_back)
        return combined[combined["time"] >= cutoff_date]

    return None

def calculate_vwap(df: pd.DataFrame) -> pd.Series:
    """Calculate VWAP (Volume Weighted Average Price)"""
    typical_price = (df["high"] + df["low"] + df["close"]) / 3
    vwap = (typical_price * df["volume"]).cumsum() / df["volume"].cumsum()
    return vwap

def detect_crossings_with_history(df: pd.DataFrame) -> Dict[str, Any]:
    """Detect crossings and track bars since last cross"""
    if len(df) < 2:
        return {}

    crossings = {}
    bars_since = {}
    last_cross_info = {"type": None, "at": None}

    # Get last two bars
    last = df.iloc[-1]
    prev = df.iloc[-2]

    # Basic crossings
    crossings["macd_cross_up"] = bool(prev["macd"] <= prev["signal"] and last["macd"] > last["signal"])
    crossings["macd_cross_dn"] = bool(prev["macd"] >= prev["signal"] and last["macd"] < last["signal"])
    crossings["ema_support_lost"] = bool(prev["close"] >= prev["ema9"] and last["close"] < last["ema9"])
    crossings["ema_reclaim"] = bool(prev["close"] <= prev["ema9"] and last["close"] > last["ema9"])
    crossings["rsi_overbought"] = bool(last["rsi"] >= 70)
    crossings["rsi_oversold"] = bool(last["rsi"] <= 30)
    crossings["bb_squeeze"] = bool((last["bb_upper"] - last["bb_lower"]) / last["bb_middle"] < 0.04)
    crossings["bb_breakout_up"] = bool(last["close"] > last["bb_upper"])
    crossings["bb_breakout_dn"] = bool(last["close"] < last["bb_lower"])

    # Count bars since each type of crossing
    for i in range(len(df) - 1, -1, -1):
        row = df.iloc[i]
        prev_row = df.iloc[i - 1] if i > 0 else None

        # MACD crosses
        if prev_row is not None:
            if prev_row["macd"] <= prev_row["signal"] and row["macd"] > row["signal"]:
                if "macd_cross_up_bars" not in bars_since:
                    bars_since["macd_cross_up_bars"] = len(df) - 1 - i
                    if not last_cross_info["type"]:
                        last_cross_info = {"type": "macd_cross_up", "at": str(row.name)}

            if prev_row["macd"] >= prev_row["signal"] and row["macd"] < row["signal"]:
                if "macd_cross_dn_bars" not in bars_since:
                    bars_since["macd_cross_dn_bars"] = len(df) - 1 - i
                    if not last_cross_info["type"]:
                        last_cross_info = {"type": "macd_cross_dn", "at": str(row.name)}

            # EMA crosses
            if prev_row["close"] >= prev_row["ema9"] and row["close"] < row["ema9"]:
                if "ema_support_lost_bars" not in bars_since:
                    bars_since["ema_support_lost_bars"] = len(df) - 1 - i
                    if not last_cross_info["type"]:
                        last_cross_info = {"type": "ema_support_lost", "at": str(row.name)}

            if prev_row["close"] <= prev_row["ema9"] and row["close"] > row["ema9"]:
                if "ema_reclaim_bars" not in bars_since:
                    bars_since["ema_reclaim_bars"] = len(df) - 1 - i
                    if not last_cross_info["type"]:
                        last_cross_info = {"type": "ema_reclaim", "at": str(row.name)}

    return {
        "crossings": crossings,
        "bars_since": bars_since,
        "last_cross": last_cross_info
    }

class MCPServer:
    """MCP Server that communicates via stdin/stdout"""

    def __init__(self):
        self.running = True
        ensure_data_directories()
        logger.info("MCP Server initialized with real data integration")

    async def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming JSON-RPC request"""
        method = request.get("method")
        params = request.get("params", {})
        request_id = request.get("id")

        logger.info(f"Handling request: {method}")

        # Handle MCP protocol methods
        if method == "initialize":
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
                        "version": "2.0.0"
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
                            "description": "Get real-time trading signals for a symbol",
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
                            "description": "Get current watchlist with real prices",
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
                        },
                        {
                            "name": "get_storage_info",
                            "description": "Get information about stored data",
                            "inputSchema": {
                                "type": "object",
                                "properties": {}
                            }
                        },
                        {
                            "name": "get_capabilities",
                            "description": "Get server capabilities and version",
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
                result = self.get_signals(
                    tool_args.get("symbol"),
                    tool_args.get("timeframe", "1min")
                )
            elif tool_name == "get_watchlist":
                result = self.get_watchlist()
            elif tool_name == "check_market_status":
                result = self.check_market_status()
            elif tool_name == "get_storage_info":
                result = self.get_storage_info()
            elif tool_name == "get_capabilities":
                result = self.get_capabilities()
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

    def get_signals(self, symbol: str, timeframe: str = "1min") -> Dict[str, Any]:
        """Get real trading signals for a symbol"""
        if not symbol:
            return {"error": "Symbol required"}

        # Determine if crypto and normalize symbol
        is_crypto = "/" in symbol or symbol in ["BTC", "ETH"]

        # Normalize crypto symbols to include /USD for file loading
        if is_crypto and "/" not in symbol:
            file_symbol = f"{symbol}/USD"
        else:
            file_symbol = symbol

        # Try to load from memory cache first
        cache_key = f"{symbol}-{timeframe}"

        # Load from parquet if not in cache
        df = load_from_parquet(file_symbol, timeframe, is_crypto, days_back=7)

        if df is None or len(df) < 35:
            # Try loading 1min and aggregating if larger timeframe requested
            if timeframe != "1min":
                df_1min = load_from_parquet(file_symbol, "1min", is_crypto, days_back=7)
                if df_1min is not None and len(df_1min) >= 35:
                    df = self.aggregate_timeframe(df_1min, timeframe)
                else:
                    return {
                        "ready": False,
                        "reason": f"insufficient bars (have {len(df_1min) if df_1min is not None else 0}, need 35+)",
                        "symbol": symbol,
                        "timeframe": timeframe
                    }
            else:
                return {
                    "ready": False,
                    "reason": f"insufficient bars (have {len(df) if df is not None else 0}, need 35+)",
                    "symbol": symbol,
                    "timeframe": timeframe
                }

        # Prepare dataframe
        df["time"] = pd.to_datetime(df["time"])
        df.set_index("time", inplace=True)

        # Calculate indicators
        df["ema9"] = ta.ema(df["close"], length=9)
        df["ma10"] = ta.sma(df["close"], length=10)
        macd = ta.macd(df["close"], fast=12, slow=26, signal=9)
        df["macd"] = macd["MACD_12_26_9"]
        df["signal"] = macd["MACDs_12_26_9"]
        df["hist"] = macd["MACDh_12_26_9"]
        df["rsi"] = ta.rsi(df["close"], length=14)

        # Bollinger Bands
        try:
            bbands = ta.bbands(df["close"], length=20, std=2)
            if bbands is not None and not bbands.empty:
                # Get column names dynamically as they may vary
                bb_cols = bbands.columns.tolist()
                df["bb_upper"] = bbands.iloc[:, 0] if len(bb_cols) > 0 else None  # Upper band
                df["bb_middle"] = bbands.iloc[:, 1] if len(bb_cols) > 1 else None  # Middle band
                df["bb_lower"] = bbands.iloc[:, 2] if len(bb_cols) > 2 else None  # Lower band
            else:
                df["bb_upper"] = None
                df["bb_middle"] = None
                df["bb_lower"] = None
        except Exception as e:
            logger.warning(f"Bollinger Bands calculation failed: {e}")
            df["bb_upper"] = None
            df["bb_middle"] = None
            df["bb_lower"] = None

        # VWAP
        df["vwap"] = calculate_vwap(df)

        # Detect crossings with history
        crossing_data = detect_crossings_with_history(df)

        # Get last two bars for comparison
        last = df.iloc[-1]
        prev = df.iloc[-2] if len(df) > 1 else last

        # Current snapshot
        snapshot = {
            "price": float(last["close"]),
            "ema9": float(last["ema9"]) if not pd.isna(last["ema9"]) else None,
            "ma10": float(last["ma10"]) if not pd.isna(last["ma10"]) else None,
            "macd": float(last["macd"]) if not pd.isna(last["macd"]) else None,
            "signal": float(last["signal"]) if not pd.isna(last["signal"]) else None,
            "hist": float(last["hist"]) if not pd.isna(last["hist"]) else None,
            "rsi": float(last["rsi"]) if not pd.isna(last["rsi"]) else None,
            "bb_upper": float(last["bb_upper"]) if not pd.isna(last["bb_upper"]) else None,
            "bb_middle": float(last["bb_middle"]) if not pd.isna(last["bb_middle"]) else None,
            "bb_lower": float(last["bb_lower"]) if not pd.isna(last["bb_lower"]) else None,
            "vwap": float(last["vwap"]) if not pd.isna(last["vwap"]) else None,
            "volume": float(last["volume"]),
            "time": str(df.index[-1])
        }

        # Previous snapshot for delta calculations
        prev_snapshot = {
            "price": float(prev["close"]),
            "ema9": float(prev["ema9"]) if not pd.isna(prev["ema9"]) else None,
            "ma10": float(prev["ma10"]) if not pd.isna(prev["ma10"]) else None,
            "macd": float(prev["macd"]) if not pd.isna(prev["macd"]) else None,
            "signal": float(prev["signal"]) if not pd.isna(prev["signal"]) else None,
            "hist": float(prev["hist"]) if not pd.isna(prev["hist"]) else None,
            "rsi": float(prev["rsi"]) if not pd.isna(prev["rsi"]) else None,
            "volume": float(prev["volume"]),
            "time": str(df.index[-2]) if len(df) > 1 else str(df.index[-1])
        }

        # Calculate trend state
        trend_state = self.calculate_trend_state(last)

        # Determine risk anchor
        risk_anchor = self.calculate_risk_anchor(df, last, trend_state)

        return {
            "ready": True,
            "symbol": symbol,
            "asset_type": "crypto" if is_crypto else "stock",
            "tf": timeframe,
            "snapshot": snapshot,
            "prev_snapshot": prev_snapshot,  # NEW: Previous bar for deltas
            "trend_state": trend_state,      # NEW: Compact position summary
            "risk_anchor": risk_anchor,      # NEW: Stop loss suggestion
            "crossings": crossing_data["crossings"],
            "bars_since": crossing_data["bars_since"],
            "last_cross": crossing_data["last_cross"]
        }

    def aggregate_timeframe(self, df_1min: pd.DataFrame, target_tf: str) -> pd.DataFrame:
        """Aggregate 1min data to larger timeframe"""
        df = df_1min.copy()
        df["time"] = pd.to_datetime(df["time"])
        df.set_index("time", inplace=True)

        # Resample mapping
        resample_map = {
            "5min": "5T",
            "15min": "15T",
            "1hour": "1H"
        }

        if target_tf in resample_map:
            df_resampled = df.resample(resample_map[target_tf]).agg({
                "open": "first",
                "high": "max",
                "low": "min",
                "close": "last",
                "volume": "sum"
            }).dropna()
            return df_resampled.reset_index()

        return df_1min

    def get_watchlist(self) -> Dict[str, Any]:
        """Get watchlist with real current data"""
        watchlist_stocks = []
        watchlist_crypto = []

        try:
            watchlist_path = PROJECT_ROOT / "watchlist.txt"
            with open(watchlist_path, "r") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        symbol = line.upper()

                        # Get latest signals for each symbol
                        signals_result = self.get_signals(symbol, "1min")

                        if signals_result.get("ready"):
                            # Get active signals
                            active_signals = [
                                k for k, v in signals_result["crossings"].items() if v
                            ]

                            item = {
                                "symbol": symbol,
                                "price": signals_result["snapshot"]["price"],
                                "rsi": signals_result["snapshot"]["rsi"],
                                "signals": active_signals
                            }

                            if signals_result["asset_type"] == "crypto":
                                # Convert to proper crypto symbol format
                                if "/" not in symbol:
                                    item["symbol"] = f"{symbol}/USD"
                                watchlist_crypto.append(item)
                            else:
                                watchlist_stocks.append(item)
                        else:
                            # No data available yet
                            item = {
                                "symbol": symbol,
                                "price": None,
                                "rsi": None,
                                "signals": [],
                                "note": "No data"
                            }

                            if symbol in ["BTC", "ETH"]:
                                item["symbol"] = f"{symbol}/USD"
                                watchlist_crypto.append(item)
                            else:
                                watchlist_stocks.append(item)

        except FileNotFoundError:
            logger.warning("watchlist.txt not found")

        return {
            "watchlist": {
                "stocks": watchlist_stocks,
                "crypto": watchlist_crypto
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "market_hours": {
                "stocks": "9:30 AM - 4:00 PM ET (weekdays)",
                "crypto": "24/7"
            }
        }

    def check_market_status(self) -> Dict[str, Any]:
        """Check market status"""
        now = datetime.now(timezone.utc)

        # Convert to ET (UTC-5 or UTC-4 for DST)
        # Simplified - assumes EST (UTC-5)
        et_hour = (now.hour - 5) % 24
        et_minute = now.minute
        weekday = now.weekday()

        # Market sessions
        is_weekday = weekday < 5

        if is_weekday:
            if et_hour < 4:
                session = "closed"
                stock_market_open = False
            elif 4 <= et_hour < 9 or (et_hour == 9 and et_minute < 30):
                session = "premarket"
                stock_market_open = False
            elif (et_hour == 9 and et_minute >= 30) or (10 <= et_hour < 16):
                session = "regular"
                stock_market_open = True
            elif 16 <= et_hour < 20:
                session = "afterhours"
                stock_market_open = False
            else:
                session = "closed"
                stock_market_open = False
        else:
            session = "closed"
            stock_market_open = False

        # Next open
        if weekday == 4 and et_hour >= 16:  # Friday after close
            next_open = "Monday 9:30 AM ET"
        elif weekday == 5:  # Saturday
            next_open = "Monday 9:30 AM ET"
        elif weekday == 6:  # Sunday
            next_open = "Tomorrow 9:30 AM ET"
        elif session == "closed" or session == "afterhours":
            next_open = "Tomorrow 9:30 AM ET"
        else:
            next_open = None

        # Format current time
        current_time_et = f"{et_hour:02d}:{et_minute:02d} ET"

        return {
            "stocks": {
                "open": stock_market_open,
                "session": session,
                "next_open": next_open,
                "current_time_et": current_time_et
            },
            "crypto": {
                "open": True,
                "note": "24/7 trading"
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    def get_storage_info(self) -> Dict[str, Any]:
        """Get information about stored historical data"""
        info = {
            "data_directory": str(DATA_DIR.absolute()),
            "stored_symbols": {"stocks": [], "crypto": []},
            "total_size_mb": 0,
            "file_count": 0
        }

        if DATA_DIR.exists():
            for asset_type in ["stocks", "crypto"]:
                asset_path = DATA_DIR / asset_type
                if asset_path.exists():
                    symbols = set()
                    total_size = 0
                    file_count = 0

                    for timeframe_dir in asset_path.iterdir():
                        if timeframe_dir.is_dir():
                            for file in timeframe_dir.glob("*.parquet"):
                                # Extract symbol from filename
                                symbol = file.stem.split("_")[0]
                                if asset_type == "crypto":
                                    # Convert back to / format
                                    symbol = symbol.replace("USD", "/USD")
                                symbols.add(symbol)
                                total_size += file.stat().st_size
                                file_count += 1

                    info["stored_symbols"][asset_type] = sorted(list(symbols))
                    info["total_size_mb"] += total_size / (1024 * 1024)
                    info["file_count"] += file_count

        info["total_size_mb"] = round(info["total_size_mb"], 2)
        return info

    def get_capabilities(self) -> Dict[str, Any]:
        """Get server capabilities and version"""
        return {
            "version": "2.0.0",
            "protocol": "2025-06-18",
            "indicators": ["EMA9", "SMA10", "MACD(12,26,9)", "RSI14", "BB(20,2)", "VWAP"],
            "timeframes": ["1min", "5min", "15min", "1hour"],
            "asset_types": ["stocks", "crypto"],
            "data_source": "Alpaca Markets via parquet storage",
            "features": [
                "real-time signals",
                "crossing detection",
                "bars_since tracking",
                "last_cross info",
                "VWAP calculation"
            ],
            "storage": "parquet",
            "max_bars_in_memory": 3000
        }

    def calculate_trend_state(self, last_row) -> str:
        """
        Calculate overall trend state based on multiple indicators
        Returns: 'bullish', 'bearish', 'mixed', or 'consolidating'
        """
        bullish_signals = 0
        bearish_signals = 0

        # Price vs moving averages
        if not pd.isna(last_row["ema9"]):
            if last_row["close"] > last_row["ema9"]:
                bullish_signals += 1
            else:
                bearish_signals += 1

        if not pd.isna(last_row["ma10"]):
            if last_row["close"] > last_row["ma10"]:
                bullish_signals += 1
            else:
                bearish_signals += 1

        # MACD
        if not pd.isna(last_row["macd"]) and not pd.isna(last_row["signal"]):
            if last_row["macd"] > last_row["signal"]:
                bullish_signals += 1
            else:
                bearish_signals += 1

            # MACD histogram direction
            if not pd.isna(last_row["hist"]):
                if last_row["hist"] > 0:
                    bullish_signals += 1
                else:
                    bearish_signals += 1

        # RSI levels
        if not pd.isna(last_row["rsi"]):
            if last_row["rsi"] > 50:
                bullish_signals += 1
            else:
                bearish_signals += 1

            # Extreme RSI levels (stronger signal)
            if last_row["rsi"] > 70:
                bearish_signals += 1  # Overbought warning
            elif last_row["rsi"] < 30:
                bullish_signals += 1  # Oversold opportunity

        # Bollinger Bands position
        if not pd.isna(last_row["bb_upper"]) and not pd.isna(last_row["bb_lower"]):
            bb_range = last_row["bb_upper"] - last_row["bb_lower"]
            price_position = (last_row["close"] - last_row["bb_lower"]) / bb_range if bb_range > 0 else 0.5

            if price_position > 0.8:
                bearish_signals += 1  # Near upper band
            elif price_position < 0.2:
                bullish_signals += 1  # Near lower band
            else:
                pass  # Neutral in middle

        # VWAP comparison
        if not pd.isna(last_row["vwap"]):
            if last_row["close"] > last_row["vwap"]:
                bullish_signals += 1
            else:
                bearish_signals += 1

        # Determine overall state
        total_signals = bullish_signals + bearish_signals
        if total_signals == 0:
            return "consolidating"

        bullish_ratio = bullish_signals / total_signals

        if bullish_ratio >= 0.7:
            return "bullish"
        elif bullish_ratio <= 0.3:
            return "bearish"
        elif 0.45 <= bullish_ratio <= 0.55:
            return "consolidating"
        else:
            return "mixed"

    def calculate_risk_anchor(self, df: pd.DataFrame, last_row, trend_state: str) -> Dict[str, Any]:
        """
        Calculate risk anchor (suggested stop loss placement) based on market structure
        Returns dict with stop price and reasoning
        """
        risk_anchor = {
            "price": None,
            "type": None,
            "distance_pct": None,
            "reasoning": None
        }

        current_price = last_row["close"]

        # Method 1: ATR-based stop (if we have enough data)
        if len(df) >= 14:
            # Calculate ATR
            high_low = df["high"] - df["low"]
            high_close = abs(df["high"] - df["close"].shift())
            low_close = abs(df["low"] - df["close"].shift())
            true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
            atr = true_range.rolling(14).mean().iloc[-1]

            if not pd.isna(atr):
                # Use 2x ATR for stop distance
                atr_stop = current_price - (2 * atr)
                risk_anchor["price"] = atr_stop
                risk_anchor["type"] = "ATR"
                risk_anchor["distance_pct"] = ((current_price - atr_stop) / current_price) * 100
                risk_anchor["reasoning"] = f"2x ATR ({atr:.2f}) below entry"

        # Method 2: Bollinger Band based stop
        if not pd.isna(last_row["bb_lower"]) and risk_anchor["price"] is None:
            bb_stop = last_row["bb_lower"] * 0.995  # Slightly below lower band
            risk_anchor["price"] = bb_stop
            risk_anchor["type"] = "Bollinger"
            risk_anchor["distance_pct"] = ((current_price - bb_stop) / current_price) * 100
            risk_anchor["reasoning"] = "Below lower Bollinger Band"

        # Method 3: Recent swing low
        if len(df) >= 20 and (risk_anchor["price"] is None or trend_state == "bullish"):
            # Find recent swing low
            recent_lows = df["low"].tail(20)
            swing_low = recent_lows.min()

            if swing_low < current_price:
                swing_stop = swing_low * 0.995  # Slightly below swing low

                # Use swing low if it's closer than current anchor (for bullish trends)
                if risk_anchor["price"] is None or (trend_state == "bullish" and swing_stop > risk_anchor["price"]):
                    risk_anchor["price"] = swing_stop
                    risk_anchor["type"] = "SwingLow"
                    risk_anchor["distance_pct"] = ((current_price - swing_stop) / current_price) * 100
                    risk_anchor["reasoning"] = "Below recent swing low"

        # Method 4: Moving average support
        if not pd.isna(last_row["ema9"]) and trend_state == "bullish":
            ema_stop = last_row["ema9"] * 0.99  # 1% below EMA9

            # Use EMA stop if it's tighter than current (for strong trends)
            if risk_anchor["price"] is None or (ema_stop > risk_anchor["price"] and risk_anchor["distance_pct"] > 3):
                risk_anchor["price"] = ema_stop
                risk_anchor["type"] = "EMA"
                risk_anchor["distance_pct"] = ((current_price - ema_stop) / current_price) * 100
                risk_anchor["reasoning"] = "Below EMA9 support"

        # Method 5: Fixed percentage (fallback)
        if risk_anchor["price"] is None:
            # Default to 2% stop
            fixed_stop = current_price * 0.98
            risk_anchor["price"] = fixed_stop
            risk_anchor["type"] = "Fixed"
            risk_anchor["distance_pct"] = 2.0
            risk_anchor["reasoning"] = "Fixed 2% stop loss"

        # Round values for cleaner output
        if risk_anchor["price"] is not None:
            risk_anchor["price"] = round(risk_anchor["price"], 2)
            risk_anchor["distance_pct"] = round(risk_anchor["distance_pct"], 2)

        return risk_anchor

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

                logger.info(f"Received: {line_str[:200]}")

                try:
                    request = json.loads(line_str)
                except json.JSONDecodeError as e:
                    logger.error(f"JSON decode error: {e}")
                    continue

                # Handle request
                response = await self.handle_request(request)

                # Send response
                response_str = json.dumps(response)
                logger.info(f"Sending: {response_str[:200]}")

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
    logger.info("Starting MCP Chart Signals Server v2.0 with Real Data")
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}")