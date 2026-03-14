from decimal import Decimal
from typing import Optional
import random
from .AgentParent import AgentParent
from ..Market.LimitOrderBook import LimitOrderBook
from ..Market.Market import Market


class StopLossAgent(AgentParent):
    """
    Child of AgentParent, StopLossAgent executes trades using stop-loss and take-profit levels.
    Takes positions up to a maximum size and exits if price hits the stop-loss or take-profit limits.
    After a stop-loss exit, the agent will not re-enter until either price recovers above the exit
    price by at least the stop-loss threshold, or the stopTriggeredTimeout has elapsed, preventing
    cascade selling during prolonged downturns while ensuring agents eventually re-enter the market.
    """
    def __init__(
            self,
            name: str,
            cash: float = 10_000.0,
            quantity: int = 0,
            stopLossPct: float = 0.03,
            takeProfitPct: float = 0.05,
            tradeSize: int = 5,
            maxPosition: int = 50,
            cooldownTicks: int = 10,
            initialEntryPrice: Optional[float] = None,
            stopTriggeredTimeout: int = 100,
    ):
        """
        Initialises a StopLossAgent.
        Parameters:
            name: Unique string identifier.
            cash: Starting amount of liquidity.
            quantity: Starting amount of assets held.
            stopLossPct: Loss threshold relative to entry price to trigger exit.
            takeProfitPct: Gain threshold relative to entry price to trigger exit.
            tradeSize: Number of units traded per order.
            maxPosition: Maximum absolute position allowed.
            cooldownTicks: Minimum number of ticks between trades.
            initialEntryPrice: Entry price for any initial holdings. Required if quantity > 0.
            stopTriggeredTimeout: Number of ticks after a stop-loss exit before the agent is
                                  allowed to re-enter regardless of price recovery.
        """
        super().__init__(name, cash, quantity)
        self._stopLossPercentage = Decimal(str(stopLossPct))
        self._takeProfitPercentage = Decimal(str(takeProfitPct))
        self._tradeSize = int(tradeSize)
        self._maxPosition = int(maxPosition)
        self._cooldownTicks = int(cooldownTicks)
        self._entryPrice: Decimal | None = Decimal(str(initialEntryPrice)) if quantity > 0 and initialEntryPrice is not None else None
        self._lastTradeTick: int = -999
        self._stopTriggered: bool = False
        self._stopExitPrice: Optional[Decimal] = None
        self._stopTriggeredTimeout: int = int(stopTriggeredTimeout)

    def _tryEnter(self, currentPrice: Decimal, limitOrderBook: LimitOrderBook, timeTick: int) -> bool:
        """
        Attempts to enter a buy position.
        Checks position limits, available cash, and submits a market order if possible.
        Will not enter if a stop-loss was recently triggered and neither the price recovery
        threshold nor the stop triggered timeout has been reached.
        Updates entry price and last trade tick if trade is filled.
        Returns True if a trade was filled, otherwise False.
        Parameters:
            currentPrice: Current market price.
            limitOrderBook: Instance of LimitOrderBook used to submit orders.
            timeTick: Current simulation tick.
        """
        if self._stopTriggered:
            priceRecovered = (
                self._stopExitPrice is not None
                and currentPrice > self._stopExitPrice * (Decimal("1") + self._stopLossPercentage)
            )
            timeoutReached = (timeTick - self._lastTradeTick) > self._stopTriggeredTimeout
            if priceRecovered or timeoutReached:
                self._stopTriggered = False
                self._stopExitPrice = None
            else:
                return False
        if self._quantity >= self._maxPosition:
            return False
        bestAsk = limitOrderBook.bestAsk()
        if bestAsk is None:
            return False
        size = min(self._tradeSize, self._maxPosition - self._quantity)
        if size <= 0:
            return False
        if self._cash < bestAsk * size:
            size = int(self._cash / bestAsk)
            if size <= 0:
                return False
        averagePrice, filled = limitOrderBook.submitMarketOrder("buy", size, self, timeTick)
        if filled > 0:
            self._entryPrice = Decimal(str(averagePrice))
            self._lastTradeTick = timeTick
            return True
        return False

    def _tryExit(self, currentPrice: Decimal, limitOrderBook: LimitOrderBook, timeTick: int) -> bool:
        """
        Attempts to exit a position based on stop-loss or take-profit levels.
        Sets the stop triggered flag if exit was caused by stop-loss to prevent immediate re-entry.
        Returns True if a trade was filled, otherwise False.
        Parameters:
            currentPrice: Current market price.
            limitOrderBook: Instance of LimitOrderBook used to submit orders.
            timeTick: Current simulation tick.
        """
        if self._quantity <= 0 or self._entryPrice is None:
            return False
        stopLevel = self._entryPrice * (Decimal("1") - self._stopLossPercentage)
        targetLevel = self._entryPrice * (Decimal("1") + self._takeProfitPercentage)
        if currentPrice <= stopLevel or currentPrice >= targetLevel:
            size = min(self._tradeSize, self._quantity)
            avgPrice, filled = limitOrderBook.submitMarketOrder("sell", size, self, timeTick)
            if filled > 0:
                if currentPrice <= stopLevel:
                    self._stopTriggered = True
                    self._stopExitPrice = currentPrice
                self._entryPrice = None
                self._lastTradeTick = timeTick
                return True
        return False

    def step(self, market: Market, limitOrderBook: LimitOrderBook, timeTick: int) -> None:
        """
        Step is called at the current simulation tick, where the agent may exit or enter trades.
        Checks cooldown and price, applies stop-loss and take-profit rules, and enters new positions if allowed.
        An entry is not attempted in the same tick as an exit.
        Parameters:
            market: Instance of Market providing current price.
            limitOrderBook: Instance of LimitOrderBook for order execution.
            timeTick: Current simulation tick.
        """
        if market.price is None:
            return
        currentPrice = Decimal(str(market.price))
        if timeTick - self._lastTradeTick < self._cooldownTicks:
            return
        exited = self._tryExit(currentPrice, limitOrderBook, timeTick)
        if not exited:
            self._tryEnter(currentPrice, limitOrderBook, timeTick)