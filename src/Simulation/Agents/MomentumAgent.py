from decimal import Decimal
from .AgentParent import AgentParent
from ..Market.LimitOrderBook import LimitOrderBook
from ..Market.Market import Market


class MomentumAgent(AgentParent):
    """
    Child of AgentParent, MomentumAgent trades based on price momentum.
    Calculates short and long-term averages to signal trades when their gap exceeds a threshold.
    Trades follow position, size, and cooldown limits.
    """

    def __init__(
            self,
            name: str,
            cash: float = 10_000.0,
            quantity: int = 0,
            shortWindow: int = 5,
            longWindow: int = 20,
            tradeSize: int = 1,
            maxPosition: int = 50,
            momentumThreshold: float = 0.002,
            cooldownTicks: int = 3,
    ):
        """
        Initialises a MomentumAgent.
        Parameters:
            name: Unique string identifier.
            cash: Starting amount of liquidity.
            quantity: Starting amount of assets held.
            shortWindow: Window size for the short-term moving average.
            longWindow: Window size for the long-term moving average.
            tradeSize: Number of units traded per order.
            maxPosition: Maximum absolute position allowed.
            momentumThreshold: Relative difference between averages required to trigger a trade.
            cooldownTicks: Minimum number of ticks between trades.
        """
        super().__init__(name, cash, quantity)
        self.shortWindow = int(shortWindow)
        self.longWindow = int(longWindow)
        self.tradeSize = int(tradeSize)
        self.maxPosition = int(maxPosition)
        self.momentumThreshold = Decimal(str(momentumThreshold))
        self.cooldownTicks = int(cooldownTicks)
        self._prices: list = []
        self._lastTradeTick: int = -999

    def _rollingMean(self, window: int):
        """
        Calculates the moving average over the specified window.
        Returns a moving average as Decimal, or None if insufficient history.
        Parameters:
            window: Number of most recent prices to include.
        """
        if len(self._prices) < window:
            return None
        return sum(self._prices[-window:]) / Decimal(window)

    def _signal(self):
        """
        Determines trading signal based on momentum.
        Compares short-term and long-term moving averages.
        Returns buy string signal if positive momentum, sell signal if negative, otherwise None.
        """
        shortMovingAverage = self._rollingMean(self.shortWindow)
        longMovingAverage = self._rollingMean(self.longWindow)
        if shortMovingAverage is None or longMovingAverage is None:
            return None
        diff = (shortMovingAverage - longMovingAverage) / longMovingAverage
        if diff > self.momentumThreshold:
            return "buy"
        if diff < -self.momentumThreshold:
            return "sell"
        return None

    def _updatePriceHistory(self, currentPrice: Decimal) -> None:
        """
        Adds the current price to the history and maintains the longWindow.
        """
        self._prices.append(currentPrice)
        if len(self._prices) > self.longWindow:
            self._prices.pop(0)

    def _canTrade(self, timeTick: int) -> bool:
        """
        Checks whether cooldown period has passed since the last trade.
        """
        return timeTick - self._lastTradeTick >= self.cooldownTicks

    def _getSignal(self) -> str | None:
        """
        Determines the trading signal from _signal() and validates it.
        """
        signal = self._signal()
        return signal if signal in ("buy", "sell") else None

    def _computeTradeSize(self, signal: str) -> int:
        """
        Computes the allowed trade size based on signal and current position.
        Returns the adjusted trade size. The size is 0 if position limits are reached.
        """
        if signal == "buy":
            return min(self.tradeSize, self.maxPosition - self._quantity)
        else:
            return min(self.tradeSize, self._quantity)

    def _computeAffordableSize(self, limitOrderBook: LimitOrderBook, size: int) -> int:
        """
        Returns the largest quantity the agent can afford to buy at the current best ask.
        Returns 0 if there is no ask or the agent has insufficient cash.
        """
        bestAsk = limitOrderBook.bestAsk()
        if bestAsk is None:
            return 0
        bestAsk = Decimal(str(bestAsk))
        if self._cash < bestAsk * size:
            size = int(Decimal(str(self._cash)) / bestAsk)
        return size

    def _executeTrade(self, signal: str, size: int, limitOrderBook: LimitOrderBook, timeTick: int) -> None:
        """
        Submits a market order and updates the last trade tick.
        """
        averagePrice, filled = limitOrderBook.submitMarketOrder(signal, size, self, timeTick)
        if filled > 0:
            self._lastTradeTick = timeTick

    def step(self, market: Market, limitOrderBook: LimitOrderBook, timeTick: int) -> None:
        """
        Step is called at the current simulation time step, when the MomentumAgent executes its trading strategy.
        Updates price history, evaluates limits and signals, adjusts size, and submits an order.
        """
        if market.price is None:
            return
        currentPrice = Decimal(str(market.price))
        self._updatePriceHistory(currentPrice)
        if not self._canTrade(timeTick):
            return
        signal = self._getSignal()
        if not signal:
            return
        size = self._computeTradeSize(signal)
        if size <= 0:
            return
        if signal == "buy":
            size = self._computeAffordableSize(limitOrderBook, size)
            if size <= 0:
                return
        self._executeTrade(signal, size, limitOrderBook, timeTick)
