import random
from decimal import Decimal
from .AgentParent import AgentParent
from ..Market.LimitOrderBook import LimitOrderBook
from ..Market.Market import Market


class NoisyAgent(AgentParent):
    """
    Child of AgentParent, NoisyAgent executes trades randomly.
    The agent trades buy or sell orders with a fixed probability and random trade sizes.
    This is done without any market signal or strategy.
    """

    def __init__(self, name, cash=0.0, quantity=0, tradeProbability=0.5, maxTradeNum=3):
        """
        Initialises a NoisyAgent.
        Parameters:
            name: Unique string identifier.
            cash: Starting amount of liquidity.
            quantity: Starting amount of assets held.
            tradeProbability: Probability of trading at each step.
            maxTradeNum: Maximum quantity traded in a single order.
        """
        AgentParent.__init__(self, name, cash, quantity)
        self.tradeProbability = tradeProbability
        self.maxTradeNum = maxTradeNum

    def step(self, market: Market, limitOrderBook: LimitOrderBook, timeTick: int):
        """
        Step is called at the current simulation tick, where NoisyAgent may trade randomly.
        Randomly submits a market buy or sell order within 1 and maxTradeNum, limited by cash and inventory.
        Parameters:
            market: Instance of Market providing the current price.
            limitOrderBook: Instance of LimitOrderBook used to submit orders.
            timeTick: Current simulation tick.
        """
        if random.random() > self.tradeProbability or market.price is None:
            return
        tradeNum = random.randint(1, self.maxTradeNum)
        if random.random() < 0.5:
            cost = Decimal(str(market.price)) * Decimal(tradeNum)
            if self.cash >= cost:
                limitOrderBook.submitMarketOrder("buy", tradeNum, self, timeTick)
        else:
            if self.quantity >= tradeNum:
                limitOrderBook.submitMarketOrder("sell", tradeNum, self, timeTick)
