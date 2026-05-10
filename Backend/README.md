# Algo Trading Backtest API

A comprehensive FastAPI-based algorithmic trading backtesting platform using Backtrader.

## Features

- **Multiple Built-in Strategies**: SMA, RSI, MACD, Bollinger Bands
- **Custom Strategy Creation**: Create and save your own trading strategies
- **Performance Metrics**: Sharpe ratio, max drawdown, total return, win rate
- **RESTful API**: Complete API for strategy management and backtesting
- **Persistent Storage**: Custom strategies are saved to files
- **Flexible Parameters**: Configurable strategy parameters

## Available Strategies

### Built-in Strategies

1. **SMA (Simple Moving Average)** - Crossover strategy
   - Parameters: `fast` (default: 10), `slow` (default: 30)

2. **RSI (Relative Strength Index)** - Oversold/overbought strategy
   - Parameters: `rsi_period` (default: 14), `overbought` (default: 70), `oversold` (default: 30)

3. **MACD (Moving Average Convergence Divergence)** - MACD crossover strategy
   - Parameters: `fast` (default: 12), `slow` (default: 26), `signal` (default: 9)

4. **Bollinger Bands** - Mean reversion strategy
   - Parameters: `period` (default: 20), `devfactor` (default: 2)

### Custom Strategies

Create your own strategies using Python code. Strategies are automatically saved and persist across server restarts.

## API Endpoints

### GET /
Returns API information.

**Response:**
```json
{
  "message": "Algo Trading Backtest API"
}
```

### GET /strategies
Returns list of all available strategies (built-in + custom).

**Response:**
```json
{
  "strategies": ["sma", "rsi", "macd", "bollinger", "my_custom_strategy"]
}
```

### POST /run_backtest
Run a backtest with any available strategy.

**Request Body:**
```json
{
  "ticker": "AAPL",
  "start_date": "2020-01-01",
  "end_date": "2023-01-01",
  "strategy": "sma",
  "cash": 100000,
  "strategy_params": {
    "fast": 10,
    "slow": 30
  }
}
```

**Response:**
```json
{
  "final_portfolio_value": 125000.0,
  "trade_log": [
    {"action": "BUY", "price": 150.0},
    {"action": "SELL", "price": 160.0}
  ],
  "metrics": {
    "sharpe_ratio": 1.23,
    "max_drawdown": -0.15,
    "total_return": 0.25,
    "win_rate": 0.6,
    "total_trades": 15
  }
}
```

### POST /custom_strategy
Create and save a custom trading strategy.

**Request Body:**
```json
{
  "name": "my_custom_strategy",
  "code": "import backtrader as bt\n\nclass MyStrategy(bt.Strategy):\n    params = (('threshold', 0.01),)\n    \n    def __init__(self):\n        self.trade_log = []\n    \n    def next(self):\n        if not self.position and self.data.close[0] > self.data.open[0] * (1 + self.params.threshold):\n            self.buy()\n            self.trade_log.append({'action': 'BUY', 'price': self.data.close[0]})\n        elif self.position and self.data.close[0] < self.data.open[0] * (1 - self.params.threshold):\n            self.sell()\n            self.trade_log.append({'action': 'SELL', 'price': self.data.close[0]})"
}
```

**Response:**
```json
{
  "message": "Custom strategy 'my_custom_strategy' created successfully",
  "strategy_name": "my_custom_strategy"
}
```

### POST /run_custom_backtest
Run backtest with custom strategy code (one-off, not saved).

**Request Body:**
```json
{
  "ticker": "GOOGL",
  "start_date": "2021-01-01",
  "end_date": "2022-01-01",
  "strategy": "temp_strategy",
  "cash": 50000,
  "strategy_params": {
    "code": "import backtrader as bt\n\nclass TempStrategy(bt.Strategy):\n    def __init__(self):\n        self.trade_log = []\n    def next(self):\n        # strategy logic here\n        pass"
  }
}
```
}
```

## Installation & Setup

### Prerequisites
- Python 3.8+
- pip

### Install Dependencies
```bash
pip install -r requirements.txt
```

Or install individually:
```bash
pip install fastapi uvicorn backtrader yfinance numpy pydantic
```

### Run the API
```bash
# Development mode with auto-reload
python -m uvicorn main:app --reload

# Production mode
python -m uvicorn main:app --host 0.0.0.0 --port 8000

# Access the API documentation at: http://127.0.0.1:8000/docs
```

## Custom Strategy Format

### Requirements
Custom strategies must:
1. **Inherit from `bt.Strategy`**: Your class must extend `backtrader.Strategy`
2. **Include `trade_log` attribute**: A list to record buy/sell actions
3. **Implement `next()` method**: Contains your trading logic

### Important Notes
- **Class names are flexible**: Any class name that inherits from `bt.Strategy` will work
- **Strategies are persistent**: Created strategies are saved to files and persist across restarts
- **Parameters are optional**: Use `params` tuple for configurable parameters

### Example Custom Strategy
```python
import backtrader as bt

