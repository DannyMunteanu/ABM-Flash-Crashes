from .AgentParent import AgentParent
from decimal import Decimal
import random
class FundamentalAgent(AgentParent):

    def __init__(self, name, cash=0.0, quantity=0, maxTradeSize=5):
        super().__init__(name, cash, quantity)
        self.maxTradeSize = maxTradeSize


    def step(self, market, lob, timeTick):

        # Require valid prices
        if market.price is None:
            return

        marketPrice = Decimal(str(market.price))
        fundamentalPrice = market.fundamentalPrice

        # Random trade size
        tradeSize = random.randint(1, self.maxTradeSize)


        # BUY if undervalued
        if marketPrice < fundamentalPrice:

            cost = marketPrice * tradeSize

            if self.cash >= cost:

                lob.submitMarketOrder(
                    "buy",
                    tradeSize,
                    self,
                    timeTick
                )


        # SELL if overvalued
        elif marketPrice > fundamentalPrice:

            if self.quantity >= tradeSize:

                lob.submitMarketOrder(
                    "sell",
                    tradeSize,
                    self,
                    timeTick
                )