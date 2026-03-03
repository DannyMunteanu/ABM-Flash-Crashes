from .AgentParent import AgentParent
from decimal import Decimal
import random


class HFTAgent(AgentParent):

    def __init__(self, name, cash=0.0, quantity=0, maxTradeNum=3, tradeProbability=1.0,
                 inventoryCap=40, bufferBeforeReachingCap=4):

        AgentParent.__init__(self, name, cash, quantity)
        self.tickSize = Decimal("0.01")
        self._orderIdBid = None
        self._orderIdAsk = None
        self.maxTradeNum = int(maxTradeNum)
        self.tradeProbability = float(tradeProbability)
        self.inventoryCap = int(inventoryCap)
        self.bufferBeforeReachingCap = int(bufferBeforeReachingCap)

    def _cancelQuotes(self, lob):
        for attribute in ["_orderIdBid", "_orderIdAsk"]:
            orderId = getattr(self, attribute)
            if orderId is not None:
                lob.cancelOrder(orderId)
                setattr(self, attribute, None)

    def step(self, market, lob, timeTick):

        if random.random() > self.tradeProbability:
            return

        bestAsk = lob.bestAsk()
        bestBid = lob.bestBid()

        if bestAsk is None or bestBid is None:
            return

        tradeNum = random.randint(1, self.maxTradeNum)

        if self.quantity >= self.inventoryCap - self.bufferBeforeReachingCap:
            sellSize = min(tradeNum, int(self.quantity))
            if sellSize > 0:
                lob.submitMarketOrder("sell", sellSize, self, timeTick)
            self._cancelQuotes(lob)
            return

        bid = Decimal(str(bestBid)) + self.tickSize
        ask = Decimal(str(bestAsk)) - self.tickSize

        if bid >= ask:
            bid = Decimal(str(bestBid))
            ask = Decimal(str(bestAsk))

        bidSize = min(tradeNum, max(0, self.inventoryCap - int(self.quantity)))
        askSize = min(tradeNum, max(0, int(self.quantity)))

        self._cancelQuotes(lob)

        if bidSize > 0 and self.cash >= bid * Decimal(bidSize):
            self._orderIdBid = lob.submitLimitOrder("buy", float(bid), bidSize, self, timeTick)

        if askSize > 0:
            self._orderIdAsk = lob.submitLimitOrder("sell", float(ask), askSize, self, timeTick)