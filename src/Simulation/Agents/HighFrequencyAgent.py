import random
from .AgentParent import AgentParent
from decimal import Decimal


class HighFrequencyAgent(AgentParent):
    """
    Child of AgentParent, HighFrequencyAgent follows a simple market making strategy.
    Places buy and sell orders limits around the mid-price and sells as inventory nears a set limit.
    The high frequency rate of trading is defined out of scope for HighFrequencyAgent.
    """

    def __init__(
            self,
            name: str,
            cash: float = 0.0,
            quantity: int = 0,
            maxTradeNum: int = 3,
            tradeProbability: float = 1.0,
            inventoryCap: int = 40,
            bufferBeforeReachingCap: int = 4
    ):
        """
        Initialises a HighFrequencyAgent.
        Parameters:
            name: Unique string identifier.
            cash: Starting amount of liquidity.
            quantity: Starting amount of assets held.
            maxTradeNum: Maximum quantity traded in a single order.
            tradeProbability: Probability that the agent trades at a given step.
            inventoryCap: Maximum quantity the agent aims to hold.
            bufferBeforeReachingCap: Threshold before the quantity cap where the agent begins selling.
        """
        AgentParent.__init__(self, name, cash, quantity)
        self._tickSize = Decimal("0.01")
        self._orderIdBid = None
        self._orderIdAsk = None
        self._maxTradeNum = int(maxTradeNum)
        self._tradeProbability = float(tradeProbability)
        self._inventoryCap = int(inventoryCap)
        self._bufferBeforeReachingCap = int(bufferBeforeReachingCap)

    def _cancelQuotes(self, logOrderBook):
        """
        Cancels any active bid or ask orders previously submitted by the agent.
        Parameters:
            logOrderBook: Instance of LimitOrderBook used to cancel orders.
        """
        for attribute in ["_orderIdBid", "_orderIdAsk"]:
            orderId = getattr(self, attribute)
            if orderId is not None:
                logOrderBook.cancelOrder(orderId)
                setattr(self, attribute, None)

    def _shouldTrade(self) -> bool:
        """
        Determines whether the agent trades during the current step.
        Returns True if the agent should trade, otherwise False.
        """
        return random.random() <= self._tradeProbability

    def _needsToSell(self, logOrderBook, timeTick) -> bool:
        """
        Checks whether the agent's inventory is close to the defined cap.
        If the threshold is reached, the agent submits a market sell order to reduce its holdings.
        Returns True if a sell order was submitted, otherwise False.
        Parameters:
            logOrderBook: Instance of LimitOrderBook used to submit orders.
            timeTick: Current point in time for the simulation.
        """
        if self.quantity < self._inventoryCap - self._bufferBeforeReachingCap:
            return False
        tradeNum = random.randint(1, self._maxTradeNum)
        sellSize = min(tradeNum, int(self.quantity))
        if sellSize > 0:
            logOrderBook.submitMarketOrder("sell", sellSize, self, timeTick)
        self._cancelQuotes(logOrderBook)
        return True

    def _calculateBidAsk(self, midPrice):
        """
        Calculates bid and ask prices around the current market mid-price.
        Returns a tuple containing bid and ask prices.
        Parameters:
            midPrice: Current market mid-price.
        """
        bid = midPrice - self._tickSize
        ask = midPrice + self._tickSize
        return bid, ask

    def _calculateSizes(self):
        """
        Determines the quantity of assets to buy and sell.
        The sizes depend on the agent's current quantity and the maximum trade size allowed.
        Returns a tuple containing bid and ask order sizes.
        """
        tradeNum = random.randint(1, self._maxTradeNum)
        bidSize = min(tradeNum, max(0, self._inventoryCap - int(self.quantity)))
        askSize = min(tradeNum, max(0, int(self.quantity)))
        return bidSize, askSize

    def _submitOrders(self, logOrderBook, bid, ask, bidSize, askSize, timeTick):
        """
        Submits limit orders to the order book using the calculated prices and sizes.
        Parameters:
            logOrderBook: Instance of LimitOrderBook used to submit orders.
            bid: Price of the bid order.
            ask: Price of the ask order.
            bidSize: Quantity of the bid order.
            askSize: Quantity of the ask order.
            timeTick: Current point in time for the simulation.
        """
        if bidSize > 0 and self.cash >= bid * Decimal(bidSize):
            self._orderIdBid = logOrderBook.submitLimitOrder(
                "buy", float(bid), bidSize, self, timeTick
            )
        if askSize > 0:
            self._orderIdAsk = logOrderBook.submitLimitOrder(
                "sell", float(ask), askSize, self, timeTick
            )

    def step(self, market, logOrderBook, timeTick):
        """
        Step is called at the current simulation time step, when the HighFrequencyAgent executes its trading strategy.
        Places limit orders around the current market price and adjusts its behaviour based on inventory levels.
        Parameters:
            market: Instance of Market that provides the current market price.
            logOrderBook: Instance of LimitOrderBook used to submit and cancel orders.
            timeTick: Current point in time for the simulation.
        """
        if not self._shouldTrade():
            return
        if market.price is None:
            return
        midPrice = Decimal(str(market.price))
        bestAsk = logOrderBook.bestAsk()
        bestBid = logOrderBook.bestBid()
        if bestAsk is None or bestBid is None:
            return
        if self._needsToSell(logOrderBook, timeTick):
            return
        bid, ask = self._calculateBidAsk(midPrice)
        bidSize, askSize = self._calculateSizes()
        self._cancelQuotes(logOrderBook)
        self._submitOrders(logOrderBook, bid, ask, bidSize, askSize, timeTick)
