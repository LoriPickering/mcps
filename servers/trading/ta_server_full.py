# ta_server_full.py - MCP server with Alpaca stocks + crypto, and parquet storage
import asyncio
import os
from typing import Dict, Any, List, Literal, Optional
from datetime import datetime, timezone, timedelta
from pathlib import Path
import pandas as pd
import pandas_ta as ta
from fastapi import FastAPI
try:
    from mcp.server.fastapi import FastAPIServer
    HAS_MCP = True
except ImportError:
    # MCP not available, we'll run without MCP tools
    HAS_MCP = False
    class FastAPIServer:
        def __init__(self, app, name):
            self.app = app
            self.name = name
        def tool(self):
            # Dummy decorator when MCP not available
            def decorator(func):
                return func
            return decorator
from dotenv import load_dotenv

# Alpaca imports
from alpaca.data.live import StockDataStream, CryptoDataStream
from alpaca.data.models import Bar
from alpaca.data.timeframe import TimeFrame

load_dotenv()

# Alpaca credentials
API_KEY = os.getenv("ALPACA_API_KEY")
SECRET_KEY = os.getenv("ALPACA_SECRET_KEY")
# Use paper trading endpoint for safety
BASE_URL = os.getenv("ALPACA_BASE_URL", "https://paper-api.alpaca.markets")

# Data storage
CANDLES: Dict[str, pd.DataFrame] = {}  # In-memory for real-time
DATA_DIR = Path("data")  # Disk storage for historical

# MCP setup
api = FastAPI()
mcp = FastAPIServer(api, "chart-signals")

# Alpaca data streams
stock_stream = None
crypto_stream = None
subscribed_stocks = set()
subscribed_crypto = set()

# Storage settings
SAVE_INTERVAL = 60  # Save to disk every 60 seconds
last_save_time = {}

def ensure_data_directories():
    """Create data directory structure"""
    for asset_type in ["stocks", "crypto"]:
        for timeframe in ["1min", "5min", "15min", "1hour", "1day"]:
            path = DATA_DIR / asset_type / timeframe
            path.mkdir(parents=True, exist_ok=True)

def get_parquet_path(symbol: str, timeframe: str, is_crypto: bool = False) -> Path:
    """Get parquet file path for a symbol/timeframe"""
    asset_type = "crypto" if is_crypto else "stocks"
    # Clean symbol name for filesystem (replace / with _)
    clean_symbol = symbol.replace("/", "_")
    # Monthly files
    month_str = datetime.now().strftime("%Y-%m")
    return DATA_DIR / asset_type / timeframe / f"{clean_symbol}_{month_str}.parquet"

def save_to_parquet(symbol: str, df: pd.DataFrame, timeframe: str = "1min", is_crypto: bool = False):
    """Save dataframe to parquet file (append if exists)"""
    if df.empty:
        return

    file_path = get_parquet_path(symbol, timeframe, is_crypto)

    try:
        if file_path.exists():
            # Read existing data
            existing_df = pd.read_parquet(file_path)
            # Combine and deduplicate
            combined_df = pd.concat([existing_df, df], ignore_index=True)
            combined_df = combined_df.drop_duplicates(subset=["time"]).sort_values("time")
        else:
            combined_df = df.sort_values("time")

        # Save to parquet
        combined_df.to_parquet(file_path, compression='snappy')
        print(f"💾 Saved {len(combined_df)} bars to {file_path.name}")
    except Exception as e:
        print(f"❌ Error saving {symbol} to parquet: {e}")

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
            except Exception as e:
                print(f"Error loading {file_path}: {e}")

    if all_data:
        combined = pd.concat(all_data, ignore_index=True)
        combined = combined.drop_duplicates(subset=["time"]).sort_values("time")
        # Filter to requested days
        cutoff_date = datetime.now() - timedelta(days=days_back)
        return combined[pd.to_datetime(combined["time"]) >= cutoff_date]

    return None

async def handle_stock_bar(bar: Bar):
    """Process incoming stock bar data"""
    try:
        await handle_bar(bar, is_crypto=False)
    except Exception as e:
        print(f"Error handling stock bar for {bar.symbol}: {e}")

async def handle_crypto_bar(bar: Bar):
    """Process incoming crypto bar data"""
    try:
        await handle_bar(bar, is_crypto=True)
    except Exception as e:
        print(f"Error handling crypto bar for {bar.symbol}: {e}")

