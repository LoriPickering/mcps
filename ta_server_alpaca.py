# ta_server_alpaca.py - MCP server with Alpaca real-time data feed
import asyncio
import os
from typing import Dict, Any, List, Literal
from datetime import datetime, timezone
import pandas as pd
import pandas_ta as ta
from mcp.server.fastapi import FastAPIServer
from fastapi import FastAPI
from dotenv import load_dotenv

# Alpaca imports
from alpaca.data.live import StockDataStream
from alpaca.data.models import Bar
from alpaca.data.timeframe import TimeFrame

load_dotenv()

# Alpaca credentials
API_KEY = os.getenv("ALPACA_API_KEY")
SECRET_KEY = os.getenv("ALPACA_SECRET_KEY")
# Use paper trading endpoint for safety
BASE_URL = os.getenv("ALPACA_BASE_URL", "https://paper-api.alpaca.markets")

# Data storage
CANDLES: Dict[str, pd.DataFrame] = {}  # key "AAPL-1Min" -> DataFrame[time, open, high, low, close, volume]

# MCP setup
api = FastAPI()
mcp = FastAPIServer(api, "chart-signals")

# Alpaca data stream
data_stream = None
subscribed_symbols = set()

def timeframe_to_string(tf: TimeFrame) -> str:
    """Convert Alpaca TimeFrame to string for storage key"""
    tf_map = {
        TimeFrame.Minute: "1Min",
        TimeFrame.Hour: "1Hour",
        TimeFrame.Day: "1Day"
    }
    return tf_map.get(tf, "1Min")

async def handle_bar(bar: Bar):
    """Process incoming bar data from Alpaca"""
    symbol = bar.symbol
    # Alpaca bars come with minute resolution by default
    key = f"{symbol}-1Min"

    # Convert to DataFrame row
    df = CANDLES.get(key, pd.DataFrame(columns=["time", "open", "high", "low", "close", "volume"]))

    new_row = pd.DataFrame([{
        "time": bar.timestamp,
        "open": float(bar.open),
        "high": float(bar.high),
        "low": float(bar.low),
        "close": float(bar.close),
        "volume": float(bar.volume)
    }])

    # Append and maintain last 3000 bars
    df = pd.concat([df, new_row], ignore_index=True)
    df = df.drop_duplicates(subset=["time"]).sort_values("time").tail(3000)
    CANDLES[key] = df

    print(f"📊 {symbol} bar: ${bar.close:.2f} @ {bar.timestamp}")

@api.post("/subscribe")
async def subscribe(symbols: List[str]):
    """Subscribe to real-time data for symbols"""
    global data_stream, subscribed_symbols

    if not API_KEY or not SECRET_KEY:
        return {"error": "Alpaca API credentials not configured"}

    if data_stream is None:
        # Don't pass url_override for WebSocket streams
        data_stream = StockDataStream(API_KEY, SECRET_KEY)
        data_stream.subscribe_bars(handle_bar, *symbols)

        # Start stream in background
        asyncio.create_task(run_stream())
        subscribed_symbols.update(symbols)
        return {"status": "started", "symbols": symbols}
    else:
        # Add new symbols to existing stream
        new_symbols = set(symbols) - subscribed_symbols
        if new_symbols:
            data_stream.subscribe_bars(handle_bar, *list(new_symbols))
            subscribed_symbols.update(new_symbols)
        return {"status": "updated", "symbols": list(subscribed_symbols)}

async def run_stream():
    """Run the Alpaca data stream"""
    global data_stream
    if data_stream:
        try:
            await data_stream._run_forever()
        except Exception as e:
            print(f"Stream error: {e}")
            data_stream = None

@api.get("/status")
def get_status():
    """Check connection and data status"""
    return {
        "alpaca_configured": bool(API_KEY and SECRET_KEY),
        "stream_active": data_stream is not None,
        "subscribed_symbols": list(subscribed_symbols),
        "data_available": list(CANDLES.keys()),
        "bar_counts": {k: len(v) for k, v in CANDLES.items()}
    }

