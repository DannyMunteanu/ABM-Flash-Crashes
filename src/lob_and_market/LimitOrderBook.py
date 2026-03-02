from decimal import Decimal
from collections import deque
import pandas as pd

TICK = Decimal("0.01")  # minimum price increment (1 penny)

def toDec(value) -> Decimal:
    # convert any price to Decimal rounded to 2dp — avoids float key collisions
    return Decimal(str(value)).quantize(TICK)

class Order:
    def __init__(self, orderId, seqNum, side, price, size, agent, timeTick):
        self.orderId  = orderId   
        self.seqNum   = seqNum   
        self.side     = side     
        self.price    = price    
        self.size     = size     
        self.agent    = agent    
        self.timeTick = timeTick 

class LimitOrderBook:
    def __init__(self):
        self.bids   = {}  # {Decimal price -> deque[Order]} — buy side, front = oldest
        self.asks   = {}  # {Decimal price -> deque[Order]} — sell side, front = oldest
        self.bidQty = {}  # {Decimal price -> int} — cached total qty per bid level
        self.askQty = {}  # {Decimal price -> int} — cached total qty per ask level
        self.orders = {}  # {orderId -> Order} — registry of all resting orders
        self.trades = []  # list of dicts — record of every executed fill
        self._nextId  = 0 # increments on every new order
        self._seqNum  = 0 # increments on every submission — enforces strict FIFO

    def submitLimitOrder(self, side, price, size, agent, timeTick):
        price = toDec(price)
        order = Order(self._nextId, self._seqNum, side, price, size, agent, timeTick)
        self._nextId += 1
        self._seqNum += 1

        filled = self._match(order, timeTick) # try to match immediately against the opposite side
        remaining = size - filled #this might be wrong
        if remaining > 0:
            order.size = remaining # unfilled portion rests in the book
            book, qtyBook = (self.bids, self.bidQty) if side == "buy" else (self.asks, self.askQty)
            if price not in book:
                book[price]    = deque() # first order at this price level — create new deque and qty entry
                qtyBook[price] = 0
            book[price].append(order)    # append to back — FIFO (oldest at front)
            qtyBook[price] += remaining 
            self.orders[order.orderId] = order
            return order.orderId         # caller can use this to cancel later

        return None  # fully matched on arrival - nothing rests

    def submitMarketOrder(self, side, size, agent, timeTick):
        self._seqNum += 1  # market orders consume a sequence slot but never rest
        book, qtyBook = (self.asks, self.askQty) if side == "buy" else (self.bids, self.bidQty) # buy walks up the ask side; sell walks down the bid side
        startLevels = len(book)
        startQ = sum(qtyBook.values())
        remaining  = size
        totalValue = Decimal("0")
        
       


        bestFn = min if side == "buy" else max  # bestFn - best price function, best ask = lowest; best bid = highest

        while remaining > 0 and book:
            price = bestFn(book.keys())  # best available price on opposite side
            queue = book[price]

            while remaining > 0 and queue:
                resting  = queue[0]                      # oldest order at this level 
                fill     = min(remaining, resting.size)  # fill as much as possible
                self._fill(price, fill, side, resting, agent, timeTick)
                totalValue      += price * fill  # accumulate for avg price calculation
                remaining       -= fill 
                resting.size    -= fill 
                qtyBook[price]  -= fill          

                if resting.size == 0:
                    queue.popleft()                          # remove fully filled order
                    self.orders.pop(resting.orderId, None)   # remove from registry

            if not queue: 
                del book[price]
                del qtyBook[price]


        filled = size - remaining

        if remaining > 0:
            agent1 = getattr(agent, "_name", None) or str(agent)
            print( f"INFO: {agent1} market {side} only filled {filled}/{size} — book exhausted "
            f"(startLevels={startLevels}, startQty={startQ}, endLevels={len(book)})") # book ran out before order was fully filled 

        avgPrice = totalValue / filled if filled > 0 else None
        return avgPrice, filled  # return avg execution price and qty filled

    def cancelOrder(self, orderId):
        if orderId not in self.orders:
            return False  # order not found — already filled or never existed

        order = self.orders.pop(orderId)  # remove from registry
        book, qtyBook = (self.bids, self.bidQty) if order.side == "buy" else (self.asks, self.askQty)
        price = order.price

        if price in book:
            try:
                book[price].remove(order)  # remove from deque
            except ValueError:
                pass  # already consumed by a concurrent fill
            qtyBook[price] -= order.size   
            if not book[price] or qtyBook[price] <= 0:
                # level is now empty — clean up
                del book[price]
                del qtyBook[price]

        return True

    # State queries
    def bestBid(self):
        return max(self.bids.keys()) if self.bids else None  

    def bestAsk(self):
        return min(self.asks.keys()) if self.asks else None  

    def midPrice(self):
        bb, ba = self.bestBid(), self.bestAsk()
        return float((bb + ba) / 2) if bb and ba else None  

    def spread(self):
        bb, ba = self.bestBid(), self.bestAsk()
        return float(ba - bb) if bb and ba else None  

    def depth(self, side, levels=5): #tells the total quantity of orders resting in the book across the top N price levels on one side.
        qtyBook = self.bidQty if side == "buy" else self.askQty
        prices  = sorted(qtyBook.keys(), reverse=(side == "buy"))[:levels]
        return sum(qtyBook[p] for p in prices)

    def tradeHistory(self):
        return pd.DataFrame(self.trades)  # all fills as a DataFrame for analysis

    def _match(self, order, timeTick):
        filled = 0
        book, qtyBook = (self.asks, self.askQty) if order.side == "buy" else (self.bids, self.bidQty)
        bestFn  = min if order.side == "buy" else max
        crossOk = (lambda op, bp: op >= bp) if order.side == "buy" else (lambda op, bp: op <= bp) # crossOk: buy limit matches if bid price >= best ask; sell if ask price <= best bid

        while order.size > filled and book:
            best = bestFn(book.keys())
            if not crossOk(order.price, best):
                break  # price doesn't cross — order rests without matching

            queue = book[best] #fetches the list of orders sitting at the best available price, ready to be matched against the incoming order.
            while order.size > filled and queue:
                resting  = queue[0]  # oldest order at this level (FIFO)
                fill     = min(order.size - filled, resting.size)
                self._fill(best, fill, order.side, resting, order.agent, timeTick)
                filled          += fill
                resting.size    -= fill
                qtyBook[best]   -= fill  

                if resting.size == 0:
                    queue.popleft()
                    self.orders.pop(resting.orderId, None)

            if not queue:
                del book[best]      # level empty — remove entirely
                del qtyBook[best]

        return filled

    def _fill(self, price, size, aggressor, passive, activeAgent, timeTick):
        priceF = float(price)
        if aggressor == "buy":
            activeAgent.buy(timeTick, priceF, size)   
            passive.agent.sell(timeTick, priceF, size) 
        else:
            activeAgent.sell(timeTick, priceF, size)  
            passive.agent.buy(timeTick, priceF, size)  

        self.trades.append({
            "timeTick":  timeTick,
            "price":     priceF,
            "size":      size,
            "aggressor": aggressor,                    
            "seqNum":    passive.seqNum,               
            "buyer":     getattr(activeAgent if aggressor == "buy" else passive.agent, "_name", None),
            "seller":    getattr(activeAgent if aggressor == "sell" else passive.agent, "_name", None),
        })