async def handle_bar(bar: Bar, is_crypto: bool = False):
    """Process incoming bar data from Alpaca"""
    symbol = bar.symbol
    key = f"{symbol}-1min"

    # Get existing dataframe or create new one
    if key in CANDLES and not CANDLES[key].empty:
        df = CANDLES[key]
    else:
        df = pd.DataFrame(columns=["time", "open", "high", "low", "close", "volume"])

    new_row = pd.DataFrame([{
        "time": bar.timestamp,
        "open": float(bar.open),
        "high": float(bar.high),
        "low": float(bar.low),
        "close": float(bar.close),
        "volume": float(bar.volume)
    }])

    # Append and maintain last 3000 bars in memory
    if not df.empty:
        df = pd.concat([df, new_row], ignore_index=True)
    else:
        df = new_row
    df = df.drop_duplicates(subset=["time"]).sort_values("time").tail(3000)
    CANDLES[key] = df

    icon = "🪙" if is_crypto else "📊"
    print(f"{icon} {symbol} bar: ${bar.close:.2f} @ {bar.timestamp}")

    # Periodic save to disk
    now = datetime.now()
    last_save = last_save_time.get(symbol, datetime.min)
    if (now - last_save).total_seconds() >= SAVE_INTERVAL:
        # Save recent data to parquet
        asyncio.create_task(save_recent_data(symbol, df, is_crypto))
        last_save_time[symbol] = now

async def save_recent_data(symbol: str, df: pd.DataFrame, is_crypto: bool):
    """Save recent data to parquet in background"""
    # Save last 100 bars (avoid duplicates by saving recent only)
    recent_df = df.tail(100).copy()
    save_to_parquet(symbol, recent_df, "1min", is_crypto)

@api.post("/subscribe")
async def subscribe(symbols: List[str], asset_type: str = "auto"):
    """Subscribe to real-time data for symbols
    asset_type: 'stocks', 'crypto', or 'auto' (detect based on symbol)
    """
    global stock_stream, crypto_stream, subscribed_stocks, subscribed_crypto

    if not API_KEY or not SECRET_KEY:
        return {"error": "Alpaca API credentials not configured"}

    stocks = []
    cryptos = []

    # Detect asset type
    for symbol in symbols:
        symbol = symbol.upper()
        # Common crypto symbols - Alpaca uses "BTC/USD" format
        if asset_type == "crypto" or (asset_type == "auto" and symbol in ["BTC", "ETH", "BCH", "LTC", "UNI", "LINK", "DOGE", "SHIB"]):
            # Convert to Alpaca format: BTC -> BTC/USD
            if "/" not in symbol:
                if symbol.endswith("USD"):
                    # Convert BTCUSD -> BTC/USD
                    symbol = symbol[:-3] + "/USD"
                else:
                    # Convert BTC -> BTC/USD
                    symbol = f"{symbol}/USD"
            cryptos.append(symbol)
        else:
            stocks.append(symbol)

    results = {"stocks": [], "crypto": [], "errors": []}

    # Subscribe to stocks
    if stocks:
        try:
            if stock_stream is None:
                # Don't pass url_override for WebSocket streams - they use wss:// automatically
                stock_stream = StockDataStream(API_KEY, SECRET_KEY)
                stock_stream.subscribe_bars(handle_stock_bar, *stocks)
                asyncio.create_task(run_stock_stream())
                subscribed_stocks.update(stocks)
                results["stocks"] = stocks
            else:
                new_stocks = set(stocks) - subscribed_stocks
                if new_stocks:
                    stock_stream.subscribe_bars(handle_stock_bar, *list(new_stocks))
                    subscribed_stocks.update(new_stocks)
                    results["stocks"] = list(new_stocks)
        except Exception as e:
            results["errors"].append(f"Stock subscription error: {e}")

    # Subscribe to crypto
    if cryptos:
        try:
            if crypto_stream is None:
                crypto_stream = CryptoDataStream(API_KEY, SECRET_KEY)
                crypto_stream.subscribe_bars(handle_crypto_bar, *cryptos)
                asyncio.create_task(run_crypto_stream())
                subscribed_crypto.update(cryptos)
                results["crypto"] = cryptos
            else:
                new_crypto = set(cryptos) - subscribed_crypto
                if new_crypto:
                    crypto_stream.subscribe_bars(handle_crypto_bar, *list(new_crypto))
                    subscribed_crypto.update(new_crypto)
                    results["crypto"] = list(new_crypto)
        except Exception as e:
            results["errors"].append(f"Crypto subscription error: {e}")

    return results

async def run_stock_stream():
    """Run the Alpaca stock data stream"""
    global stock_stream
    if stock_stream:
        try:
            await stock_stream._run_forever()
        except Exception as e:
            print(f"Stock stream error: {e}")
            stock_stream = None

