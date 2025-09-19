#!/usr/bin/env python3
"""
Check which symbols from watchlist are available on Alpaca
"""
import os
from dotenv import load_dotenv
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import GetAssetsRequest
from alpaca.data.historical import StockHistoricalDataClient, CryptoHistoricalDataClient
from alpaca.data.requests import StockBarsRequest, CryptoBarsRequest
from alpaca.data.timeframe import TimeFrame
from datetime import datetime, timedelta
import asyncio

load_dotenv()

API_KEY = os.getenv("ALPACA_API_KEY")
SECRET_KEY = os.getenv("ALPACA_SECRET_KEY")

def load_watchlist():
    """Load symbols from watchlist file"""
    symbols = {"stocks": [], "crypto": []}
    try:
        with open("watchlist.txt", "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    symbol = line.upper()
                    if symbol in ["BTC", "ETH", "BCH", "LTC", "UNI", "LINK", "DOGE", "SHIB"]:
                        symbols["crypto"].append(f"{symbol}USD")
                    else:
                        symbols["stocks"].append(symbol)
        return symbols
    except FileNotFoundError:
        print("watchlist.txt not found")
        return symbols

def check_tradeable_assets():
    """Check which stocks are tradeable on Alpaca"""
    print("\n📊 Checking Stock Availability on Alpaca...")
    print("=" * 50)

    trading = TradingClient(API_KEY, SECRET_KEY, paper=True)
    symbols = load_watchlist()

    # Get all assets
    assets_request = GetAssetsRequest(status="active", asset_class="us_equity")
    assets = trading.get_all_assets(assets_request)

    # Create a set of tradeable symbols
    tradeable_symbols = {asset.symbol for asset in assets if asset.tradable}

    print(f"Total tradeable stocks on Alpaca: {len(tradeable_symbols)}\n")

    # Check each symbol in watchlist
    print("Stock Status:")
    for symbol in symbols["stocks"]:
        if symbol in tradeable_symbols:
            # Get asset details
            try:
                asset = trading.get_asset(symbol)
                status = f"✅ Available - {asset.name[:30]}"
                if not asset.easy_to_borrow:
                    status += " (Hard to borrow)"
                if asset.marginable:
                    status += " (Marginable)"
            except:
                status = "✅ Available"
        else:
            status = "❌ Not available on Alpaca"
        print(f"  {symbol:6} {status}")

    return tradeable_symbols

def check_crypto_availability():
    """Check which cryptos are available and have recent data"""
    print("\n🪙 Checking Crypto Availability...")
    print("=" * 50)

    symbols = load_watchlist()
    crypto_client = CryptoHistoricalDataClient(API_KEY, SECRET_KEY)

    # Common crypto symbols on Alpaca - they use "BTC/USD" format
    all_crypto = [
        "BTC/USD", "ETH/USD", "LTC/USD", "BCH/USD", "UNI/USD", "LINK/USD",
        "MATIC/USD", "ALGO/USD", "DOGE/USD", "SHIB/USD", "AVAX/USD", "GRT/USD"
    ]

    print(f"Testing crypto symbols from watchlist: {symbols['crypto']}\n")

    print("Crypto Status:")
    for symbol in symbols["crypto"]:
        try:
            # Try to get recent bars
            request = CryptoBarsRequest(
                symbol_or_symbols=symbol,
                timeframe=TimeFrame.Minute,
                start=datetime.now() - timedelta(hours=1)
            )
            bars = crypto_client.get_crypto_bars(request)

            if symbol in bars.data and len(bars.data[symbol]) > 0:
                latest_bar = bars.data[symbol][-1]
                print(f"  {symbol:8} ✅ Available - Latest: ${latest_bar.close:.2f} @ {latest_bar.timestamp}")
            else:
                print(f"  {symbol:8} ⚠️  Available but no recent data")
        except Exception as e:
            print(f"  {symbol:8} ❌ Not available: {str(e)[:50]}")

    print(f"\nOther available crypto on Alpaca:")
    for symbol in all_crypto:
        if symbol not in symbols["crypto"]:
            try:
                request = CryptoBarsRequest(
                    symbol_or_symbols=symbol,
                    timeframe=TimeFrame.Minute,
                    start=datetime.now() - timedelta(hours=1),
                    limit=1
                )
                bars = crypto_client.get_crypto_bars(request)
                if symbol in bars.data and len(bars.data[symbol]) > 0:
                    print(f"  {symbol:8} (not in watchlist)")
            except:
                pass

async def check_live_data_flow():
    """Check if data is currently flowing"""
    print("\n📡 Checking Live Data Flow...")
    print("=" * 50)

    import httpx

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:8742/status")
            status = response.json()

            print("\nCurrent Server Status:")
            print(f"  Stocks stream active: {status['streams']['stocks_active']}")
            print(f"  Crypto stream active: {status['streams']['crypto_active']}")

            print("\nData Received (bar counts):")

            # Separate stocks and crypto
            stocks_data = {k: v for k, v in status['bar_counts'].items() if not k.startswith(("BTC", "ETH"))}
            crypto_data = {k: v for k, v in status['bar_counts'].items() if k.startswith(("BTC", "ETH"))}

            if stocks_data:
                print("  Stocks:")
                for symbol, count in sorted(stocks_data.items()):
                    print(f"    {symbol:15} {count:3} bars")
            else:
                print("  Stocks: No data yet")

            if crypto_data:
                print("  Crypto:")
                for symbol, count in sorted(crypto_data.items()):
                    print(f"    {symbol:15} {count:3} bars")
            else:
                print("  Crypto: No data flowing yet")

            # Wait and check again
            if not crypto_data:
                print("\n⏳ Waiting 10 seconds to check for crypto data...")
                await asyncio.sleep(10)

                response = await client.get("http://localhost:8742/status")
                status = response.json()
                crypto_data = {k: v for k, v in status['bar_counts'].items() if k.startswith(("BTC", "ETH"))}

                if crypto_data:
                    print("  Crypto update:")
                    for symbol, count in sorted(crypto_data.items()):
                        print(f"    {symbol:15} {count:3} bars")
                else:
                    print("  Still no crypto data - may need to check if crypto markets are active")

    except Exception as e:
        print(f"  Error checking server: {e}")
        print("  Make sure the server is running (make run)")

def suggest_alternatives():
    """Suggest alternative symbols for those not available"""
    print("\n💡 Suggestions:")
    print("=" * 50)

    suggestions = {
        "DOXL": "Consider TQQQ (3x Nasdaq) or SPXL (3x S&P 500) instead",
        "NVDX": "Consider NVDA (base stock) or SOXL (3x semiconductors)",
        "AAPX": "This might be a typo - did you mean AAPL?",
        "NANO": "Consider NNDM or other nano-tech stocks"
    }

    symbols = load_watchlist()
    for symbol in symbols["stocks"]:
        if symbol in suggestions:
            print(f"  {symbol}: {suggestions[symbol]}")

if __name__ == "__main__":
    print("🔍 Alpaca Symbol Validator")
    print("=" * 50)

    if not API_KEY or not SECRET_KEY:
        print("❌ ERROR: Alpaca API credentials not found!")
        print("Please set ALPACA_API_KEY and ALPACA_SECRET_KEY in .env file")
        exit(1)

    # Check stocks
    tradeable_symbols = check_tradeable_assets()

    # Check crypto
    check_crypto_availability()

    # Check live data
    print("\nChecking live data flow from server...")
    asyncio.run(check_live_data_flow())

    # Suggestions
    suggest_alternatives()

    print("\n✅ Check complete!")