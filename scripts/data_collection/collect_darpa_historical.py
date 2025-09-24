#!/usr/bin/env python3
"""
Collect historical data for DARPA frontier tech tickers
This script fetches and stores historical data needed for signal generation
"""

import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
import pytz
import pandas as pd
from dotenv import load_dotenv

# Setup paths
PROJECT_ROOT = Path(__file__).parent.absolute()
DATA_DIR = PROJECT_ROOT / "data"
sys.path.insert(0, str(PROJECT_ROOT))

# Load environment
load_dotenv(PROJECT_ROOT / ".env")

from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame

# DARPA tickers to collect
DARPA_TICKERS = {
    'defense': ['DNA', 'KRMN', 'KTOS', 'AVAV', 'MRCY'],
    'quantum': ['IONQ', 'RGTI', 'QBTS', 'QUBT'],
    'ai_robotics': ['BBAI', 'SOUN', 'ARM', 'PLTR'],
    'nuclear': ['SMR', 'UEC'],
    'space': ['RKLB', 'ASTS', 'LUNR']
}

def ensure_directories():
    """Create necessary data directories"""
    for asset_type in ["stocks"]:
        for timeframe in ["1min", "5min", "15min", "1hour", "daily"]:
            path = DATA_DIR / asset_type / timeframe
            path.mkdir(parents=True, exist_ok=True)

def collect_historical_data(symbol: str, days_back: int = 30):
    """Collect historical data for a symbol"""

    api_key = os.getenv("ALPACA_API_KEY")
    secret_key = os.getenv("ALPACA_SECRET_KEY")

    if not api_key or not secret_key:
        print("❌ API keys not configured")
        return False

    client = StockHistoricalDataClient(api_key, secret_key, raw_data=False)

    # Calculate date range
    end = datetime.now(pytz.UTC)
    start = end - timedelta(days=days_back)

    # Define timeframes - use the enum values directly
    timeframes = [
        (TimeFrame.Minute, "1min"),
        (TimeFrame.Hour, "1hour"),
        (TimeFrame.Day, "daily")
    ]

    success_count = 0

    for tf, tf_name in timeframes:
        try:
            # Fetch data
            request = StockBarsRequest(
                symbol_or_symbols=symbol,
                start=start,
                end=end,
                timeframe=tf,
                adjustment='all',
                feed='sip' if tf_name == 'daily' else 'iex'
            )

            bars = client.get_stock_bars(request)

            if symbol in bars and len(bars[symbol]) > 0:
                # Convert to DataFrame
                data = []
                for bar in bars[symbol]:
                    data.append({
                        'time': bar.timestamp,
                        'open': float(bar.open),
                        'high': float(bar.high),
                        'low': float(bar.low),
                        'close': float(bar.close),
                        'volume': int(bar.volume),
                        'trade_count': int(bar.trade_count) if bar.trade_count else 0,
                        'vwap': float(bar.vwap) if bar.vwap else 0
                    })

                df = pd.DataFrame(data)

                # Save to parquet
                month_str = datetime.now().strftime("%Y-%m")
                file_path = DATA_DIR / "stocks" / tf_name / f"{symbol}_{month_str}.parquet"

                df.to_parquet(file_path, compression='snappy')
                print(f"  ✅ {tf_name}: {len(df)} bars saved")
                success_count += 1
            else:
                print(f"  ⏭️  {tf_name}: No data available")

        except Exception as e:
            if "subscription does not permit" in str(e):
                # Try with IEX feed
                try:
                    request.feed = 'iex'
                    bars = client.get_stock_bars(request)

                    if symbol in bars and len(bars[symbol]) > 0:
                        data = []
                        for bar in bars[symbol]:
                            data.append({
                                'time': bar.timestamp,
                                'open': float(bar.open),
                                'high': float(bar.high),
                                'low': float(bar.low),
                                'close': float(bar.close),
                                'volume': int(bar.volume),
                                'trade_count': 0,
                                'vwap': 0
                            })

                        df = pd.DataFrame(data)
                        month_str = datetime.now().strftime("%Y-%m")
                        file_path = DATA_DIR / "stocks" / tf_name / f"{symbol}_{month_str}.parquet"
                        df.to_parquet(file_path, compression='snappy')
                        print(f"  ✅ {tf_name}: {len(df)} bars saved (IEX feed)")
                        success_count += 1
                except Exception as e2:
                    print(f"  ❌ {tf_name}: {str(e2)[:50]}")
            else:
                print(f"  ❌ {tf_name}: {str(e)[:50]}")

    return success_count > 0

def main():
    print("=" * 60)
    print("🚀 DARPA HISTORICAL DATA COLLECTION")
    print("=" * 60)

    ensure_directories()

    # Collect data for all DARPA tickers
    total_tickers = 0
    success_tickers = 0

    for category, tickers in DARPA_TICKERS.items():
        print(f"\n📊 {category.upper()} SECTOR")
        print("-" * 40)

        for ticker in tickers:
            print(f"\n{ticker}:")
            total_tickers += 1

            if collect_historical_data(ticker, days_back=30):
                success_tickers += 1

    print("\n" + "=" * 60)
    print("📈 COLLECTION COMPLETE")
    print("=" * 60)
    print(f"✅ Successfully collected: {success_tickers}/{total_tickers} tickers")
    print(f"📁 Data saved to: {DATA_DIR}/stocks/")

    # Check what we have
    print("\n📋 Data Inventory:")
    for tf in ["1min", "5min", "15min", "1hour", "daily"]:
        tf_dir = DATA_DIR / "stocks" / tf
        if tf_dir.exists():
            files = list(tf_dir.glob("*.parquet"))
            darpa_files = [f for f in files if any(
                ticker in f.stem for category in DARPA_TICKERS.values()
                for ticker in category
            )]
            if darpa_files:
                print(f"  {tf}: {len(darpa_files)} DARPA ticker files")

if __name__ == "__main__":
    main()