async def run_crypto_stream():
    """Run the Alpaca crypto data stream"""
    global crypto_stream
    if crypto_stream:
        try:
            await crypto_stream._run_forever()
        except Exception as e:
            print(f"Crypto stream error: {e}")
            crypto_stream = None

@api.get("/status")
def get_status():
    """Check connection and data status"""
    return {
        "alpaca_configured": bool(API_KEY and SECRET_KEY),
        "streams": {
            "stocks_active": stock_stream is not None,
            "crypto_active": crypto_stream is not None,
        },
        "subscribed": {
            "stocks": list(subscribed_stocks),
            "crypto": list(subscribed_crypto),
        },
        "data_available": list(CANDLES.keys()),
        "bar_counts": {k: len(v) for k, v in CANDLES.items()},
        "storage_path": str(DATA_DIR.absolute())
    }

@mcp.tool()
def get_signals(symbol: str, tf: Literal["1min", "5min", "15min", "1hour"] = "1min") -> Dict[str, Any]:
    """Return latest indicators and crossing signals for a symbol."""
    key = f"{symbol}-{tf}"

    # Try loading from memory first
    if tf == "1min":
        if f"{symbol}-1min" not in CANDLES or len(CANDLES[f"{symbol}-1min"]) < 35:
            # Try loading from disk
            is_crypto = symbol.endswith("USD") or symbol in ["BTC", "ETH"]
            historical = load_from_parquet(symbol, "1min", is_crypto)
            if historical is not None and len(historical) >= 35:
                CANDLES[f"{symbol}-1min"] = historical.tail(3000)
            else:
                return {"ready": False, "reason": "insufficient bars (need 35+)"}
        df = CANDLES[f"{symbol}-1min"].copy()
    else:
        # Aggregate from 1min data
        base_key = f"{symbol}-1min"
        if base_key not in CANDLES or len(CANDLES[base_key]) < 35:
            return {"ready": False, "reason": f"insufficient 1min bars to aggregate to {tf}"}

        df_1min = CANDLES[base_key].copy()
        df_1min["time"] = pd.to_datetime(df_1min["time"])
        df_1min.set_index("time", inplace=True)

        # Resample based on timeframe
        resample_map = {
            "5min": "5T",
            "15min": "15T",
            "1hour": "1H"
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

    if "time" not in df.index.names:
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

    # Bollinger Bands (useful for crypto volatility)
    bbands = ta.bbands(df["close"], length=20, std=2)
    df["bb_upper"] = bbands["BBU_20_2.0"]
    df["bb_middle"] = bbands["BBM_20_2.0"]
    df["bb_lower"] = bbands["BBL_20_2.0"]

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
        "bb_squeeze": (last["bb_upper"] - last["bb_lower"]) / last["bb_middle"] < 0.04,  # Volatility squeeze
        "bb_breakout_up": last["close"] > last["bb_upper"],
        "bb_breakout_dn": last["close"] < last["bb_lower"],
    }

    snapshot = {
        "price": float(last["close"]),
        "ema9": float(last["ema9"]),
        "ma10": float(last["ma10"]),
        "macd": float(last["macd"]),
        "signal": float(last["signal"]),
        "hist": float(last["hist"]),
        "rsi": float(last["rsi"]),
        "bb_upper": float(last["bb_upper"]),
        "bb_middle": float(last["bb_middle"]),
        "bb_lower": float(last["bb_lower"]),
        "time": str(df.index[-1])
    }

    # Determine if crypto
    is_crypto = symbol.endswith("USD") or symbol in ["BTC", "ETH"]

    return {
        "ready": True,
        "symbol": symbol,
        "asset_type": "crypto" if is_crypto else "stock",
        "tf": tf,
        "snapshot": snapshot,
        "crossings": crossings
    }

@mcp.tool()
def get_watchlist() -> Dict[str, Any]:
    """Get current watchlist with latest prices and signals"""
    watchlist = {
        "stocks": [],
        "crypto": []
    }

    for symbol in subscribed_stocks:
        signals = get_signals(symbol, "1min")
        if signals.get("ready"):
            watchlist["stocks"].append({
                "symbol": symbol,
                "price": signals["snapshot"]["price"],
                "rsi": signals["snapshot"]["rsi"],
                "signals": [k for k, v in signals["crossings"].items() if v]
            })

    for symbol in subscribed_crypto:
        signals = get_signals(symbol, "1min")
        if signals.get("ready"):
            watchlist["crypto"].append({
                "symbol": symbol,
                "price": signals["snapshot"]["price"],
                "rsi": signals["snapshot"]["rsi"],
                "signals": [k for k, v in signals["crossings"].items() if v]
            })

    return {
        "watchlist": watchlist,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "market_hours": {
            "stocks": "9:30 AM - 4:00 PM ET (weekdays)",
            "crypto": "24/7"
        }
    }

