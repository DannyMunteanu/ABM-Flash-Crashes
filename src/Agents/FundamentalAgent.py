from .AgentParent import AgentParent
from decimal import Decimal
import random
class FundamentalAgent(AgentParent):

    def __init__(self, name, cash=0.0, quantity=0, maxTradeSize=5):
        super().__init__(name, cash, quantity)
        self.maxTradeSize = maxTradeSize


    def step(self, market, lob, timeTick):

        #sanity check
        if market.price is None:
            return

        marketPrice = Decimal(str(market.price))
        fundamentalPrice = market.fundamentalPrice

        # Random trade size
        tradeSize = random.randint(1, self.maxTradeSize)


        mispricingThreshold = Decimal("0.5")  # try 0.5 or even 1.0

        if marketPrice < fundamentalPrice - mispricingThreshold:

            cost = marketPrice * tradeSize

            if self.cash >= cost:

                lob.submitMarketOrder(
                    "buy",
                    tradeSize,
                    self,
                    timeTick
                )


        # SELL if overvalued
        elif marketPrice > fundamentalPrice + mispricingThreshold:

            if self.quantity >= tradeSize:

                lob.submitMarketOrder(
                    "sell",
                    tradeSize,
                    self,
                    timeTick
                )