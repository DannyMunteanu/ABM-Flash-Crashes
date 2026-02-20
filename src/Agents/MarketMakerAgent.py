from .AgentParent import AgentParent
from decimal import Decimal
import random


class MarketMakerAgent(AgentParent):

    def __init__(self, name, cash=0.0,quantity=0, spread=0.4, maxTradeNum=2):

        # Initialising the parent agent
        AgentParent.__init__(self, name, cash, quantity)
        self.spread= Decimal(str(spread))
        self.maxTradeNum = maxTradeNum

    def step(self, timeStep, price):

        # Computing quotes
        bid, ask = (Decimal(str(price)) - self.spread / Decimal("4"),
        Decimal(str(price)) + self.spread / Decimal("4"))

        tradeNum = random.randint(1, self.maxTradeNum)

        # This will be removed once the market is implemented it's just a placeholder
        if random.random() < 0.5:
            cost = bid * Decimal(tradeNum)

            if self.cash >= cost:
                self.buy(timeStep, float(bid), tradeNum)

        else:
            if self.quantity>= tradeNum:
                self.sell(timeStep, float(ask), tradeNum)
