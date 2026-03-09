import random
from decimal import Decimal
from .AgentParent import AgentParent
from ..Market.LimitOrderBook import LimitOrderBook
from ..Market.Market import Market


class FundamentalAgent(AgentParent):
    """
    Child of AgentParent, FundamentalAgent follows a fundamental trading strategy.
    Comparing the current market price with the fundamental price.
    """

    def __init__(self, name: str, cash: float = 0.0, quantity: int = 0, maxTradeSize: int = 5):
        """
        Initialises a FundamentalAgent.
        Parameters:
            name: Unique string identifier.
            cash: Starting amount of liquidity.
            quantity: Starting amount of assets held.
            maxTradeSize: Maximum quantity that can be traded at a given step.
        """
        super().__init__(name, cash, quantity)
        self._maxTradeSize = maxTradeSize

    @property
    def maxTradeSize(self) -> int:
        """
        Getter method returns integer value for maxTradeSize
        """
        return self._maxTradeSize

    def step(self, market: Market, logOrderBook: LimitOrderBook, timeTick):
        """
        Step is called at the current simulation time step, in which this FundamentalAgent executes is strategy.
        If the asset is undervalued it submits a market buy order, else if overvalued it submits a market sell order.
        The frequency at which the agent trades is determined out of scope for FundamentalAgent.

        Parameters:
            market: Instance of Market that contains current and fundamental prices.
            logOrderBook: Instance of LogOrderBook used to submit orders.
            timeTick: Current point in time for the simulation.
        """
        if market.price is None:
            return
        marketPrice = Decimal(str(market.price))
        fundamentalPrice = market.fundamentalPrice
        tradeSize = random.randint(1, self._maxTradeSize)
        if marketPrice < fundamentalPrice and self.cash >= marketPrice * tradeSize:
            logOrderBook.submitMarketOrder("buy", tradeSize, self, timeTick)
        elif marketPrice > fundamentalPrice and self.quantity >= tradeSize:
            logOrderBook.submitMarketOrder("sell", tradeSize, self, timeTick)