class MyAwesomeStrategy(bt.Strategy):  # Any class name works!
    params = (
        ('fast_period', 10),
        ('slow_period', 30),
    )

    def __init__(self):
        # Initialize indicators
        self.fast_sma = bt.indicators.SMA(self.data.close, period=self.params.fast_period)
        self.slow_sma = bt.indicators.SMA(self.data.close, period=self.params.slow_period)

        # Required: trade log for recording transactions
        self.trade_log = []

    def next(self):
        # Trading logic
        if not self.position and self.fast_sma[0] > self.slow_sma[0]:
            self.buy()
            self.trade_log.append({
                "action": "BUY",
                "price": self.data.close[0],
                "fast_sma": self.fast_sma[0],
                "slow_sma": self.slow_sma[0]
            })
        elif self.position and self.fast_sma[0] < self.slow_sma[0]:
            self.sell()
            self.trade_log.append({
                "action": "SELL",
                "price": self.data.close[0],
                "fast_sma": self.fast_sma[0],
                "slow_sma": self.slow_sma[0]
            })
```

## Testing with Postman

### 1. Start the Server
```bash
python -m uvicorn main:app --reload
```

### 2. Test Endpoints

#### Check API Health
- **Method**: GET
- **URL**: `http://127.0.0.1:8000/`

#### List Available Strategies
- **Method**: GET
- **URL**: `http://127.0.0.1:8000/strategies`

#### Run Backtest with Built-in Strategy
- **Method**: POST
- **URL**: `http://127.0.0.1:8000/run_backtest`
- **Body**:
```json
{
  "ticker": "AAPL",
  "start_date": "2020-01-01",
  "end_date": "2023-01-01",
  "strategy": "sma",
  "cash": 100000,
  "strategy_params": {
    "fast": 10,
    "slow": 30
  }
}
```

#### Create Custom Strategy
- **Method**: POST
- **URL**: `http://127.0.0.1:8000/custom_strategy`
- **Body**:
```json
{
  "name": "my_custom_strategy",
  "code": "import backtrader as bt\n\nclass MyStrategy(bt.Strategy):\n    def __init__(self):\n        self.trade_log = []\n    \n    def next(self):\n        if not self.position and self.data.close[0] > self.data.open[0]:\n            self.buy()\n            self.trade_log.append({'action': 'BUY', 'price': self.data.close[0]})\n        elif self.position and self.data.close[0] < self.data.open[0]:\n            self.sell()\n            self.trade_log.append({'action': 'SELL', 'price': self.data.close[0]})"
}
```

#### Run Backtest with Custom Strategy
- **Method**: POST
- **URL**: `http://127.0.0.1:8000/run_backtest`
- **Body**:
```json
{
  "ticker": "GOOGL",
  "start_date": "2021-01-01",
  "end_date": "2022-01-01",
  "strategy": "my_custom_strategy",
  "cash": 50000
}
```

## Performance Metrics

The API calculates comprehensive performance metrics:

- **Sharpe Ratio**: Risk-adjusted return measure
- **Maximum Drawdown**: Largest peak-to-trough decline
- **Total Return**: Overall portfolio performance
- **Win Rate**: Percentage of profitable trades
- **Total Trades**: Number of buy/sell transactions

## Error Handling

The API provides clear error messages for common issues:

- **400 Bad Request**: Invalid strategy name, missing parameters, or strategy creation errors
- **422 Validation Error**: Invalid JSON format or missing required fields

## Project Structure

```
algo trader/
├── main.py                 # FastAPI application
├── requirements.txt        # Python dependencies
├── README.md              # This documentation
├── models/
│   └── request_models.py  # Pydantic models for API requests
├── engine/
│   ├── backtest_engine.py     # Core backtesting logic
│   └── custom_strategy_engine.py  # Custom strategy handling
├── strategies/            # Trading strategies
│   ├── __init__.py
│   ├── sma_strategy.py
│   ├── rsi_strategy.py
│   ├── macd_strategy.py
│   ├── bollinger_strategy.py
│   └── *_strategy.py      # Custom strategies (auto-generated)
└── utils/
    └── metrics.py         # Performance calculation utilities
```

## Contributing

1. Create custom strategies in the `strategies/` directory
2. Follow the naming convention: `{strategy_name}_strategy.py`
3. Ensure strategies inherit from `bt.Strategy`
4. Include comprehensive trade logging

## License

This project is open-source. Feel free to use and modify as needed.