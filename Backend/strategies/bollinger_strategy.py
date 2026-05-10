import backtrader as bt

class BollingerBandsStrategy(bt.Strategy):

    params = (
        ("period", 20),
        ("devfactor", 2),
    )

    def __init__(self):

        self.bbands = bt.indicators.BollingerBands(
            self.data.close,
            period=self.params.period,
            devfactor=self.params.devfactor
        )

        self.trade_log = []

    def next(self):

        if not self.position:

            # Buy when price touches lower band
            if self.data.close[0] <= self.bbands.lines.bot[0]:
                self.buy()

                self.trade_log.append({
                    "action": "BUY",
                    "price": self.data.close[0],
                    "lower_band": self.bbands.lines.bot[0],
                    "middle_band": self.bbands.lines.mid[0]
                })

        else:

            # Sell when price touches upper band
            if self.data.close[0] >= self.bbands.lines.top[0]:
                self.sell()

                self.trade_log.append({
                    "action": "SELL",
                    "price": self.data.close[0],
                    "upper_band": self.bbands.lines.top[0],
                    "middle_band": self.bbands.lines.mid[0]
                })