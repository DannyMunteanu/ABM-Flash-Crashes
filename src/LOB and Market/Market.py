from decimal import Decimal
import random

class Market:
    def __init__(
        self,
        lob,
        initialFundamental=100.0,
        fundamentalVol=0.02,
        noiseStd=0.01,
        initialPrice=None   
    ):
        # limit order book reference
        self.lob = lob

        # True asset value
        self.fundamentalPrice = Decimal(str(initialFundamental))

        # how fast fundamental moves
        self.fundamentalVol = fundamentalVol

        # microstructure noise
        self.noiseStd = noiseStd

        # Set initial market price
        if initialPrice is None:
            # default: start at fundamental value
            self.price = Decimal(str(initialFundamental))
        else:
            self.price = Decimal(str(initialPrice))

        # history
        self.priceHistory = [float(self.price)]
        self.fundamentalHistory = [float(self.fundamentalPrice)]

    def updateFundamental(self):

        shock = Decimal(str(
            random.gauss(0, self.fundamentalVol)
        ))

        self.fundamentalPrice += shock

        if self.fundamentalPrice <= 0:
            self.fundamentalPrice = Decimal("0.01")

        self.fundamentalHistory.append(
            float(self.fundamentalPrice)
        )
    def updatePrice(self, timeTick):

        price = None

        # 1. Last trade price (most informative)
        if self.lob.trades:
            price = self.lob.trades[-1]["price"]

        # 2. Mid price (standard estimator)
        if price is None:
            price = self.lob.midPrice()

        # 3. Best bid / ask fallback
        if price is None:

            bestBid = self.lob.bestBid()
            bestAsk = self.lob.bestAsk()

            if bestBid is not None and bestAsk is not None:
                price = float((bestBid + bestAsk) / 2)
            elif bestBid is not None:
                price = float(bestBid)
            elif bestAsk is not None:
                price = float(bestAsk)

        # 4. NEW: fall back to previous known price
        if price is None and self.price is not None:
            price = float(self.price)

        # 5. FINAL safety fallback: fundamental value
        if price is None:
            price = float(self.fundamentalPrice)

        # 6. Add microstructure noise
        price += random.gauss(0, self.noiseStd)

        # 7. Prevent negative price
        if price <= 0:
            price = 0.01

        # 8. Save price
        self.price = Decimal(str(price))
        self.priceHistory.append(price)

        return price