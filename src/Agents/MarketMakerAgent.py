from .AgentParent import AgentParent
from decimal import Decimal
import random


class MarketMakerAgent(AgentParent):

    def __init__(self, name, cash=0.0, quantity=0, spread=0.4, maxTradeNum=2,inventoryAim=0, inventoryCoefficient=0.001, inventoryCap=500):

        # Initialising the parent agent
        AgentParent.__init__(self, name, cash, quantity)

        self.spread = Decimal(str(spread))
        self.maxTradeNum = maxTradeNum
        self._orderIdBid =None
        self._orderIdAsk = None
        self.inventoryAim = inventoryAim
        self.inventoryCoefficient = Decimal(str(inventoryCoefficient))
        self.inventoryCap = int(inventoryCap)

    def step(self, market, lob, timeTick):

        # If the market price is not available the agent does nothing
        if market.price is None:
            return

        # Existing quotes are cancelled prior to submitting new ones
        for attribute in ["_orderIdBid", "_orderIdAsk"]:

            orderId = getattr(self,attribute)

            if orderId is not None:
                lob.cancelOrder(orderId)
                setattr(self, attribute,None)

        # Calculating bid/ask in relation to the market price
        bid, ask = (Decimal(str(market.price)) -self.spread / Decimal("2"),
        Decimal(str(market.price))+ self.spread / Decimal("2"))

        # Taking inventory into consideration
        inventoryError = Decimal(self.quantity- self.inventoryAim)
   
        bid -= self.inventoryCoefficient * inventoryError
        ask += self.inventoryCoefficient * inventoryError

        # I ensure that the bids/asks are valid
        bid = max(bid, Decimal("0.01"))
        ask = max(ask, bid + Decimal("0.01"))


        bidSize = random.randint(1, self.maxTradeNum)
        askSize = random.randint(1, self.maxTradeNum)

        cappedBuySize = max(0,self.inventoryCap - self.quantity)
        bidSize = min(bidSize, cappedBuySize)

        # Submitting bid quotes
        if bidSize > 0 and self.cash >= bid * Decimal(bidSize):
            self._orderIdBid = lob.submitLimitOrder("buy",float(bid), bidSize, self, timeTick)

        # Submitting ask quotes
        if self.quantity >= askSize:
            self._orderIdAsk = lob.submitLimitOrder("sell", float(ask), askSize, self, timeTick)
