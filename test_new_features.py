#!/usr/bin/env python
"""Test script for new MCP server features"""

import sys
import os
sys.path.insert(0, '/Users/loripickering/Projects/mcps')
os.chdir('/Users/loripickering/Projects/mcps')

from servers.trading.mcp_server_integrated import MCPServer

def test_signals(symbol, timeframe='1min'):
    server = MCPServer()
    result = server.get_signals(symbol, timeframe)

    print(f"\n{'='*60}")
    print(f"Testing {symbol} ({timeframe})")
    print('='*60)

    if result.get('ready'):
        snapshot = result.get('snapshot', {})
        prev_snapshot = result.get('prev_snapshot', {})
        risk_anchor = result.get('risk_anchor', {})

        print(f"✅ Signal Ready!")
        print(f"\n📊 Market State:")
        print(f"  Current Price: ${snapshot.get('price'):.2f}")
        print(f"  Previous Price: ${prev_snapshot.get('price'):.2f}")
        price_change = snapshot.get('price', 0) - prev_snapshot.get('price', 0)
        print(f"  Price Change: ${price_change:.2f} ({price_change/prev_snapshot.get('price', 1)*100:.2f}%)")

        print(f"\n🎯 Trend Analysis:")
        print(f"  Trend State: {result.get('trend_state').upper()}")
        print(f"  RSI: {snapshot.get('rsi'):.1f}")
        print(f"  MACD: {snapshot.get('macd'):.2f}")

        print(f"\n⚠️  Risk Management:")
        print(f"  Stop Type: {risk_anchor.get('type')}")
        print(f"  Stop Price: ${risk_anchor.get('price'):.2f}")
        print(f"  Stop Distance: {risk_anchor.get('distance_pct'):.2f}%")
        print(f"  Reasoning: {risk_anchor.get('reasoning')}")

        print(f"\n🚦 Active Signals:")
        crossings = result.get('crossings', {})
        active_crossings = [k for k, v in crossings.items() if v]
        if active_crossings:
            for signal in active_crossings:
                bars = result.get('bars_since', {}).get(signal)
                print(f"  • {signal} ({bars} bars ago)")
        else:
            print("  • No active crossings")

    else:
        print(f"❌ Not Ready: {result.get('reason')}")

# Test multiple symbols
test_symbols = [
    ('AAPL', '1min'),
    ('BTC/USD', '1min'),
    ('ETH/USD', '1min'),
    ('TSLA', '1min')
]

for symbol, tf in test_symbols:
    try:
        test_signals(symbol, tf)
    except Exception as e:
        print(f"\n❌ Error testing {symbol}: {e}")

print(f"\n{'='*60}")
print("✅ All tests completed!")
print('='*60)