#!/usr/bin/env python
"""Check status of MCP trading system"""

import subprocess
import pandas as pd
from pathlib import Path
from datetime import datetime, timezone, timedelta

print("=" * 60)
print("MCP TRADING SYSTEM STATUS")
print("=" * 60)

# Check servers
print("\n📡 SERVER STATUS:")
print("-" * 40)

# Check data collection server
result = subprocess.run("ps aux | grep ta_server_full | grep -v grep", shell=True, capture_output=True, text=True)
if result.stdout:
    print("✅ Data Collection Server: RUNNING")
    pid = result.stdout.split()[1]
    print(f"   PID: {pid}")
else:
    print("❌ Data Collection Server: NOT RUNNING")
    print("   Run: make run")

# Check MCP server
result = subprocess.run("ps aux | grep mcp_server_integrated | grep -v grep", shell=True, capture_output=True, text=True)
if result.stdout:
    print("✅ MCP Server: RUNNING")
    pid = result.stdout.split()[1]
    print(f"   PID: {pid}")
else:
    print("⚠️  MCP Server: NOT RUNNING")
    print("   (Auto-starts when Claude Desktop connects)")

# Check data status
print("\n📊 DATA STATUS:")
print("-" * 40)

data_dir = Path("data")
total_files = 0
total_rows = 0
fresh_symbols = []
stale_symbols = []

for asset_type in ["stocks", "crypto"]:
    type_files = 0
    type_rows = 0

    for timeframe in ["1min", "5min", "15min", "1hour"]:
        tf_dir = data_dir / asset_type / timeframe
        if tf_dir.exists():
            files = list(tf_dir.glob("*.parquet"))
            type_files += len(files)

            # Check 1min data freshness
            if timeframe == "1min":
                for file in files:
                    try:
                        df = pd.read_parquet(file)
                        type_rows += len(df)

                        if len(df) > 0:
                            last_time = pd.to_datetime(df["time"].max())
                            age = datetime.now(timezone.utc) - last_time
                            symbol = file.stem.split("_")[0]

                            if asset_type == "crypto":
                                symbol = symbol.replace("_", "/")

                            if age < timedelta(minutes=5):
                                fresh_symbols.append(f"{symbol} ({asset_type[0].upper()})")
                            elif age > timedelta(hours=1):
                                stale_symbols.append(f"{symbol} ({asset_type[0].upper()}, {age.days}d)")
                    except:
                        pass

    print(f"\n{asset_type.upper()}:")
    print(f"  Files: {type_files}")
    print(f"  1min bars: {type_rows:,}")
    total_files += type_files
    total_rows += type_rows

print(f"\nTOTAL: {total_files} files, {total_rows:,} data points")

if fresh_symbols:
    print(f"\n✅ Fresh data (< 5 min old): {', '.join(fresh_symbols[:5])}")
    if len(fresh_symbols) > 5:
        print(f"   ... and {len(fresh_symbols)-5} more")

if stale_symbols:
    print(f"\n⚠️  Stale data: {', '.join(stale_symbols[:5])}")
    if len(stale_symbols) > 5:
        print(f"   ... and {len(stale_symbols)-5} more")

# Test MCP functionality
print("\n🧪 MCP FUNCTIONALITY TEST:")
print("-" * 40)

try:
    import sys
    sys.path.insert(0, str(Path.cwd()))
    from servers.trading.mcp_server_integrated import MCPServer

    server = MCPServer()
    test_symbols = ["AAPL", "BTC", "ETH"]

    for symbol in test_symbols:
        result = server.get_signals(symbol, "1min")
        if result.get("ready"):
            price = result.get("snapshot", {}).get("price")
            trend = result.get("trend_state")
            print(f"✅ {symbol}: ${price:.2f} ({trend})")
        else:
            print(f"❌ {symbol}: {result.get('reason')}")
except Exception as e:
    print(f"❌ MCP test failed: {e}")

print("\n" + "=" * 60)
print("Use 'make run' to start data collection")
print("Claude Desktop will auto-start MCP server when needed")
print("=" * 60)