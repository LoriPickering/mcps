# Technical Indicators Specification

## Overview

This document defines the technical indicators used by the MCP Trading servers for market analysis and signal generation.

## Supported Indicators

### 1. Exponential Moving Average (EMA)
- **Parameter**: `ema9` (9-period EMA)
- **Purpose**: Trend identification and support/resistance levels
- **Calculation**: Uses `pandas_ta.ema()` with 9-period lookback
- **Signal**: Price crossing above/below EMA indicates trend change

### 2. Simple Moving Average (SMA)
- **Parameter**: `ma10` (10-period SMA)
- **Purpose**: Trend confirmation and smoothing
- **Calculation**: Uses `pandas_ta.sma()` with 10-period lookback
- **Signal**: Used as secondary trend filter

### 3. MACD (Moving Average Convergence Divergence)
- **Parameters**:
  - Fast: 12 periods
  - Slow: 26 periods
  - Signal: 9 periods
- **Components**:
  - `macd`: Main MACD line (fast EMA - slow EMA)
  - `signal`: Signal line (9-period EMA of MACD)
  - `hist`: Histogram (MACD - Signal)
- **Signals**:
  - `macd_cross_up`: MACD crosses above signal line (bullish)
  - `macd_cross_dn`: MACD crosses below signal line (bearish)

### 4. RSI (Relative Strength Index)
- **Parameter**: `rsi` (14-period RSI)
- **Purpose**: Momentum oscillator for overbought/oversold conditions
- **Range**: 0-100
- **Signals**:
  - `rsi_overbought`: RSI >= 70 (potential sell signal)
  - `rsi_oversold`: RSI <= 30 (potential buy signal)

### 5. Bollinger Bands
- **Parameters**:
  - Length: 20 periods
  - Standard Deviation: 2.0
- **Components**:
  - `bb_upper`: Upper band (SMA + 2*std)
  - `bb_middle`: Middle band (20-period SMA)
  - `bb_lower`: Lower band (SMA - 2*std)
- **Signals**:
  - `bb_squeeze`: Low volatility when (upper - lower) / middle < 0.04
  - `bb_breakout_up`: Price breaks above upper band
  - `bb_breakout_dn`: Price breaks below lower band

## Signal Detection Logic

### Crossing Signals
The system detects crossing events by comparing the last two bars:
- **Previous bar**: `prev = df.iloc[-2]`
- **Current bar**: `last = df.iloc[-1]`

### EMA Support/Resistance
- **EMA Support Lost**: `ema_support_lost`
  - Previous: close >= ema9
  - Current: close < ema9
- **EMA Reclaim**: `ema_reclaim`
  - Previous: close <= ema9
  - Current: close > ema9

## Data Requirements

### Minimum Bars
- **35 bars minimum** required for reliable indicator calculation
- **3000 bars maximum** kept in memory for performance
- Historical data loaded from parquet files when memory insufficient

### Timeframes Supported
- `1min`: 1-minute bars (primary)
- `5min`: 5-minute bars (aggregated from 1min)
- `15min`: 15-minute bars (aggregated from 1min)
- `1hour`: 1-hour bars (aggregated from 1min)

### Aggregation Rules
Higher timeframes are created by resampling 1-minute data:
```python
resample_map = {
    "5min": "5T",
    "15min": "15T",
    "1hour": "1H"
}

aggregation = {
    "open": "first",
    "high": "max",
    "low": "min",
    "close": "last",
    "volume": "sum"
}
```

## Output Format

### Snapshot Data
```json
{
  "price": 150.25,
  "ema9": 149.80,
  "ma10": 149.50,
  "macd": 0.15,
  "signal": 0.12,
  "hist": 0.03,
  "rsi": 65.5,
  "bb_upper": 152.30,
  "bb_middle": 150.00,
  "bb_lower": 147.70,
  "time": "2024-01-15T14:30:00"
}
```

### Crossing Signals
```json
{
  "macd_cross_up": false,
  "macd_cross_dn": false,
  "ema_support_lost": false,
  "ema_reclaim": true,
  "rsi_overbought": false,
  "rsi_oversold": false,
  "bb_squeeze": false,
  "bb_breakout_up": false,
  "bb_breakout_dn": false
}
```

## Asset Type Detection

### Crypto Assets
Symbols are identified as crypto if:
- Symbol ends with "USD" (e.g., "BTC/USD")
- Symbol is in crypto list: ["BTC", "ETH", "BCH", "LTC", "UNI", "LINK", "DOGE", "SHIB"]

### Stock Assets
All other symbols are treated as stocks.

## Performance Considerations

### Memory Management
- Maximum 3000 bars per symbol in memory
- Older data automatically pruned
- Background saving to parquet every 60 seconds

### Storage Format
- Parquet compression: Snappy
- Monthly files: `{symbol}_{YYYY-MM}.parquet`
- Automatic deduplication on timestamps

### Error Handling
- Insufficient data returns: `{"ready": false, "reason": "insufficient bars (need 35+)"}`
- Missing credentials: API error responses
- Stream failures: Automatic reconnection attempts

## Dependencies

- **pandas_ta**: Technical analysis library
- **pandas**: Data manipulation
- **numpy**: Numerical computations (implicit via pandas)

## Version Compatibility

This specification is compatible with:
- pandas_ta >= 0.3.14b
- pandas >= 1.3.0
- Python >= 3.8