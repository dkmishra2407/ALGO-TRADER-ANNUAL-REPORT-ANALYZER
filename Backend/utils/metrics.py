import numpy as np

def sharpe_ratio(returns, risk_free_rate=0.02):
    """
    Calculate Sharpe ratio
    """
    returns = np.array(returns)

    if len(returns) < 2:
        return 0

    mean = np.mean(returns)
    std = np.std(returns)

    return (mean - risk_free_rate/252) / std * np.sqrt(252) if std > 0 else 0

def max_drawdown(portfolio_values):
    """
    Calculate maximum drawdown
    """
    portfolio_values = np.array(portfolio_values)
    peak = np.maximum.accumulate(portfolio_values)
    drawdown = (portfolio_values - peak) / peak
    return np.min(drawdown)

def total_return(initial_value, final_value):
    """
    Calculate total return
    """
    return (final_value - initial_value) / initial_value

def win_rate(trades):
    """
    Calculate win rate from trade log
    """
    if not trades:
        return 0

    wins = 0
    for i in range(1, len(trades), 2):
        if i+1 < len(trades):
            buy_price = trades[i-1]['price']
            sell_price = trades[i]['price']
            if sell_price > buy_price:
                wins += 1

    total_trades = len(trades) // 2
    return wins / total_trades if total_trades > 0 else 0