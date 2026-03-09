import random
from decimal import Decimal
from typing import Optional
from .AgentParent import AgentParent
from ..Market.LimitOrderBook import LimitOrderBook
from ..Market.Market import Market


class MarketMakerAgent(AgentParent):
    """
    Child of AgentParent, MarketMakerAgent follows a market making strategy.
    Continuously places bid and ask limit orders around the market price while adjusting quotes based on inventory.
    MarketMakerAgent may temporarily withdraw from the market during periods of price decline and low order book depth.
    """
    def __init__(
            self,
            name: str,
            cash: float = 0.0,
            quantity: int = 0,
            spread: float = 0.4,
            maxTradeNum: int = 2,
            inventoryAim: int = 0,
            inventoryCoefficient: float = 0.001,
            inventoryCap: int = 500,
            movingWindowForPrices: int = 45,
            withdrawTicks: int = 20,
            durationForWithdrawal: int = 40,
            withdrawCooldownTicks: int = 100,
            withdrawalMinDepth: int = 5,
            inventoryPressureTicks: int = 5,
            checkDepth: int = 10
    ) -> None:
        """
        Initialises a MarketMakerAgent.
        Parameters:
            name: Unique string identifier.
            cash: Starting amount of liquidity.
            quantity: Starting amount of assets held.
            spread: Base spread placed around the current price.
            maxTradeNum: Maximum quantity traded in a single order.
            inventoryAim: Target inventory level for the agent.
            inventoryCoefficient: Strength of inventory adjustment applied to quotes.
            inventoryCap: Maximum inventory the agent may hold.
            movingWindowForPrices: Number of recent prices stored for withdrawal checks.
            withdrawTicks: Price drop threshold used to trigger withdrawal.
            durationForWithdrawal: Number of ticks the agent remains withdrawn.
            withdrawCooldownTicks: Minimum time between withdrawal events.
            withdrawalMinDepth: Minimum order book depth required to remain active.
            inventoryPressureTicks: Price adjustment applied when inventory approaches limits.
            checkDepth: Number of order book levels checked for liquidity.
        """
        super().__init__(name, cash, quantity)
        self.spread: Decimal = Decimal(str(spread))
        self.maxTradeNum: int = maxTradeNum
        self.tickSize: Decimal = Decimal("0.01")
        self.inventoryAim: int = inventoryAim
        self.inventoryCoefficient: Decimal = Decimal(str(inventoryCoefficient))
        self.inventoryCap: int = inventoryCap
        self.inventoryPressureTicks: int = inventoryPressureTicks
        self.movingWindowForPrices: int = movingWindowForPrices
        self.withdrawTicks: int = withdrawTicks
        self.durationForWithdrawal: int = durationForWithdrawal
        self.withdrawCooldownTicks: int = withdrawCooldownTicks
        self.withdrawalMinDepth: int = withdrawalMinDepth
        self.checkDepth: int = checkDepth
        self._orderIdBid: Optional[int] = None
        self._orderIdAsk: Optional[int] = None
        self._prevBid: Optional[Decimal] = None
        self._prevAsk: Optional[Decimal] = None
        self._pricesList: list[Decimal] = []
        self.withdrawTill: int = -1
        self._nextWithdraw: int = 0
        self.flag: bool = False

    def _cancelQuotes(self, limitOrderBook: LimitOrderBook) -> None:
        """
        Cancels any active bid or ask orders previously submitted by the MarketMakerAgent.
        Parameters:
            limitOrderBook: Instance of LimitOrderBook used to cancel orders.
        """
        for attr in ["_orderIdBid", "_orderIdAsk"]:
            orderId = getattr(self, attr)
            if orderId is not None:
                limitOrderBook.cancelOrder(orderId)
                setattr(self, attr, None)

    def _priceRounder(self, price: Decimal) -> Decimal:
        """
        Rounds a price to the nearest valid tick size.
        Returns a rounded price that aligns with the market tick size.
        Parameters:
            price: Price to be rounded.
        """
        return (price / self.tickSize).quantize(Decimal("1")) * self.tickSize

    def _withdrawOrDont(self, currentPrice: Decimal, limitOrderBook: LimitOrderBook, timeTick: int) -> bool:
        """
        Determines whether the agent temporarily withdraws from the market.
        Withdraws when price drops below a recent average threshold and order book depth is sufficient.
        Returns True if the agent withdraws from quoting, otherwise False.
        Parameters:
           currentPrice: Current market price.
           limitOrderBook: Instance of LimitOrderBook used to check depth and cancel orders.
           timeTick: Current point in time for the simulation.
        """
        if timeTick < self.withdrawTill:
            if not self.flag:
                self._cancelQuotes(limitOrderBook)
                self.flag = True
            return True
        self.flag = False
        if len(self._pricesList) != self.movingWindowForPrices or timeTick < self._nextWithdraw:
            return False
        averagePrice = sum(self._pricesList) / Decimal(self.movingWindowForPrices)
        threshold = averagePrice - Decimal(self.withdrawTicks) * self.tickSize
        if currentPrice >= threshold:
            return False
        if limitOrderBook.depth("buy", levels=self.checkDepth) < self.withdrawalMinDepth \
                or limitOrderBook.depth("sell", levels=self.checkDepth) < self.withdrawalMinDepth:
            return False
        self._cancelQuotes(limitOrderBook)
        self.withdrawTill = timeTick + self.durationForWithdrawal
        self._nextWithdraw = timeTick + self.withdrawCooldownTicks
        self.flag = True
        return True

    def _computeBidAsk(self, currentPrice: Decimal) -> tuple[Decimal, Decimal]:
        """
        Calculates bid and ask prices around the current market price.
        Quotes are adjusted based on the agent's inventory to encourage movement towards the target inventory level.
        Returns a tuple containing bid and ask prices.
        Parameters:
            currentPrice: Current market price.
        """
        bid = currentPrice - self.spread / Decimal("2")
        ask = currentPrice + self.spread / Decimal("2")
        inventoryErr = Decimal(self.quantity - self.inventoryAim)
        bid -= self.inventoryCoefficient * inventoryErr
        ask += self.inventoryCoefficient * inventoryErr
        if self.quantity >= self.inventoryCap - 1:
            bid -= self.tickSize * Decimal(self.inventoryPressureTicks)
        if self.quantity <= 1:
            ask += self.tickSize * Decimal(self.inventoryPressureTicks)
        bid = max(self._priceRounder(bid), self.tickSize)
        ask = max(self._priceRounder(ask), bid + self.tickSize)
        return bid, ask

    def _computeOrderSizes(self) -> tuple[int, int]:
        """
        Determines the sizes of buy and sell orders.
        Order sizes are random but constrained by the inventory limits and maximum trade size.
        Returns a tuple containing buy and sell order sizes.
        """
        buySize = random.randint(1, self.maxTradeNum)
        sellSize = random.randint(1, self.maxTradeNum)
        buySize = min(buySize, max(0, self.inventoryCap - self.quantity))
        sellSize = min(sellSize, max(0, int(self.quantity)))
        return buySize, sellSize

    def _submitOrders(
            self,
            limitOrderBook: LimitOrderBook,
            bid: Decimal,
            ask: Decimal,
            buySize: int,
            sellSize: int,
            timeTick: int
    ) -> None:
        """
        Submits bid and ask limit orders to the order book.
        Existing orders are replaced if new quotes are submitted.
        Parameters:
            limitOrderBook: Instance of LimitOrderBook used to submit orders.
            bid: Price of the bid order.
            ask: Price of the ask order.
            buySize: Quantity of the buy order.
            sellSize: Quantity of the sell order.
            timeTick: Current point in time for the simulation.
        """
        oldBidId = self._orderIdBid
        oldAskId = self._orderIdAsk
        orderIdBidNew: Optional[int] = None
        orderIdAskNew: Optional[int] = None
        if buySize > 0 and self.cash >= bid * Decimal(buySize):
            orderIdBidNew = limitOrderBook.submitLimitOrder("buy", float(bid), buySize, self, timeTick)
        if sellSize > 0:
            orderIdAskNew = limitOrderBook.submitLimitOrder("sell", float(ask), sellSize, self, timeTick)
        if orderIdBidNew and oldBidId and oldBidId != orderIdBidNew:
            limitOrderBook.cancelOrder(oldBidId)
        if orderIdAskNew and oldAskId and oldAskId != orderIdAskNew:
            limitOrderBook.cancelOrder(oldAskId)
        self._orderIdBid = orderIdBidNew or oldBidId
        self._orderIdAsk = orderIdAskNew or oldAskId

    def step(self, market: Market, limitOrderBook: LimitOrderBook, timeTick: int) -> None:
        """
        Step is called at the current simulation time step, in which this MarketMakerAgent executes its strategy.
        Updates its price window, decides on withdrawal, or submits bid and ask orders at the current market price.
        Parameters:
            market: Instance of Market that provides the current market price.
            limitOrderBook: Instance of LimitOrderBook used to submit and cancel orders.
            timeTick: Current point in time for the simulation.
        """
        if market.price is None:
            return
        currentPrice: Decimal = Decimal(str(market.price))
        self._pricesList.append(currentPrice)
        if len(self._pricesList) > self.movingWindowForPrices:
            self._pricesList.pop(0)
        if self._withdrawOrDont(currentPrice, limitOrderBook, timeTick):
            return
        bid, ask = self._computeBidAsk(currentPrice)
        if (self._prevBid == bid and self._prevAsk == ask) and (self._orderIdBid or self._orderIdAsk):
            return
        self._prevBid = bid
        self._prevAsk = ask
        buySize, sellSize = self._computeOrderSizes()
        self._cancelQuotes(limitOrderBook)
        self._submitOrders(limitOrderBook, bid, ask, buySize, sellSize, timeTick)
