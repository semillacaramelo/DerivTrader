# Technical Documentation

## API Integration

### DerivAPIConnection Class
The core API interface that handles WebSocket connections to Deriv.com.

#### Key Methods:
- `connect()`: Establishes WebSocket connection and authenticates
- `subscribe()`: Sets up data subscriptions with callbacks
- `send_request()`: Sends API requests and handles responses
- `disconnect()`: Gracefully closes connections
- `test_connection()`: Comprehensive connection testing
- `switch_account()`: Switch between demo and real accounts
- `get_token_diagnostic()`: Token validation and diagnostics

### Error Handling
- Connection errors trigger automatic reconnection attempts
- API errors are logged and propagated appropriately
- Simulation mode provides safe testing environment
- Comprehensive token validation and diagnostics

## Environment Configuration

### Required Variables:
```bash
# API Configuration
DERIV_APP_ID=your_app_id                # Your Deriv App ID
DERIV_API_TOKEN_DEMO=your_demo_token    # Demo account token
DERIV_API_TOKEN_REAL=your_real_token    # Real account token

# Account Settings
DEFAULT_ACCOUNT_TYPE=demo               # 'demo' or 'real'
ENABLE_SIMULATION=false                 # Test mode without real API

# Trading Parameters
TRADING_SYMBOL=R_100                    # Symbol to trade
STAKE_AMOUNT=10.0                       # Base stake amount
MAX_CONCURRENT_TRADES=1                 # Max simultaneous trades

# Strategy Parameters
SHORT_MA_PERIOD=5                       # Short moving average period
MEDIUM_MA_PERIOD=10                     # Medium moving average period
LONG_MA_PERIOD=20                       # Long moving average period
SIGNAL_THRESHOLD=0.5                    # Signal strength threshold

# Risk Management
MAX_DAILY_LOSS=100.0                   # Daily loss limit
MAX_DAILY_TRADES=50                     # Maximum trades per day

# Logging 
LOG_LEVEL=INFO                         # Logging verbosity
LOG_FILE=deriv_bot.log                 # Log file location
```

## Moving Average Strategy

### MovingAverageStrategy Class
Implements the 3 MA trading strategy.

#### Signal Generation:
```python
Buy Signal:  short_MA > medium_MA > long_MA
Sell Signal: short_MA < medium_MA < long_MA
```

#### Signal Strength:
Calculated as: `min(abs(short_MA - long_MA) / long_MA, 1.0)`

### Performance Considerations
- Moving averages are computed using numpy for efficiency
- Price data is stored in memory efficiently
- Signal generation optimized for real-time processing

## Trading System

### DerivTrader Class
Manages trade execution and monitoring.

#### Features:
- Real-time price monitoring via WebSocket
- Automatic signal processing
- Risk management enforcement
- Position tracking and P&L calculation
- Daily statistics tracking
- Account balance management

#### Risk Management:
- Daily loss limits
- Maximum trade counts
- Concurrent trade restrictions
- Signal strength filtering
- Dynamic stake sizing

## API Details

### WebSocket Connection
```python
# Primary endpoint
wss://ws.derivapi.com/websockets/v3

# Backup endpoints
wss://ws.binaryws.com/websockets/v3
```

### Common Requests
```json
// Tick subscription
{
    "ticks": "R_100",
    "subscribe": 1
}

// Contract proposal
{
    "proposal": 1,
    "amount": 10,
    "basis": "stake",
    "contract_type": "CALL",
    "currency": "USD",
    "duration": 1,
    "duration_unit": "m",
    "symbol": "R_100"
}
```

## Development Guidelines

### Testing
The project includes comprehensive test suites:
- Unit tests for strategy (`tests/test_strategy.py`)
- Integration tests for trader (`tests/test_trader.py`)
- API connection tests (`test_api_connection.py`)

### Running Tests
```bash
# Run unit tests
pytest tests/

# Test API connection
python test_api_connection.py

# Run with simulation
ENABLE_SIMULATION=true python __main__.py
```

### Code Style
- Follow PEP 8
- Use type hints
- Document public methods
- Include unit tests
- Handle errors gracefully

## Troubleshooting

### Common Issues
1. Connection Failures
   - Validate API tokens using `get_token_diagnostic()`
   - Check network connectivity
   - Verify endpoint availability

2. Authentication Errors
   - Ensure token format matches Deriv's requirements (15 chars)
   - Verify token permissions
   - Check account status

3. Trading Issues
   - Confirm sufficient balance
   - Check market availability
   - Verify trade parameters
   - Review risk management limits

### Logging
- Rolling log files with 1MB size limit
- Backup logs maintained
- Configurable verbosity via LOG_LEVEL
- Separate loggers for different components

## Future Enhancements

### Planned Features
1. Additional Strategies
   - Multiple timeframe analysis
   - Technical indicator combinations
   - Machine learning integration

2. Enhanced Risk Management
   - Dynamic position sizing
   - Advanced drawdown protection
   - Risk-adjusted stake calculation

3. System Improvements
   - Performance optimization
   - Extended backtesting capabilities
   - Market analysis tools