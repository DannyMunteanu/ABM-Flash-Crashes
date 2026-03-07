from .AgentParent import AgentParent
from decimal import Decimal
import random


class MarketMakerAgent(AgentParent):

    def __init__(self,name,cash=0.0,quantity=0,spread=0.4,maxTradeNum=2,inventoryAim=0,
        inventoryCoefficient=0.001, inventoryCap=500,movingWindowForPrices=45,
        withdrawTicks=20,durationForWithdrawal=40,withdrawCooldownTicks=100,
        withdrawalMinDepth= 5,inventoryPressureTicks=5,checkDepth=10):

        AgentParent.__init__(self, name, cash, quantity)

        self.spread = Decimal(str(spread))
        self.maxTradeNum = int(maxTradeNum)
        self.tickSize = Decimal("0.01")
        self.inventoryAim= int(inventoryAim)
        self.inventoryCoefficient = Decimal(str(inventoryCoefficient))
        self.inventoryCap = int(inventoryCap)
        self.inventoryPressureTicks = int(inventoryPressureTicks)
        self._orderIdBid =None
        self._orderIdAsk = None
        self.withdrawTill = -1
        self._nextWithdraw = 0
        self.flag = False
        self._prevBid= None
        self._prevAsk = None
        self._pricesList = []
        self.movingWindowForPrices = int(movingWindowForPrices)
        self.withdrawTicks= int(withdrawTicks)
        self.durationForWithdrawal = int(durationForWithdrawal)
        self.withdrawCooldownTicks = int(withdrawCooldownTicks)
        self.withdrawalMinDepth= int(withdrawalMinDepth)
        self.checkDepth = int(checkDepth)
     

    def _cancelQuotes(self, lob):
        for attribute in ["_orderIdBid", "_orderIdAsk"]:
            orderId = getattr(self, attribute)
            if orderId is not None:
                lob.cancelOrder(orderId)
                setattr(self, attribute, None)

    def _priceRounder(self, p1):
        return (p1 / self.tickSize).quantize(Decimal("1"))*self.tickSize

    def _withdrawOrDont(self, currentPrice, lob, timeTick):
    
        if timeTick <self.withdrawTill:
            if not self.flag:
                self._cancelQuotes(lob)
                self.flag = True

            return True
        
        self.flag = False
        
        if len(self._pricesList)!= self.movingWindowForPrices:
            return False
        
        if timeTick< self._nextWithdraw:
            return False
        
        threshold1 = sum(self._pricesList)/Decimal(self.movingWindowForPrices)- Decimal(self.withdrawTicks) * self.tickSize        
        if currentPrice>= threshold1:
            return False
        
        if lob.depth("buy", levels=self.checkDepth) < self.withdrawalMinDepth or lob.depth("sell", levels=self.checkDepth) < self.withdrawalMinDepth:
            return False

        self._cancelQuotes(lob)
        self.withdrawTill = timeTick+self.durationForWithdrawal
        self._nextWithdraw = timeTick+ self.withdrawCooldownTicks
        self.flag = True
        return True

    def step(self, market, lob, timeTick):
        if market.price is None:
            return

        currentPrice = Decimal(str(market.price))

        self._pricesList.append(currentPrice)
        if len(self._pricesList)> self.movingWindowForPrices:
            self._pricesList.pop(0)

        if self._withdrawOrDont(currentPrice, lob, timeTick):
            return

        bid = currentPrice-self.spread/Decimal("2")
        ask = currentPrice+self.spread/ Decimal("2")

        inventoryErr = Decimal(self.quantity - self.inventoryAim)

        bid -= self.inventoryCoefficient * inventoryErr
        ask += self.inventoryCoefficient * inventoryErr
   
        if self.quantity >= self.inventoryCap - 1:
            bid -= self.tickSize * Decimal(self.inventoryPressureTicks)

        if self.quantity <= 1:
            ask += self.tickSize * Decimal(self.inventoryPressureTicks)

        bid = max(self._priceRounder(bid), self.tickSize)
        ask = max(self._priceRounder(ask), bid + self.tickSize)

        if (self._prevBid == bid and self._prevAsk== ask) and (self._orderIdBid is not None or self._orderIdAsk is not None):        
            return

        self._prevBid=bid
        self._prevAsk=ask

        buyS = random.randint(1, self.maxTradeNum)
        sellS = random.randint(1, self.maxTradeNum)

        buyS = min(buyS, max(0, self.inventoryCap - self.quantity))
        sellS = min(sellS, max(0, int(self.quantity)))

        oldBidId=self._orderIdBid
        oldAskId=self._orderIdAsk
        orderIDBidNew = None
        orderIDAskNew = None

        if buyS > 0 and self.cash >= bid * Decimal(buyS):
            orderIDBidNew = lob.submitLimitOrder("buy", float(bid), buyS, self, timeTick)

        if sellS > 0:
            orderIDAskNew = lob.submitLimitOrder("sell", float(ask), sellS, self, timeTick)

        if orderIDBidNew is not None and oldBidId is not None and oldBidId!= orderIDBidNew:
            lob.cancelOrder(oldBidId)

        if orderIDAskNew is not None and oldAskId is not None and oldAskId !=orderIDAskNew:
            lob.cancelOrder(oldAskId)

        self._orderIdBid = orderIDBidNew if orderIDBidNew is not None else oldBidId
        self._orderIdAsk = orderIDAskNew if orderIDAskNew is not None else oldAskId