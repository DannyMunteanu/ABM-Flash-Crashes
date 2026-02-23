from .AgentParent import AgentParent
from decimal import Decimal
import random


class NoisyAgent(AgentParent):

    def __init__(self, name, cash=0.0, quantity=0,tradeProbability=0.5, maxTradeNum=3):

        # Initialising the parent agent 
        AgentParent.__init__(self, name, cash, quantity)
        
        self.tradeProbability= tradeProbability
        self.maxTradeNum= maxTradeNum

    def step(self, market, lob, timeTick):

        # The agent places a random buy or sell order with 0.5 probability
        if random.random() > self.tradeProbability or market.price is None:

            return
        
        tradeNum = random.randint(1, self.maxTradeNum)

        # Randomly buying or selling with 0.5 probability
        if random.random()<0.5:

            cost = Decimal(str(market.price)) * Decimal(tradeNum)

            if self.cash>= cost:

                lob.submitMarketOrder("buy", tradeNum, self, timeTick)
        else:
            if self.quantity>= tradeNum:

                lob.submitMarketOrder("sell", tradeNum, self, timeTick)

