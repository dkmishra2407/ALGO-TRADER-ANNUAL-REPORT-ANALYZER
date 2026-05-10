import backtrader as bt

class MyCustomStrategyStrategy(bt.Strategy):
    params = (
        ('threshold', 0.01),
    )
    
    def __init__(self):
        self.trade_log = []
    
    def next(self):
        if not self.position:
            if self.data.close[0] > self.data.open[0] * (1 + self.params.threshold):
                self.buy()
                self.trade_log.append({
                    'action': 'BUY',
                    'price': self.data.close[0]
                })
        elif self.position:
            if self.data.close[0] < self.data.open[0] * (1 - self.params.threshold):
                self.sell()
                self.trade_log.append({
                    'action': 'SELL',
                    'price': self.data.close[0]
                })