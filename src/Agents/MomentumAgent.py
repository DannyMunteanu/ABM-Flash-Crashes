from .AgentParent import AgentParent
from decimal import Decimal


class MomentumAgent(AgentParent):
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
        if len(self._prices) < window:
            return None
        return sum(self._prices[-window:]) / Decimal(window)

    def _signal(self):
        shortMA = self._rollingMean(self.shortWindow)
        longMA = self._rollingMean(self.longWindow)

        if shortMA is None or longMA is None:
            return None

        diff = (shortMA - longMA) / longMA

        if diff > self.momentumThreshold:
            return "buy"
        if diff < -self.momentumThreshold:
            return "sell"
        return None

    def step(self, market, lob, timeTick: int) -> None:
        if market.price is None:
            return

        currentP = Decimal(str(market.price))

        self._prices.append(currentP)
        if len(self._prices) > self.longWindow:
            self._prices.pop(0)

        if timeTick - self._lastTradeTick < self.cooldownTicks:
            return

        signal = self._signal()
        if signal is None:
            return

        if signal == "buy" and self._quantity >= self.maxPosition:
            return
        if signal == "sell" and self._quantity <= -self.maxPosition:
            return

        size = self.tradeSize
        if signal == "buy":
            size = min(size, self.maxPosition - self._quantity)
        else:
            size = min(size, self.maxPosition + self._quantity)

        if size <= 0:
            return

        if signal == "buy":
            bestAsk = lob.bestAsk()
            if bestAsk is None:
                return
            if self._cash < bestAsk * size:
                size = int(self._cash / bestAsk)
                if size <= 0:
                    return

        avgPrice, filled = lob.submitMarketOrder(signal, size, self, timeTick)

        if filled > 0:
            self._lastTradeTick = timeTick
