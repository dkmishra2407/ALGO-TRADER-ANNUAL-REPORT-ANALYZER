import backtrader as bt

class RSIStrategy(bt.Strategy):

    params = (
        ("rsi_period", 14),
        ("overbought", 70),
        ("oversold", 30),
    )

    def __init__(self):

        self.rsi = bt.indicators.RSI(
            self.data.close,
            period=self.params.rsi_period
        )

        self.trade_log = []

    def next(self):

        if not self.position:

            if self.rsi < self.params.oversold:
                self.buy()

                self.trade_log.append({
                    "action": "BUY",
                    "price": self.data.close[0],
                    "rsi": self.rsi[0]
                })

        else:

            if self.rsi > self.params.overbought:
                self.sell()

                self.trade_log.append({
                    "action": "SELL",
                    "price": self.data.close[0],
                    "rsi": self.rsi[0]
                })