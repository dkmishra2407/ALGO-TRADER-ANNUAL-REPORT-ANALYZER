import backtrader as bt
import yfinance as yf
from strategies.sma_strategy import SMAStrategy
from strategies.rsi_strategy import RSIStrategy
from strategies.macd_strategy import MACDStrategy
from strategies.bollinger_strategy import BollingerBandsStrategy
from .custom_strategy_engine import create_custom_strategy, load_custom_strategy_code, list_custom_strategies_from_s3
from utils.metrics import sharpe_ratio, max_drawdown, total_return, win_rate
import importlib
import sys
import os
import numpy as np

STRATEGY_MAP = {
    "sma": SMAStrategy,
    "rsi": RSIStrategy,
    "macd": MACDStrategy,
    "bollinger": BollingerBandsStrategy,
}

_custom_strategies = {}  # Cache for custom strategies

def run_backtest(params):

    data = yf.download(
        params.ticker,
        start=params.start_date,
        end=params.end_date,
        auto_adjust=True
    )

    data.columns = [col[0] if isinstance(col,tuple) else col for col in data.columns]

    cerebro = bt.Cerebro()

    cerebro.broker.setcash(params.cash)

    strategy_class = STRATEGY_MAP.get(params.strategy.lower())
    if not strategy_class:
        # Try to load custom strategy
        strategy_class = load_custom_strategy(params.strategy)

    if not strategy_class:
        raise ValueError(f"Strategy {params.strategy} not found")

    # Use strategy_params if provided, otherwise use defaults
    strategy_kwargs = params.strategy_params or {}

    cerebro.addstrategy(strategy_class, **strategy_kwargs)

    datafeed = bt.feeds.PandasData(dataname=data)

    cerebro.adddata(datafeed)

    result = cerebro.run()

    if getattr(params, 'plot', False):
        try:
            cerebro.plot()
        except Exception as e:
            print(f"Backtest plot failed: {e}")

    final_value = cerebro.broker.getvalue()
    initial_value = params.cash

    strategy = result[0]

    # Calculate additional metrics
    trade_log = strategy.trade_log if hasattr(strategy, 'trade_log') else []

    # Calculate returns (simplified - in real implementation you'd use daily portfolio values)
    returns = []
    if len(trade_log) >= 2:
        for i in range(1, len(trade_log), 2):
            if i < len(trade_log):
                buy_trade = trade_log[i-1]
                sell_trade = trade_log[i]
                if buy_trade['action'] == 'BUY' and sell_trade['action'] == 'SELL':
                    ret = (sell_trade['price'] - buy_trade['price']) / buy_trade['price']
                    returns.append(ret)

    metrics = {
        "sharpe_ratio": sharpe_ratio(returns) if returns else 0,
        "max_drawdown": 0,  # Would need portfolio values over time
        "total_return": total_return(initial_value, final_value),
        "win_rate": win_rate(trade_log),
        "total_trades": len(trade_log) // 2
    }
    
    # if getattr(params, 'plot', False):
    cerebro.plot(style='candlestick')
    return {
        "final_portfolio_value": final_value,
        "trade_log": trade_log,
        "metrics": metrics
    }

def load_custom_strategy(strategy_name):
    """Load a custom strategy from AWS S3 or local directory"""
    if strategy_name in _custom_strategies:
        return _custom_strategies[strategy_name]

    try:
        # First try to load from S3
        strategy_code = load_custom_strategy_code(strategy_name)
        if strategy_code is not None:
            strategy_class = create_custom_strategy(strategy_code, strategy_name)
            _custom_strategies[strategy_name] = strategy_class
            return strategy_class
    except Exception as e:
        print(f"Error loading from S3: {e}")

    # Fallback to local file
    try:
        strategy_file = f"strategies.{strategy_name}_strategy"
        module = importlib.import_module(strategy_file)

        # Find the strategy class (any class that inherits from bt.Strategy)
        strategy_class = None
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if (isinstance(attr, type) and
                issubclass(attr, bt.Strategy) and
                attr != bt.Strategy):
                strategy_class = attr
                break

        if strategy_class is None:
            return None

        _custom_strategies[strategy_name] = strategy_class
        return strategy_class
    except (ImportError, AttributeError):
        return None

def register_custom_strategy(strategy_code: str, strategy_name: str):
    """Register a custom strategy from code"""
    strategy_class = create_custom_strategy(strategy_code, strategy_name)
    _custom_strategies[strategy_name] = strategy_class
    return strategy_class

def get_available_strategies():
    """Get list of available strategies"""
    strategies = list(STRATEGY_MAP.keys())

    # Add custom strategies from cache
    strategies.extend(_custom_strategies.keys())

    # Add custom strategies from S3
    s3_strategies = list_custom_strategies_from_s3()
    for strategy in s3_strategies:
        if strategy not in strategies:
            strategies.append(strategy)

    # Add custom strategies from local directory
    strategies_dir = os.path.join(os.path.dirname(__file__), '..', 'strategies')
    if os.path.exists(strategies_dir):
        for file in os.listdir(strategies_dir):
            if file.endswith('_strategy.py') and file != '__init__.py':
                strategy_name = file.replace('_strategy.py', '')
                if strategy_name not in strategies:
                    strategies.append(strategy_name)

    return strategies