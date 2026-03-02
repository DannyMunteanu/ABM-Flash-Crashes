from .AgentParent import AgentParent
from decimal import Decimal


class StopLossAgent(AgentParent):

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
    ):
        super().__init__(name, cash, quantity)

        self.stopLossPct    = Decimal(str(stopLossPct))
        self.takeProfitPct  = Decimal(str(takeProfitPct))
        self.tradeSize      = int(tradeSize)
        self.maxPosition    = int(maxPosition)
        self.cooldownTicks  = int(cooldownTicks)

        self._entryPrice: Decimal | None = Decimal(str(100)) if quantity > 0 else None
        self._lastTradeTick: int         = -999

    def _tryEnter(self, lob, timeTick: int) -> None:
        if self._quantity >= self.maxPosition:
            return

        bestAsk = lob.bestAsk()
        if bestAsk is None:
            return

        size = min(self.tradeSize, self.maxPosition)
        if size <= 0:
            return

        if self._cash < bestAsk * size:
            size = int(self._cash / bestAsk)
            if size <= 0:
                return

        avgPrice, filled = lob.submitMarketOrder("buy", size, self, timeTick)

        if filled > 0:
            self._entryPrice    = Decimal(str(avgPrice))
            self._lastTradeTick = timeTick

    def _tryExit(self, currentP: Decimal, lob, timeTick: int) -> None:
        if self._quantity <= 0 or self._entryPrice is None:
            return

        stopLevel   = self._entryPrice * (Decimal("1") - self.stopLossPct)
        targetLevel = self._entryPrice * (Decimal("1") + self.takeProfitPct)

        if currentP <= stopLevel or currentP >= targetLevel:
            size = min(self._quantity, self.maxPosition)
            avgPrice, filled = lob.submitMarketOrder("sell", size, self, timeTick)

            if filled > 0:
                self._entryPrice    = None
                self._lastTradeTick = timeTick

    def step(self, market, lob, timeTick: int) -> None:
        if market.price is None:
            return

        currentP = Decimal(str(market.price))

        if timeTick - self._lastTradeTick < self.cooldownTicks:
            return

        self._tryExit(currentP, lob, timeTick)
        self._tryEnter(lob, timeTick)