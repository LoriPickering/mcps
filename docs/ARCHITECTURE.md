# System Architecture

## Overview

The MCP Chart Signals project is a distributed system that provides real-time trading indicators and signals through the Model Context Protocol (MCP). The system integrates with Alpaca Markets for live market data and uses technical analysis to generate trading signals.

## High-Level Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│                 │    │                 │    │                 │
│   MCP Client    │◄──►│   MCP Server    │◄──►│ Alpaca Markets  │
│   (Claude/IDE)  │    │ Chart Signals   │    │   Live Data     │
│                 │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                              │
                       ┌─────────────────┐
                       │                 │
                       │  Data Storage   │
                       │  (Parquet)      │
                       │                 │
                       └─────────────────┘
```

## Core Components

### 1. MCP Server Layer
- **Location**: `/servers/trading/`
- **Primary**: `mcp_server_integrated.py`
- **Alternative**: `ta_server_full.py` (FastAPI version)

#### Responsibilities:
- Implements MCP protocol for client communication
- Manages real-time data streams from Alpaca
- Calculates technical indicators
- Detects trading signals and crossings
- Provides historical data access

#### Key Classes:
- `MCPServer`: Main server implementation
- Data processing functions for indicators
- Signal detection algorithms

### 2. Data Management Layer

#### Real-Time Data Stream
- **Source**: Alpaca Markets WebSocket API
- **Assets**: Stocks and Cryptocurrencies
- **Timeframes**: 1min (primary), aggregated to 5min, 15min, 1hour
- **Storage**: In-memory cache (3000 bars max per symbol)

#### Historical Data Storage
- **Format**: Parquet files with Snappy compression
- **Structure**:
  ```
  data/
  ├── stocks/
  │   ├── 1min/
  │   ├── 5min/
  │   ├── 15min/
  │   └── 1hour/
  └── crypto/
      ├── 1min/
      ├── 5min/
      ├── 15min/
      └── 1hour/
  ```
- **File Naming**: `{symbol}_{YYYY-MM}.parquet`
- **Retention**: Monthly files, automatic deduplication

### 3. Technical Analysis Engine

#### Supported Indicators:
- **Moving Averages**: EMA(9), SMA(10)
- **Momentum**: RSI(14), MACD(12,26,9)
- **Volatility**: Bollinger Bands(20,2.0)
- **Volume**: VWAP

#### Signal Detection:
- MACD crossovers (bullish/bearish)
- EMA support/resistance breaks
- RSI overbought/oversold conditions
- Bollinger Band breakouts and squeezes

### 4. Protocol Layer

#### MCP Protocol Implementation
- **Tools**: Exposed as MCP tools for client access
- **Communication**: JSON-RPC over stdio
- **Error Handling**: Graceful degradation and error reporting

#### FastAPI Alternative
- **REST API**: HTTP endpoints for web integration
- **Real-time**: WebSocket support for live updates
- **Documentation**: Auto-generated OpenAPI specs

## Data Flow

### 1. Market Data Ingestion
```
Alpaca WebSocket → Data Validator → In-Memory Cache → Parquet Storage
                                         │
                                    Indicator Calculator
                                         │
                                    Signal Detector
