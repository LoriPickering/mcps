# Testing Guide

## Overview

This document provides comprehensive testing guidelines for the MCP Chart Signals project. The testing framework is built using pytest with async support and various testing utilities.

## Test Environment Setup

### Installation

Install development dependencies including testing tools:

```bash
# Install with dev dependencies
pip install -e .[dev]

# Or install test dependencies directly
pip install pytest pytest-asyncio pytest-mock pytest-cov pytest-forked
```

### Configuration

The project uses `pyproject.toml` for pytest configuration:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
```

## Test Structure

### Test Directory Layout

```
tests/
├── __init__.py
├── conftest.py              # Shared fixtures and configuration
├── test_indicators.py       # Technical indicator tests
├── test_integration.py      # Integration tests
└── test_mcp_server.py      # MCP server functionality tests
```

### Key Test Files

- **`conftest.py`**: Contains shared pytest fixtures and test data generators
- **`test_indicators.py`**: Tests for technical analysis calculations
- **`test_integration.py`**: End-to-end integration tests
- **`test_mcp_server.py`**: MCP server core functionality tests

## Running Tests

### Basic Test Execution

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_indicators.py

# Run specific test function
pytest tests/test_indicators.py::test_rsi_calculation

# Run with verbose output
pytest -v

# Run with coverage
pytest --cov=servers --cov-report=html
```

### Parallel Test Execution

```bash
# Run tests in parallel (requires pytest-xdist)
pytest -n auto

# Run with forked processes (requires pytest-forked)
pytest --forked
```

### Test Categories

```bash
# Run only unit tests (fast)
pytest -m "not integration"

# Run only integration tests
pytest -m integration

# Run async tests specifically
pytest -k "async"
```

## Test Fixtures

### Core Fixtures (from conftest.py)

#### `mcp_server`
Creates an MCP server instance for testing:
```python
@pytest.fixture
def mcp_server():
    return MCPServer()
```

#### `sample_ohlcv_data`
Generates realistic OHLCV market data for testing:
```python
# Usage in tests
def test_indicator_calculation(sample_ohlcv_data):
    df = sample_ohlcv_data
    assert len(df) > 0
    assert 'close' in df.columns
```

#### `sample_ohlcv_with_indicators`
Provides OHLCV data with pre-calculated indicators:
```python
# Includes: RSI, MACD, Bollinger Bands
def test_signal_detection(sample_ohlcv_with_indicators):
    df = sample_ohlcv_with_indicators
    assert 'rsi' in df.columns
    assert 'macd' in df.columns
```

#### `test_symbols`
Standard test symbols for various asset types:
```python
# Includes: ['AAPL', 'BTC/USD', 'BTC', 'ETH/USD', 'TSLA', 'SPY']
def test_multi_symbol(test_symbols):
    for symbol in test_symbols:
        # Test with each symbol type
        pass
```

#### `test_timeframes`
Standard timeframes for testing:
```python
# Includes: ['1min', '5min', '15min', '1hour']
def test_timeframe_aggregation(test_timeframes):
    for tf in test_timeframes:
        # Test aggregation logic
        pass
```

#### `mock_market_data`
Pre-defined market scenarios for testing:
```python
# Scenarios: bullish, bearish, neutral, overbought, oversold
def test_market_conditions(mock_market_data):
    bullish_data = mock_market_data['bullish']
    assert bullish_data['rsi'] > 50
```

## Test Categories

### Unit Tests

Test individual functions and methods in isolation:

```python
def test_rsi_calculation():
    """Test RSI calculation accuracy"""
    # Mock data
    prices = [100, 101, 102, 101, 100, 99, 100, 101]
    df = pd.DataFrame({'close': prices})

    # Calculate RSI
    result = calculate_rsi(df['close'], period=14)

    # Assertions
    assert isinstance(result, pd.Series)
    assert not result.isna().all()
```

### Integration Tests

Test component interactions and data flow:

```python
@pytest.mark.asyncio
async def test_real_time_data_processing():
    """Test end-to-end data processing pipeline"""
    server = MCPServer()

    # Simulate incoming bar data
    bar_data = create_test_bar('AAPL', 150.0)

    # Process through pipeline
    result = await server.process_bar(bar_data)

    # Verify complete processing
    assert result['ready'] is True
    assert 'snapshot' in result
    assert 'crossings' in result
```

### Mock Tests

Test external dependencies using mocks:

```python
@pytest.mark.asyncio
async def test_alpaca_api_mock(mocker):
    """Test Alpaca API integration with mocking"""
    # Mock Alpaca API responses
    mock_client = mocker.patch('alpaca.data.StockDataStream')
    mock_client.return_value.subscribe_bars.return_value = None

    # Test subscription logic
    result = await subscribe_to_symbol('AAPL')

    # Verify mock was called correctly
    mock_client.assert_called_once()
    assert result['success'] is True
```

## Test Data Management

### Reproducible Test Data

Tests use seeded random data for reproducibility:

