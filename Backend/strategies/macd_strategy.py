import backtrader as bt

class MACDStrategy(bt.Strategy):

    params = (
        ("fast", 12),
        ("slow", 26),
        ("signal", 9),
    )

    def __init__(self):

        self.macd = bt.indicators.MACD(
            self.data.close,
            period_me1=self.params.fast,
            period_me2=self.params.slow,
            period_signal=self.params.signal
        )

        self.crossover = bt.ind.CrossOver(
            self.macd.macd,
            self.macd.signal
        )

        self.trade_log = []

    def next(self):

        if not self.position:

            if self.crossover > 0:
                self.buy()

                self.trade_log.append({
                    "action": "BUY",
                    "price": self.data.close[0],
                    "macd": self.macd.macd[0],
                    "signal": self.macd.signal[0]
                })

        else:

            if self.crossover < 0:
                self.sell()

                self.trade_log.append({
                    "action": "SELL",
                    "price": self.data.close[0],
                    "macd": self.macd.macd[0],
                    "signal": self.macd.signal[0]
                })