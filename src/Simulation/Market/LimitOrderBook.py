import pandas as pd
from decimal import Decimal
from collections import deque
from sortedcontainers import SortedList
from typing import Optional, Tuple, Dict, List
from ..Agents.AgentParent import AgentParent
from .Order import Order


class LimitOrderBook:
    """
    LimitOrderBook manages bid and ask limit orders and matches trades between agents.
    Orders are stored by price level using price-time priority.
    The book records trades, supports market and limit orders, and provides market state queries.
    """
    def __init__(self):
        """
        Initialises an empty LimitOrderBook.
        Sets up storage for bid and ask orders, quantities at each price level,
        order tracking, and trade history.
        """
        self._bids = {}
        self._asks = {}
        self._bidQuantity = {}
        self._askQuantity = {}
        self._orders = {}
        self._trades = []
        self._nextId = 0
        self._sequenceNumber = 0
        self._sortedBidPrices = SortedList(key=lambda x: -x)
        self._sortedAskPrices = SortedList()

    @property
    def bids(self) -> Dict[Decimal, deque]:
        """
        Returns the dictionary of bid price levels and their order queues.
        """
        return self._bids

    @property
    def asks(self) -> Dict[Decimal, deque]:
        """
        Returns the dictionary of ask price levels and their order queues.
        """
        return self._asks

    @property
    def bidQuantity(self) -> Dict[Decimal, int]:
        """
        Returns the total bid quantity available at each price level.
        """
        return self._bidQuantity

    @property
    def askQuantity(self) -> Dict[Decimal, int]:
        """
        Returns the total ask quantity available at each price level.
        """
        return self._askQuantity

    @property
    def trades(self) -> List[dict]:
        """
        Returns the list of completed trades recorded by the order book.
        """
        return self._trades

    @property
    def sortedBidPrices(self) -> SortedList:
        """
        Returns the sorted list of bid prices in descending order.
        """
        return self._sortedBidPrices

    @property
    def sortedAskPrices(self) -> SortedList:
        """
        Returns the sorted list of ask prices in ascending order.
        """
        return self._sortedAskPrices

    def submitLimitOrder(
            self,
            side: str,
            price: Decimal,
            size: int,
            agent: "AgentParent",
            timeTick: int
    ) -> Optional[int]:
        """
        Submits a limit order to the order book.
        The order attempts to match against existing orders before resting on the book.
        Returns the order ID if the order rests on the book, otherwise None if fully filled.
        Parameters:
            side: Order direction either buy or sell.
            price: Limit price for the order.
            size: Quantity of assets in the order.
            agent: Agent submitting the order.
            timeTick: Current point in time for the simulation.
        """
        price = Decimal(str(price)).quantize(Decimal("0.01"))
        order = Order(self._nextId, self._sequenceNumber, side, price, size, agent, timeTick)
        self._nextId += 1
        self._sequenceNumber += 1
        filled = self._match(order, timeTick)
        remaining = size - filled
        if remaining > 0:
            order.size = remaining
            if side == "buy":
                book, quantityBook, sortedPrices = self._bids, self._bidQuantity, self._sortedBidPrices
            else:
                book, quantityBook, sortedPrices = self._asks, self._askQuantity, self._sortedAskPrices
            if price not in book:
                book[price] = deque()
                sortedPrices.add(price)
            book[price].append(order)
            quantityBook[price] = quantityBook.get(price, 0) + remaining
            self._orders[order.orderId] = order
            return order.orderId
        return None

    def submitMarketOrder(
            self,
            side: str,
            size: int,
            agent: AgentParent,
            timeTick: int
    ) -> Tuple[Optional[Decimal], int]:
        """
        Submits a market order that immediately executes against the best available prices.
        Returns the average execution price and the total quantity filled.
        Parameters:
            side: Order direction either buy or sell.
            size: Quantity to trade.
            agent: Agent submitting the order.
            timeTick: Current point in time for the simulation.
        """
        self._sequenceNumber += 1
        if side == "buy":
            book, quantityBook, sortedPrices = self._asks, self._askQuantity, self._sortedAskPrices
        else:
            book, quantityBook, sortedPrices = self._bids, self._bidQuantity, self._sortedBidPrices
        remaining = size
        totalValue = Decimal("0")
        while remaining > 0 and sortedPrices:
            price = sortedPrices[0]
            queue = book[price]
            while remaining > 0 and queue:
                resting = queue[0]
                fill = min(remaining, resting.size)
                self._fill(price, fill, side, resting, agent, timeTick)
                totalValue += price * fill
                remaining -= fill
                resting.size -= fill
                quantityBook[price] -= fill
                if resting.size == 0:
                    queue.popleft()
                    self._orders.pop(resting.orderId, None)
            if not queue:
                del book[price]
                del quantityBook[price]
                sortedPrices.remove(price)
        filled = size - remaining
        if remaining > 0:
            agentName = getattr(agent, "_name", None) or str(agent)
            startLevels = len(book) + (size - remaining)
            print(f"INFO: {agentName} market {side} only filled {filled}/{size} — book exhausted "
                  f"(endLevels={len(book)})")
        averagePrice = totalValue / filled if filled > 0 else None
        return averagePrice, filled

    def cancelOrder(self, orderId: int) -> bool:
        """
        Cancels an existing limit order from the order book.
        Returns True if the order was successfully cancelled, otherwise False.
        Parameters:
            orderId: Unique identifier of the order to cancel.
        """
        if orderId not in self._orders:
            return False
        order = self._orders.pop(orderId)
        if order.side == "buy":
            book, quantityBook, sortedPrices = self._bids, self._bidQuantity, self._sortedBidPrices
        else:
            book, quantityBook, sortedPrices = self._asks, self._askQuantity, self._sortedAskPrices
        price = order.price
        if price in book:
            try:
                book[price].remove(order)
            except ValueError:
                pass
            quantityBook[price] -= order.size
            if not book[price] or quantityBook[price] <= 0:
                del book[price]
                del quantityBook[price]
                sortedPrices.remove(price)
        return True

    def bestBid(self) -> Optional[Decimal]:
        """
        Returns the highest bid price currently in the order book.
        """
        return self._sortedBidPrices[0] if self._sortedBidPrices else None

    def bestAsk(self) -> Optional[Decimal]:
        """
        Returns the lowest ask price currently in the order book.
        """
        return self._sortedAskPrices[0] if self._sortedAskPrices else None

    def midPrice(self) -> Optional[float]:
        """
        Returns the mid-price between the best bid and best ask.
        """
        bestBid = self.bestBid()
        bestAsk = self.bestAsk()
        return (bestBid + bestAsk) / 2 if bestBid is not None and bestAsk is not None else None

    def spread(self) -> Optional[float]:
        """
        Returns the bid-ask spread.
        """
        bestBid = self.bestBid()
        bestAsk = self.bestAsk()
        return bestAsk - bestBid if bestBid is not None and bestAsk is not None else None

    def depth(self, side: str, levels: int = 5) -> int:
        """
        Calculates the total quantity available across the top price levels.
        Returns the total quantity available across the specified depth.
        Parameters:
            side: Side of the book either buy or sell.
            levels: Number of price levels to include.
        """
        if side == "buy":
            sortedPrices = self._sortedBidPrices
            quantityBook = self._bidQuantity
        else:
            sortedPrices = self._sortedAskPrices
            quantityBook = self._askQuantity
        return sum(quantityBook[p] for p in sortedPrices[:levels])

    def tradeHistory(self) -> pd.DataFrame:
        """
        Returns the DataFrame containing recorded trade history.
        """
        return pd.DataFrame(self._trades)

    def _match(self, order: Order, timeTick: int) -> int:
        """
        Attempts to match a limit order against the opposing side of the order book.
        Returns the total quantity filled.
        Parameters:
            order: Order attempting to match.
            timeTick: Current point in time for the simulation.
        """
        filled = 0
        if order.side == "buy":
            book, quantityBook, sortedPrices = self._asks, self._askQuantity, self._sortedAskPrices
            crossOk = lambda bookPrice: order.price >= bookPrice
        else:
            book, quantityBook, sortedPrices = self._bids, self._bidQuantity, self._sortedBidPrices
            crossOk = lambda bookPrice: order.price <= bookPrice
        while order.size > filled and sortedPrices:
            best = sortedPrices[0]
            if not crossOk(best):
                break
            queue = book[best]
            while order.size > filled and queue:
                resting = queue[0]
                fill = min(order.size - filled, resting.size)
                self._fill(best, fill, order.side, resting, order.agent, timeTick)
                filled += fill
                resting.size -= fill
                quantityBook[best] -= fill
                if resting.size == 0:
                    queue.popleft()
                    self._orders.pop(resting.orderId, None)
            if not queue:
                del book[best]
                del quantityBook[best]
                sortedPrices.remove(best)
        return filled

    def _fill(
            self,
            price: Decimal,
            size: int,
            aggressor: str,
            passive: Order,
            activeAgent: AgentParent,
            timeTick: int):
        """
        Executes a trade between two agents and records the transaction.
        Parameters:
            price: Execution price of the trade.
            size: Quantity traded.
            aggressor: Side initiating the trade either buy or sell.
            passive: Resting order in the book.
            activeAgent: Agent submitting the aggressive order.
            timeTick: Current point in time for the simulation.
        """
        floatPrice = float(price)
        if aggressor == "buy":
            activeAgent.buy(timeTick, floatPrice, size)
            passive.agent.sell(timeTick, floatPrice, size)
        else:
            activeAgent.sell(timeTick, floatPrice, size)
            passive.agent.buy(timeTick, floatPrice, size)

        self._trades.append({
            "timeTick": timeTick,
            "price": floatPrice,
            "size": size,
            "aggressor": aggressor,
            "sequenceNumber": passive.sequenceNumber,
            "buyer": getattr(activeAgent if aggressor == "buy" else passive.agent, "_name", None),
            "seller": getattr(activeAgent if aggressor == "sell" else passive.agent, "_name", None),
        })