@mcp.tool()
def get_signals(symbol: str, tf: Literal["1Min", "5Min", "15Min", "1Hour"] = "1Min") -> Dict[str, Any]:
    """Return latest indicators and crossing signals for a symbol."""
    # For now, we only support 1Min from Alpaca real-time feed
    # You could aggregate 1Min bars to create larger timeframes
    key = f"{symbol}-{tf}"

    if tf != "1Min":
        # Simple aggregation for other timeframes
        base_key = f"{symbol}-1Min"
        if base_key not in CANDLES or len(CANDLES[base_key]) < 35:
            return {"ready": False, "reason": f"insufficient 1Min bars to aggregate to {tf}"}

        # Aggregate 1Min bars to requested timeframe
        df_1min = CANDLES[base_key].copy()
        df_1min["time"] = pd.to_datetime(df_1min["time"])
        df_1min.set_index("time", inplace=True)

        # Resample based on timeframe
        resample_map = {
            "5Min": "5T",
            "15Min": "15T",
            "1Hour": "1H"
        }

        if tf in resample_map:
            df = df_1min.resample(resample_map[tf]).agg({
                "open": "first",
                "high": "max",
                "low": "min",
                "close": "last",
                "volume": "sum"
            }).dropna()

            if len(df) < 35:
                return {"ready": False, "reason": f"insufficient {tf} bars after aggregation"}
        else:
            df = df_1min
    else:
        if key not in CANDLES or len(CANDLES[key]) < 35:
            return {"ready": False, "reason": "insufficient bars (need 35+)"}
        df = CANDLES[key].copy()
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

    # Get last two bars for crossing detection
    last = df.iloc[-1]
    prev = df.iloc[-2]

    crossings = {
        "macd_cross_up": prev["macd"] <= prev["signal"] and last["macd"] > last["signal"],
        "macd_cross_dn": prev["macd"] >= prev["signal"] and last["macd"] < last["signal"],
        "ema_support_lost": prev["close"] >= prev["ema9"] and last["close"] < last["ema9"],
        "ema_reclaim": prev["close"] <= prev["ema9"] and last["close"] > last["ema9"],
        "rsi_overbought": last["rsi"] >= 70,
        "rsi_oversold": last["rsi"] <= 30,
    }

    snapshot = {
        "price": float(last["close"]),
        "ema9": float(last["ema9"]),
        "ma10": float(last["ma10"]),
        "macd": float(last["macd"]),
        "signal": float(last["signal"]),
        "hist": float(last["hist"]),
        "rsi": float(last["rsi"]),
        "time": str(df.index[-1])
    }

    return {
        "ready": True,
        "symbol": symbol,
        "tf": tf,
        "snapshot": snapshot,
        "crossings": crossings
    }

@mcp.tool()
def get_watchlist() -> Dict[str, Any]:
    """Get current watchlist with latest prices and signals"""
    watchlist = []
    for symbol in subscribed_symbols:
        signals = get_signals(symbol, "1Min")
        if signals.get("ready"):
            watchlist.append({
                "symbol": symbol,
                "price": signals["snapshot"]["price"],
                "rsi": signals["snapshot"]["rsi"],
                "signals": [k for k, v in signals["crossings"].items() if v]
            })
    return {"watchlist": watchlist, "timestamp": datetime.now(timezone.utc).isoformat()}

def load_watchlist(filename="watchlist.txt"):
    """Load stock symbols from watchlist file"""
    symbols = []
    try:
        with open(filename, "r") as f:
            for line in f:
                line = line.strip()
                # Skip empty lines and comments
                if line and not line.startswith("#"):
                    symbols.append(line.upper())
        return symbols
    except FileNotFoundError:
        print(f"⚠️  Watchlist file '{filename}' not found")
        return []

async def auto_subscribe():
    """Automatically subscribe to watchlist symbols on startup"""
    await asyncio.sleep(2)  # Give server time to start

    symbols = load_watchlist()
    if symbols:
        print(f"\n📋 Auto-subscribing to {len(symbols)} symbols from watchlist.txt...")
        result = await subscribe(symbols)
        if "error" not in result:
            print(f"✅ Subscribed to: {', '.join(symbols)}")
        else:
            print(f"❌ Failed to subscribe: {result['error']}")
    else:
        print("\n⚠️  No symbols in watchlist.txt - add symbols to the file and restart")

@api.on_event("startup")
async def startup_event():
    """Run after server starts"""
    asyncio.create_task(auto_subscribe())

if __name__ == "__main__":
    import uvicorn

    if not API_KEY or not SECRET_KEY:
        print("⚠️  WARNING: Alpaca API credentials not found!")
        print("Please set ALPACA_API_KEY and ALPACA_SECRET_KEY in .env file")
        print("")
        print("Get your API keys from: https://app.alpaca.markets/")
        print("For paper trading (recommended), use the paper trading API keys")

    # Load and display watchlist
    symbols = load_watchlist()
    if symbols:
        print(f"\n📋 Watchlist loaded: {', '.join(symbols)}")
    else:
        print("\n⚠️  No symbols found in watchlist.txt")

    print("\n🚀 Starting MCP Chart Signals server on http://localhost:8742")
    print("📈 Status: http://localhost:8742/status")
    print("🔄 The server will auto-subscribe to watchlist.txt symbols on startup")

    uvicorn.run(api, host="127.0.0.1", port=8742)