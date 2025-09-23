"""
Pytest configuration and shared fixtures for MCP server testing
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timezone, timedelta
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(PROJECT_ROOT))

from servers.trading.mcp_server_integrated import MCPServer


@pytest.fixture
def mcp_server():
    """Create an MCP server instance for testing"""
    return MCPServer()


@pytest.fixture
def sample_ohlcv_data():
    """Create sample OHLCV data for testing"""
    dates = pd.date_range(
        start=datetime.now(timezone.utc) - timedelta(days=1),
        end=datetime.now(timezone.utc),
        freq='1min'
    )

    np.random.seed(42)  # For reproducible tests

    # Generate realistic price data
    base_price = 100.0
    price_changes = np.random.normal(0, 0.5, len(dates))
    prices = [base_price]

    for change in price_changes[1:]:
        new_price = prices[-1] + change
        prices.append(max(new_price, 1.0))  # Ensure price doesn't go negative

    # Generate OHLCV data
    data = []
    for i, (date, price) in enumerate(zip(dates, prices)):
        high = price + np.random.uniform(0, 1)
        low = price - np.random.uniform(0, 1)
        open_price = prices[i-1] if i > 0 else price
        close_price = price
        volume = np.random.randint(1000, 10000)

        data.append({
            'timestamp': date,
            'open': open_price,
            'high': high,
            'low': low,
            'close': close_price,
            'volume': volume
        })

    df = pd.DataFrame(data)
    df.set_index('timestamp', inplace=True)
    return df


@pytest.fixture
def sample_ohlcv_with_indicators():
    """Create sample OHLCV data with pre-calculated indicators"""
    dates = pd.date_range(
        start=datetime.now(timezone.utc) - timedelta(days=1),
        end=datetime.now(timezone.utc),
        freq='1min'
    )

    np.random.seed(42)

    # Generate more realistic trending data
    base_price = 100.0
    trend_strength = 0.001

    data = []
    for i, date in enumerate(dates):
        # Add some trend + noise
        price = base_price + (i * trend_strength) + np.random.normal(0, 0.2)
        high = price + np.random.uniform(0, 0.5)
        low = price - np.random.uniform(0, 0.5)
        open_price = data[i-1]['close'] if i > 0 else price
        volume = np.random.randint(1000, 10000)

        data.append({
            'timestamp': date,
            'open': open_price,
            'high': high,
            'low': low,
            'close': price,
            'volume': volume
        })

    df = pd.DataFrame(data)
    df.set_index('timestamp', inplace=True)

    # Add indicators
    df['rsi'] = pd.Series([50 + np.random.normal(0, 10) for _ in range(len(df))], index=df.index)
    df['rsi'] = df['rsi'].clip(0, 100)

    # Simple MACD simulation
    df['macd'] = pd.Series([np.random.normal(0, 0.5) for _ in range(len(df))], index=df.index)
    df['macd_signal'] = df['macd'].rolling(9).mean()
    df['macd_histogram'] = df['macd'] - df['macd_signal']

    # Bollinger Bands simulation
    df['bb_upper'] = df['close'] + np.random.uniform(1, 3, len(df))
    df['bb_lower'] = df['close'] - np.random.uniform(1, 3, len(df))
    df['bb_middle'] = (df['bb_upper'] + df['bb_lower']) / 2

    return df


@pytest.fixture
def test_symbols():
    """List of test symbols for various scenarios"""
    return [
        'AAPL',      # Regular stock
        'BTC/USD',   # Crypto with slash
        'BTC',       # Crypto without slash
        'ETH/USD',   # Another crypto
        'TSLA',      # Volatile stock
        'SPY'        # ETF
    ]


@pytest.fixture
def test_timeframes():
    """List of test timeframes"""
    return ['1min', '5min', '15min', '1hour']


@pytest.fixture
def mock_market_data():
    """Mock market data for different scenarios"""
    return {
        'bullish': {
            'rsi': 65,
            'macd': 0.5,
            'macd_signal': 0.3,
            'bb_position': 0.8,  # Close to upper band
            'price_change': 2.5
        },
        'bearish': {
            'rsi': 35,
            'macd': -0.5,
            'macd_signal': -0.3,
            'bb_position': 0.2,  # Close to lower band
            'price_change': -2.5
        },
        'neutral': {
            'rsi': 50,
            'macd': 0.1,
            'macd_signal': 0.05,
            'bb_position': 0.5,  # Middle of bands
            'price_change': 0.1
        },
        'overbought': {
            'rsi': 80,
            'macd': 1.0,
            'macd_signal': 0.8,
            'bb_position': 0.95,  # Very close to upper band
            'price_change': 5.0
        },
        'oversold': {
            'rsi': 20,
            'macd': -1.0,
            'macd_signal': -0.8,
            'bb_position': 0.05,  # Very close to lower band
            'price_change': -5.0
        }
    }


@pytest.fixture
def sample_response_structure():
    """Expected response structure for validation"""
    return {
        'ready': bool,
        'reason': str,
        'snapshot': {
            'price': float,
            'rsi': float,
            'macd': float,
            'bb_upper': float,
            'bb_lower': float,
            'bb_middle': float,
            'volume': int
        },
        'prev_snapshot': {
            'price': float,
            'rsi': float,
            'macd': float
        },
        'trend_state': str,
        'crossings': dict,
        'bars_since': dict,
        'risk_anchor': {
            'type': str,
            'price': float,
            'distance_pct': float,
            'reasoning': str
        }
    }