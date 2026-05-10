import backtrader as bt

class SMAStrategy(bt.Strategy):

    params = (
        ("fast",10),
        ("slow",30),
    )

    def __init__(self):

        self.sma_fast = bt.indicators.SMA(
            self.data.close,
            period=self.params.fast
        )

        self.sma_slow = bt.indicators.SMA(
            self.data.close,
            period=self.params.slow
        )

        self.crossover = bt.ind.CrossOver(
            self.sma_fast,
            self.sma_slow
        )

        self.trade_log = []

    def next(self):

        if not self.position:

            if self.crossover > 0:
                self.buy()

                self.trade_log.append({
                    "action":"BUY",
                    "price":self.data.close[0]
                })

        else:

            if self.crossover < 0:
                self.sell()

                self.trade_log.append({
                    "action":"SELL",
                    "price":self.data.close[0]
                })