```

### 2. Client Request Processing
```
MCP Client → MCP Server → Cache Check → Historical Load → Indicator Calc → Response
```

### 3. Real-Time Updates
```
Live Bar Data → Process Indicators → Detect Signals → Cache Update → Background Save
```

## Configuration Management

### Environment Variables
- `ALPACA_API_KEY`: Alpaca API authentication
- `ALPACA_SECRET_KEY`: Alpaca secret key
- `ALPACA_BASE_URL`: API endpoint (paper/live trading)

### Configuration Files
- `pyproject.toml`: Project dependencies and settings
- `watchlist.txt`: Auto-subscribe symbols on startup
- `.env`: Environment-specific configuration

## Deployment Architecture

### Development Setup
```
Local Development Environment
├── Python 3.12+ Virtual Environment
├── MCP Server Process
├── Local Data Storage (./data/)
└── Test Market Data Stream
```

### Production Considerations
```
Production Environment
├── Container (Docker)
├── External Data Storage (Cloud/NFS)
├── Load Balancer (Multiple Instances)
├── Monitoring & Alerting
└── Real Market Data Feed
```

## Scalability Design

### Horizontal Scaling
- **Stateless Server**: Each server instance is independent
- **Shared Storage**: Parquet files can be shared across instances
- **Load Balancing**: Distribute clients across server instances

### Vertical Scaling
- **Memory Optimization**: Configurable in-memory cache limits
- **CPU Optimization**: Efficient indicator calculations using pandas/numpy
- **I/O Optimization**: Asynchronous file operations

### Data Partitioning
- **By Symbol**: Different symbols on different instances
- **By Timeframe**: Separate instances for different timeframes
- **By Asset Type**: Stocks vs. crypto on separate instances

## Security Architecture

### Authentication
- **Alpaca API**: Secure key-based authentication
- **MCP Protocol**: Client authentication via stdio isolation
- **Environment Variables**: Secure credential storage

### Data Security
- **Local Storage**: File system permissions
- **Network Communication**: HTTPS/WSS for Alpaca
- **Sensitive Data**: No storage of personal/financial data

### Access Control
- **Read-Only**: Server provides read-only market data
- **No Trading**: No order execution capabilities
- **Rate Limiting**: Alpaca API rate limit compliance

## Performance Characteristics

### Latency Requirements
- **Real-time Data**: <1 second from market to client
- **Historical Queries**: <5 seconds for 30-day history
- **Indicator Calculations**: <100ms for standard timeframes

### Throughput Specifications
- **Concurrent Symbols**: 50+ symbols per instance
- **Update Frequency**: 1-minute bar updates
- **Client Connections**: 10+ concurrent MCP clients

### Resource Utilization
- **Memory**: ~100MB base + 10MB per 1000 bars
- **CPU**: Low baseline, spikes during indicator calculation
- **Storage**: ~1MB per symbol per month (compressed)

## Error Handling & Resilience

### Fault Tolerance
- **Connection Failures**: Automatic Alpaca reconnection
- **Data Corruption**: Validation and recovery procedures
- **Service Degradation**: Graceful fallback to cached data

### Error Recovery
- **Stream Interruption**: Resume from last known state
- **Cache Corruption**: Rebuild from historical data
- **API Limits**: Backoff and retry strategies

### Monitoring Points
- **Data Freshness**: Alert on stale data (>5 minutes)
- **Connection Status**: Monitor Alpaca connectivity
- **Error Rates**: Track and alert on error spikes
- **Performance Metrics**: Latency and throughput monitoring

## Integration Points

### External APIs
- **Alpaca Markets**: Primary data source
- **MCP Protocol**: Client integration standard
- **FastAPI**: Alternative HTTP interface

### Data Formats
- **Input**: Alpaca Bar format (OHLCV + timestamp)
- **Storage**: Parquet with standard schema
- **Output**: JSON responses with indicators and signals

### Client Compatibility
- **Claude Desktop**: Primary MCP client
- **IDEs**: VS Code, other MCP-compatible editors
- **Custom Clients**: Any MCP protocol implementation
- **Web Browsers**: FastAPI endpoints for web integration

## Future Architecture Considerations

### Planned Enhancements
- **Multi-broker Support**: Beyond Alpaca Markets
- **Advanced Indicators**: Custom technical analysis
- **Machine Learning**: Pattern recognition and predictions
- **Real-time Alerting**: Push notifications for signals

### Scalability Roadmap
- **Microservices**: Split into specialized services
- **Event Streaming**: Kafka/Redis for real-time events
- **Cloud Native**: Kubernetes deployment
- **Global Distribution**: Multi-region deployment

### Technology Evolution
- **Database Integration**: PostgreSQL/TimescaleDB for historical data
- **Caching Layer**: Redis for high-performance caching
- **API Gateway**: Centralized request routing and management
- **Observability**: Comprehensive logging, metrics, and tracing