```python
# In conftest.py
np.random.seed(42)  # Ensures consistent test data
```

### Test Data Scenarios

The test suite includes various market scenarios:

- **Trending Markets**: Consistent upward/downward movement
- **Sideways Markets**: Range-bound price action
- **Volatile Markets**: High price swings
- **Low Volume**: Minimal trading activity
- **High Volume**: Heavy trading periods

## Performance Testing

### Benchmark Tests

```python
def test_indicator_performance(benchmark, sample_ohlcv_data):
    """Benchmark indicator calculation speed"""
    result = benchmark(calculate_all_indicators, sample_ohlcv_data)
    assert result is not None
```

### Memory Usage Tests

```python
def test_memory_usage():
    """Ensure memory usage stays within bounds"""
    import psutil
    import os

    process = psutil.Process(os.getpid())
    initial_memory = process.memory_info().rss

    # Run memory-intensive operations
    large_dataset = generate_large_ohlcv_data(100000)
    process_indicators(large_dataset)

    final_memory = process.memory_info().rss
    memory_increase = final_memory - initial_memory

    # Assert memory increase is reasonable (< 100MB)
    assert memory_increase < 100 * 1024 * 1024
```

## Error Handling Tests

### Invalid Data Tests

```python
def test_invalid_symbol():
    """Test handling of invalid symbols"""
    with pytest.raises(ValueError, match="Invalid symbol"):
        get_signals("INVALID_SYMBOL_123")

def test_insufficient_data():
    """Test handling of insufficient data"""
    small_df = pd.DataFrame({'close': [100, 101]})  # Only 2 bars
    result = calculate_indicators(small_df)
    assert result['ready'] is False
    assert "insufficient data" in result['reason']
```

### Network Error Tests

```python
@pytest.mark.asyncio
async def test_api_connection_failure(mocker):
    """Test graceful handling of API failures"""
    # Mock network failure
    mock_client = mocker.patch('alpaca.data.StockDataStream')
    mock_client.side_effect = ConnectionError("API unavailable")

    result = await attempt_subscription('AAPL')
    assert result['success'] is False
    assert 'connection' in result['error'].lower()
```

## Continuous Integration

### GitHub Actions Integration

```yaml
# .github/workflows/test.yml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.12]
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: ${{ matrix.python-version }}
      - name: Install dependencies
        run: |
          pip install -e .[dev]
      - name: Run tests
        run: |
          pytest --cov=servers --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

### Pre-commit Hooks

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: pytest
        name: pytest
        entry: pytest
        language: system
        types: [python]
        stages: [commit]
```

## Test Best Practices

### Writing Effective Tests

1. **Use Descriptive Names**: Test names should clearly describe what is being tested
2. **Follow AAA Pattern**: Arrange, Act, Assert
3. **Test One Thing**: Each test should verify a single behavior
4. **Use Fixtures**: Leverage pytest fixtures for setup and teardown
5. **Mock External Dependencies**: Isolate tests from external services

### Test Data Guidelines

1. **Use Realistic Data**: Test data should mirror production scenarios
2. **Include Edge Cases**: Test boundary conditions and error states
3. **Maintain Data Consistency**: Use seeded random generation for reproducibility
4. **Clean Up**: Ensure tests don't leave behind test data

### Async Testing

```python
@pytest.mark.asyncio
async def test_async_operation():
    """Test async functions properly"""
    result = await async_function()
    assert result is not None

# For async fixtures
@pytest.fixture
async def async_setup():
    """Async fixture example"""
    await setup_async_resources()
    yield
    await cleanup_async_resources()
```

## Debugging Tests

### Debug Mode

```bash
# Run tests with debugging
pytest --pdb  # Drop into debugger on failures
pytest -s    # Show print statements
pytest --tb=long  # Detailed tracebacks
```

### Logging in Tests

```python
import logging

def test_with_logging(caplog):
    """Test with log capture"""
    with caplog.at_level(logging.INFO):
        function_that_logs()

    assert "Expected log message" in caplog.text
```

## Coverage Requirements

- **Minimum Coverage**: 85% for core functionality
- **Critical Paths**: 95% for indicator calculations
- **Error Handling**: 100% for error scenarios

### Generate Coverage Reports

```bash
# HTML coverage report
pytest --cov=servers --cov-report=html

# Terminal coverage report
pytest --cov=servers --cov-report=term-missing

# XML coverage for CI
pytest --cov=servers --cov-report=xml
```

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure project root is in Python path
2. **Async Test Failures**: Use `@pytest.mark.asyncio` decorator
3. **Fixture Scope Issues**: Check fixture scope (function/session/module)
4. **Mock Not Working**: Verify mock patch path is correct
5. **Data Inconsistency**: Use seeded random generation

### Performance Issues

1. **Slow Tests**: Profile with `pytest --durations=10`
2. **Memory Leaks**: Use memory profilers and cleanup fixtures
3. **Flaky Tests**: Investigate timing issues and race conditions