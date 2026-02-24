from .AgentParent import AgentParent
from decimal import Decimal
import random


class HFTAgent(AgentParent):

    def __init__(self, name, cash=0.0, quantity=0, mispriceThreshold=0.05, maxTradeNum=3, tradeProbability=1.0):

        AgentParent.__init__(self, name, cash, quantity)
        self.mispriceThreshold = Decimal(str(mispriceThreshold))
        self.maxTradeNum = maxTradeNum
        self.tradeProbability = tradeProbability

    def step(self, market, lob, timeTick):

        if random.random() > self.tradeProbability:
            return

        bestAsk = lob.bestAsk()
        bestBid = lob.bestBid()

        if bestAsk is None and bestBid is None:
            return

        fundamental = Decimal(str(market.fundamentalPrice))

        tradeNum = random.randint(1, self.maxTradeNum)

        # Buy if ask is "too cheap" relative to fundamental
        if bestAsk is not None:
            ask = Decimal(str(bestAsk))
            if ask < fundamental - self.mispriceThreshold:
                cost = ask * Decimal(tradeNum)
                if self.cash >= cost:
                    lob.submitMarketOrder("buy", tradeNum, self, timeTick)
                    return

        # Sell if bid is "too expensive" relative to fundamental
        if bestBid is not None:
            bid = Decimal(str(bestBid))
            if bid > fundamental + self.mispriceThreshold:
                if self.quantity >= tradeNum:
                    lob.submitMarketOrder("sell", tradeNum, self, timeTick)
                    return