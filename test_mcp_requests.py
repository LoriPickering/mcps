#!/usr/bin/env python3
"""
Test ChatGPT's exact MCP requests
"""
import json
import subprocess
import sys

# ChatGPT's exact test requests
test_requests = [
    {
        "name": "check_market_status",
        "request": '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"check_market_status","arguments":{}}}'
    },
    {
        "name": "get_signals_AAPL",
        "request": '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"get_signals","arguments":{"symbol":"AAPL","timeframe":"1min"}}}'
    },
    {
        "name": "get_watchlist",
        "request": '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"get_watchlist","arguments":{}}}'
    },
    {
        "name": "get_storage_info",
        "request": '{"jsonrpc":"2.0","id":4,"method":"tools/call","params":{"name":"get_storage_info","arguments":{}}}'
    }
]

# Additional test for other symbols
additional_tests = [
    {
        "name": "get_signals_NVDA_5min",
        "request": '{"jsonrpc":"2.0","id":5,"method":"tools/call","params":{"name":"get_signals","arguments":{"symbol":"NVDA","timeframe":"5min"}}}'
    },
    {
        "name": "get_signals_BTC_USD",
        "request": '{"jsonrpc":"2.0","id":6,"method":"tools/call","params":{"name":"get_signals","arguments":{"symbol":"BTC/USD","timeframe":"1min"}}}'
    }
]

def test_mcp_server():
    """Run test requests against MCP server"""
    mcp_path = "/Users/loripickering/Projects/mcps/.venv/bin/python"
    server_path = "/Users/loripickering/Projects/mcps/mcp_server.py"

    print("Testing MCP Server Requests for ChatGPT")
    print("=" * 60)

    # First, send initialize
    init_request = '{"jsonrpc":"2.0","method":"initialize","params":{"protocolVersion":"2025-06-18"},"id":0}'

    for test in test_requests + additional_tests:
        print(f"\n### Test: {test['name']}")
        print(f"Request: {test['request'][:100]}...")

        try:
            # Combine init and test request
            full_input = init_request + "\n" + test['request'] + "\n"

            # Run the MCP server with the request
            result = subprocess.run(
                [mcp_path, server_path],
                input=full_input,
                capture_output=True,
                text=True,
                timeout=5
            )

            # Parse output lines
            lines = result.stdout.strip().split('\n')

            # Find the response to our test request (skip init response)
            for line in lines:
                if line and '"id":' in line and f'"id":{test["request"].split('"id":')[1].split(",")[0]}' in line:
                    response = json.loads(line)
                    print(f"Response: {json.dumps(response, indent=2)[:500]}...")

                    # Save full response
                    with open(f"/tmp/mcp_test_{test['name']}.json", "w") as f:
                        json.dump(response, f, indent=2)
                    break

        except subprocess.TimeoutExpired:
            print(f"ERROR: Timeout")
        except Exception as e:
            print(f"ERROR: {e}")

    print("\n" + "=" * 60)
    print("Full responses saved to /tmp/mcp_test_*.json")

if __name__ == "__main__":
    test_mcp_server()