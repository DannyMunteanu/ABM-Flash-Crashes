import random
from decimal import Decimal
from typing import Optional

from .LimitOrderBook import LimitOrderBook


class Market:
    """
    Market manages the evolving market price and fundamental value.
    The market updates the fundamental price through a stochastic process
    and determines the current market price based on order book activity.
    """

    def __init__(
            self,
            limitOrderBook: LimitOrderBook,
            initialFundamental: float = 100.0,
            fundamentalVolatility: float = 0.2,
            noiseStandard: float = 0.01,
            initialPrice: Optional[float] = None
    ) -> None:
        """
        Initialises the Market.

        Parameters:
            limitOrderBook: LimitOrderBook used to retrieve market state and trades.
            initialFundamental: Initial fundamental value of the asset.
            fundamentalVolatility: Volatility of the fundamental price process.
            noiseStandard: Standard deviation of noise added to the market price.
            initialPrice: Optional starting market price.
        """
        self._limitOrderBook = limitOrderBook
        self._fundamentalPrice = Decimal(str(initialFundamental))
        self._fundamentalVolatility = fundamentalVolatility
        self._noiseStandard = noiseStandard

        if initialPrice is None:
            self.price = Decimal(str(initialFundamental))
        else:
            self.price = Decimal(str(initialPrice))

        self.priceHistory = [float(self.price)]
        self.fundamentalHistory = [float(self._fundamentalPrice)]

    @property
    def fundamentalPrice(self) -> Decimal:
        """
        Returns the Decimal value of fundamental price.
        """
        return self._fundamentalPrice

    def updateFundamental(self) -> None:
        """
        Updates the fundamental value using a random shock process.
        Ensures the fundamental price remains positive.
        """
        shock = Decimal(str(
            random.gauss(0, self._fundamentalVolatility)
        ))
        self._fundamentalPrice += shock
        if self._fundamentalPrice <= 0:
            self._fundamentalPrice = Decimal("0.01")
        self.fundamentalHistory.append(
            float(self._fundamentalPrice)
        )

    def updatePrice(self, timeTick: int) -> float:
        """
        Updates the observed market price based on recent trades or order book state.
        Adds noise to simulate microstructure variation.

        Parameters:
            timeTick: Current point in time for the simulation.

        Returns the updated market price.
        """
        price: Optional[float] = None
        if self._limitOrderBook.trades:
            price = self._limitOrderBook.trades[-1]["price"]
        if price is None:
            price = self._limitOrderBook.midPrice()
        if price is None:
            bestBid = self._limitOrderBook.bestBid()
            bestAsk = self._limitOrderBook.bestAsk()
            if bestBid is not None and bestAsk is not None:
                price = float((bestBid + bestAsk) / 2)
            elif bestBid is not None:
                price = float(bestBid)
            elif bestAsk is not None:
                price = float(bestAsk)
        if price is None and self.price is not None:
            price = float(self.price)
        if price is None:
            price = float(self._fundamentalPrice)
        price += random.gauss(0, self._noiseStandard)
        if price <= 0:
            price = 0.01
        self.price = Decimal(str(price))
        self.priceHistory.append(price)
        return price