@mcp.tool()
def get_storage_info() -> Dict[str, Any]:
    """Get information about stored historical data"""
    info = {
        "data_directory": str(DATA_DIR.absolute()),
        "stored_symbols": {},
        "total_size_mb": 0
    }

    if DATA_DIR.exists():
        for asset_type in ["stocks", "crypto"]:
            asset_path = DATA_DIR / asset_type
            if asset_path.exists():
                symbols = set()
                total_size = 0
                for timeframe_dir in asset_path.iterdir():
                    if timeframe_dir.is_dir():
                        for file in timeframe_dir.glob("*.parquet"):
                            symbol = file.stem.split("_")[0]
                            symbols.add(symbol)
                            total_size += file.stat().st_size

                info["stored_symbols"][asset_type] = list(symbols)
                info["total_size_mb"] += total_size / (1024 * 1024)

    info["total_size_mb"] = round(info["total_size_mb"], 2)
    return info

def load_watchlist(filename="watchlist.txt"):
    """Load symbols from watchlist file"""
    symbols = {"stocks": [], "crypto": []}
    try:
        with open(filename, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    symbol = line.upper()
                    # Detect crypto - use Alpaca's "BTC/USD" format
                    if symbol in ["BTC", "ETH", "BCH", "LTC", "UNI", "LINK", "DOGE", "SHIB"]:
                        symbols["crypto"].append(f"{symbol}/USD")
                    else:
                        symbols["stocks"].append(symbol)
        return symbols
    except FileNotFoundError:
        print(f"⚠️  Watchlist file '{filename}' not found")
        return symbols

async def auto_subscribe():
    """Automatically subscribe to watchlist symbols on startup"""
    await asyncio.sleep(2)  # Give server time to start

    symbols = load_watchlist()

    if symbols["stocks"] or symbols["crypto"]:
        print(f"\n📋 Auto-subscribing to symbols from watchlist.txt...")

        # Subscribe stocks and crypto separately
        if symbols["stocks"]:
            print(f"   Stocks: {', '.join(symbols['stocks'])}")
            result = await subscribe(symbols["stocks"], asset_type="stocks")
            if result.get("stocks"):
                print(f"✅ Subscribed to {len(result['stocks'])} stocks")

        if symbols["crypto"]:
            print(f"   Crypto: {', '.join(symbols['crypto'])}")
            result = await subscribe(symbols["crypto"], asset_type="crypto")
            if result.get("crypto"):
                print(f"✅ Subscribed to {len(result['crypto'])} crypto pairs")
            if "errors" in result and result["errors"]:
                for error in result["errors"]:
                    print(f"❌ {error}")
    else:
        print("\n⚠️  No symbols in watchlist.txt - add symbols to the file and restart")

@api.on_event("startup")
async def startup_event():
    """Run after server starts"""
    ensure_data_directories()
    asyncio.create_task(auto_subscribe())

if __name__ == "__main__":
    import uvicorn

    if not API_KEY or not SECRET_KEY:
        print("⚠️  WARNING: Alpaca API credentials not found!")
        print("Please set ALPACA_API_KEY and ALPACA_SECRET_KEY in .env file")
        print("")
        print("Get your API keys from: https://app.alpaca.markets/")
        print("For paper trading (recommended), use the paper trading API keys")

    ensure_data_directories()

    # Load and display watchlist
    symbols = load_watchlist()
    all_symbols = symbols["stocks"] + symbols["crypto"]
    if all_symbols:
        print(f"\n📋 Watchlist loaded:")
        if symbols["stocks"]:
            print(f"   Stocks: {', '.join(symbols['stocks'])}")
        if symbols["crypto"]:
            print(f"   Crypto: {', '.join(symbols['crypto'])}")
    else:
        print("\n⚠️  No symbols found in watchlist.txt")

    print("\n🚀 Starting MCP Chart Signals server (with crypto + storage)")
    print("📈 Status: http://localhost:8742/status")
    print("💾 Data will be saved to: ./data/")
    print("🔄 Auto-subscribing to watchlist.txt symbols...")

    uvicorn.run(api, host="127.0.0.1", port=8742)