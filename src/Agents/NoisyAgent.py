from .AgentParent import AgentParent
from decimal import Decimal
import random


class NoisyAgent(AgentParent):

    def __init__(self, name, cash=0.0, quantity=0,tradeProbability=0.5, maxTradeNum=3):

        # Initialising the parent agent 
        AgentParent.__init__(self, name, cash, quantity)
        self.tradeProbability= tradeProbability
        self.maxTradeNum= maxTradeNum

    def step(self, timeStep,price):

        # The agent places a random buy or sell order with 0.5 probability
        if random.random()>self.tradeProbability:
            return

        tradeNum = random.randint(1, self.maxTradeNum)

        # Randomly buying or selling with 0.5 probability
        if random.random()<0.5:

            cost = Decimal(str(price)) * tradeNum

            if self.cash>= cost:
                self.buy(timeStep, price, tradeNum)
        else:
            if self.quantity>= tradeNum:
                self.sell(timeStep,price, tradeNum)

