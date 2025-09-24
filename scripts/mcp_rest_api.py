#!/usr/bin/env python3
"""REST API wrapper for MCP server - share with any agent"""

from flask import Flask, jsonify, request
from flask_cors import CORS
import sys
from pathlib import Path
from datetime import datetime

# Setup paths
sys.path.insert(0, str(Path(__file__).parent))

# Load environment
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")

from servers.trading.mcp_server_integrated import MCPServer

app = Flask(__name__)
CORS(app)  # Allow cross-origin requests
server = MCPServer()

@app.route('/')
def home():
    """API documentation"""
    return jsonify({
        "name": "MCP Trading Signals API",
        "version": "1.0",
        "endpoints": {
            "GET /api/signals/<symbol>": "Get trading signals",
            "GET /api/watchlist": "Get watchlist with prices",
            "GET /api/darpa/events": "Get DARPA frontier tech events",
            "GET /api/macro/events": "Get macro economic events",
            "POST /api/tickers/check": "Check ticker availability",
            "GET /api/status": "Server status"
        },
        "example": "/api/signals/IONQ?timeframe=5min"
    })

@app.route('/api/status')
def status():
    """Server status"""
    return jsonify({
        "status": "online",
        "timestamp": datetime.now().isoformat(),
        "capabilities": {
            "trading_signals": True,
            "darpa_monitoring": True,
            "macro_events": True,
            "news_sentiment": True
        }
    })

@app.route('/api/signals/<symbol>')
def get_signals(symbol):
    """Get trading signals for a symbol"""
    try:
        timeframe = request.args.get('timeframe', '1min')
        result = server.get_signals(symbol, timeframe)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/watchlist')
def get_watchlist():
    """Get current watchlist"""
    try:
        result = server.get_watchlist()
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/darpa/events')
def get_darpa_events():
    """Get DARPA frontier tech events"""
    try:
        hours_back = int(request.args.get('hours_back', 24))
        source = request.args.get('source', 'all')
        result = server.get_darpa_events(hours_back, source)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/macro/events')
def get_macro_events():
    """Get macro economic events"""
    try:
        hours_ahead = int(request.args.get('hours_ahead', 48))
        min_importance = request.args.get('min_importance', 'medium')
        result = server.get_macro_events(hours_ahead, min_importance)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/tickers/check', methods=['POST'])
def check_tickers():
    """Check ticker availability"""
    try:
        data = request.get_json()
        symbols = data.get('symbols', [])

        if not symbols:
            return jsonify({"error": "No symbols provided"}), 400

        result = server.check_ticker_availability(symbols)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/powell/schedule')
def get_powell_schedule():
    """Get Powell speaking schedule"""
    try:
        result = server.get_powell_schedule()
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    print("=" * 60)
    print("🚀 MCP REST API Server")
    print("=" * 60)
    print("\n📡 Starting server on http://localhost:5000")
    print("\n📚 API Endpoints:")
    print("  GET  /                           - API documentation")
    print("  GET  /api/status                 - Server status")
    print("  GET  /api/signals/<symbol>       - Trading signals")
    print("  GET  /api/watchlist              - Watchlist with prices")
    print("  GET  /api/darpa/events           - DARPA events")
    print("  GET  /api/macro/events           - Economic events")
    print("  GET  /api/powell/schedule        - Powell speeches")
    print("  POST /api/tickers/check          - Check tickers")
    print("\n💡 Examples:")
    print("  curl http://localhost:5000/api/signals/IONQ")
    print("  curl http://localhost:5000/api/darpa/events?hours_back=168")
    print("\n🔗 Share this URL with ChatGPT, local models, or any HTTP client")
    print("=" * 60)

    app.run(host='0.0.0.0', port=5000, debug=False)