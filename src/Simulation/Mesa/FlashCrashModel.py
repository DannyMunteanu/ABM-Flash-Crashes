import mesa
from mesa import DataCollector
from decimal import Decimal
import random
from typing import List, Optional, Tuple, Dict
from ..Market.LimitOrderBook import LimitOrderBook
from ..Market.Market import Market
from .MesaAgentWrapper import MesaAgentWrapper
from ..Agents.AgentParent import AgentParent
from ..Agents.MarketMakerAgent import MarketMakerAgent
from ..Agents.NoisyAgent import NoisyAgent
from ..Agents.FundamentalAgent import FundamentalAgent
from ..Agents.HighFrequencyAgent import HighFrequencyAgent
from ..Agents.MomentumAgent import MomentumAgent
from ..Agents.StopLossAgent import StopLossAgent


class FlashCrashModel(mesa.Model):
    """
    FlashCrashModel is a Mesa model simulating a flash crash event within a market with multiple trading agents types.
    It also tracks market metrics such as mid-price, spread, and liquidity depth.
    """
    def __init__(
            self,
            numberOfMarketMakerAgents: int = 15,
            numberOfNoisyAgents: int = 7,
            numberOfFundamentalAgents: int = 3,
            numberOfHighFrequencyAgents: int = 2,
            numberOfMomentumTraders: int = 3,
            numberOfStopLossAgents: int = 3,
            fundamentalVolatility: float = 0.2,
            marketMakerSpread: float = 0.7,
            seed: Optional[int] = None,
            crashProbability: float = 0.002,
            crashDuration: int = 25,
            noCrashBefore: int = 250,
            waitTillNextCrash: int = 350,
    ) -> None:
        """
        Initialise the FlashCrashModel with the specified agent counts and market parameters.
        Parameters:
            numberOfMarketMakerAgents: Number of market maker agents.
            numberOfNoisyAgents: Number of noisy trading agents.
            numberOfFundamentalAgents: Number of fundamental-value trading agents.
            numberOfHighFrequencyAgents: Number of high-frequency trading agents.
            numberOfMomentumTraders: Number of momentum trading agents.
            numberOfStopLossAgents: Number of stop-loss agents.
            fundamentalVolatility: Standard deviation for fundamental price updates.
            marketMakerSpread: Default spread for market maker agents.
            seed: Optional random seed for reproducibility.
            crashProbability: Probability per step of triggering a flash crash.
            crashDuration: Duration (in ticks) of a flash crash.
            noCrashBefore: Minimum number of ticks before the first crash can occur.
            waitTillNextCrash: Cooldown period before another crash may happen.
        """
        super().__init__(seed=seed)
        self.limitOrderBook = LimitOrderBook()
        self.market = Market(self.limitOrderBook, fundamentalVolatility=fundamentalVolatility)
        self.timeTick = 0
        self.crashProbability = crashProbability
        self.crashDuration = crashDuration
        self.noCrashBefore = noCrashBefore
        self.waitTillNextCrash = waitTillNextCrash
        self.activeCrashTicks = 0
        self.crashCooldown = 0
        self.crashEvents = []
        self.bidLiquidityDepth = 25
        self.shockAmount = Decimal("25")
        self.basePressure = 80
        self.maxSell = Decimal("0.98")
        self.perTickSellSweep = 6
        self.marketMakers = [
            MarketMakerAgent(
                f"Market Maker Agent #{index}", cash=5000, quantity=50,
                spread=marketMakerSpread, maxTradeNum=7, inventoryAim=50,
                inventoryCoefficient=0.001, inventoryCap=500,
                movingWindowForPrices=random.randint(95, 105),
                withdrawTicks=random.randint(30, 35),
                durationForWithdrawal=10,
                withdrawCooldownTicks=random.randint(80, 120),
                withdrawalMinDepth=35,
                inventoryPressureTicks=5,
                checkDepth=10,
            )
            for index in range(numberOfMarketMakerAgents)
        ]
        self.noisy = [
            NoisyAgent(
                f"Noisy Agent #{index}", cash=5000, quantity=50,
                tradeProbability=0.5, maxTradeNum=4
            )
            for index in range(numberOfNoisyAgents)
        ]
        self.fundamental = [
            FundamentalAgent(
                f"Fundamental Agent #{index}", cash=5000, quantity=50,
                maxTradeSize=3
            )
            for index in range(numberOfFundamentalAgents)
        ]
        self.highFrequency = [
            HighFrequencyAgent(
                f"High Frequency Agent #{index}", cash=5000, quantity=5,
                maxTradeNum=3,
                tradeProbability=1.0,
                inventoryCap=40,
                bufferBeforeReachingCap=4
            )
            for index in range(numberOfHighFrequencyAgents)
        ]
        self.momentum = [
            MomentumAgent(
                f"Momentum agent #{index}", cash=5000, quantity=50,
                shortWindow=5,
                longWindow=20,
                tradeSize=2,
                maxPosition=50,
                momentumThreshold=0.002,
                cooldownTicks=3
            )
            for index in range(numberOfMomentumTraders)
        ]
        self.stopLoss = [
            StopLossAgent(
                f"Stop Loss Agent #{index}", cash=5000, quantity=50,
                stopLossPct=0.03,
                takeProfitPct=0.05,
                tradeSize=5,
                maxPosition=50,
                cooldownTicks=10
            )
            for index in range(numberOfStopLossAgents)
        ]
        self.allInner: List[AgentParent] = (
                self.marketMakers
                + self.noisy
                + self.fundamental
                + self.highFrequency
                + self.momentum
                + self.stopLoss
        )
        self.mesaAgents = [MesaAgentWrapper(self, agent) for agent in self.allInner]
        self.dataCollector = DataCollector(
            model_reporters={
                "MidPrice": lambda m: m.limitOrderBook.midPrice(),
                "Fundamental": lambda m: float(m.market.fundamentalPrice),
                "BestBid": lambda m: float(m.limitOrderBook.bestBid()) if m.limitOrderBook.bestBid() else None,
                "BestAsk": lambda m: float(m.limitOrderBook.bestAsk()) if m.limitOrderBook.bestAsk() else None,
                "Spread": lambda m: m.limitOrderBook.spread(),
                "BidDepth": lambda m: m.limitOrderBook.depth("buy", levels=10),
                "AskDepth": lambda m: m.limitOrderBook.depth("sell", levels=10),
                "TradeCount": lambda m: len(m.limitOrderBook.trades),
                "CrashActive": lambda m: 1 if m.activeCrashTicks > 0 else 0,
            }
        )
        self.dataCollector.collect(self)

    def step(self) -> None:
        """
        Advances the simulation by one tick and updates the fundamental price and  market price.
        Step also checks for flash crash conditions, and performs panic selling if a crash is triggered.
        All agent steps are executed in random order,
        """
        self.timeTick += 1
        tick = self.timeTick
        self.market.updateFundamental()
        agents = list(self.mesaAgents)
        random.shuffle(agents)
        if self.marketMakers:
            chosenMarkerMaker = random.choice(self.marketMakers)
            for wrapper in agents:
                if wrapper.inner == chosenMarkerMaker:
                    agents.remove(wrapper)
                    agents.insert(0, wrapper)
                    break
        for wrapper in agents:
            wrapper.step()
        if self.crashCooldown > 0:
            self.crashCooldown -= 1
        else:
            if (
                    tick >= self.noCrashBefore
                    and self.activeCrashTicks == 0
                    and self.limitOrderBook.bestBid() is not None
                    and (self.limitOrderBook.depth("buy", levels=3) or 0) >= 20
                    and random.random() < self.crashProbability
            ):
                self.activeCrashTicks = self.crashDuration
                self.crashCooldown = self.waitTillNextCrash
                self.crashEvents.append(tick)
        if self.activeCrashTicks > 0:
            if self.limitOrderBook.bestBid() is None:
                self.activeCrashTicks = 0
            else:
                if self.fundamental:
                    panicSeller: AgentParent = random.choice(self.fundamental)
                elif self.noisy:
                    panicSeller = random.choice(self.noisy)
                else:
                    panicSeller = random.choice(self.allInner)
                for _ in range(self.perTickSellSweep):
                    if self.limitOrderBook.bestBid() is None:
                        break
                    bidDepth: int = self.limitOrderBook.depth("buy", levels=self.bidLiquidityDepth) or 0
                    available: int = sum(self.limitOrderBook.bidQuantity.values())
                    if available <= 0:
                        available = bidDepth
                    if available <= 0:
                        break
                    panicSize: int = min(
                        max(self.basePressure, int(float(self.shockAmount) * float(bidDepth))),
                        int(Decimal(available) * self.maxSell),
                    )
                    if panicSize > 0:
                        self.limitOrderBook.submitMarketOrder("sell", panicSize, panicSeller, tick)
                self.activeCrashTicks -= 1
        self.market.updatePrice(tick)
        self.dataCollector.collect(self)

    def getOrderBookSnapshot(self, levels: int = 10) -> Tuple[List[Dict[str, float]], List[Dict[str, float]]]:
        """
        Returns the top N levels of the bid and ask sides.
        Both sides, are coupled as a tuple, and are a list of dictionaries for each order.
        Parameters:
            levels: Number of top price levels to return for each side.
        """
        bids = sorted(self.limitOrderBook.bids.keys(), reverse=True)[:levels]
        asks = sorted(self.limitOrderBook.asks.keys())[:levels]
        bidData = [
            {"price": float(price), "qty": self.limitOrderBook.bidQuantity[price], "side": "bid"}
            for price in bids
        ]
        askData = [
            {"price": float(price), "qty": self.limitOrderBook.askQuantity[price], "side": "ask"}
            for price in asks
        ]
        return bidData, askData

    def getRecentTrades(self, number: int = 20) -> List[Dict[str, float]]:
        """
        Returns the most recent trades recorded in the order book as a list of orders.
        Parameters:
            number: Number of recent trades to return.
        """
        return self.limitOrderBook.trades[-number:] if self.limitOrderBook.trades else []

    def triggerManualCrash(self) -> None:
        """
        Manually triggers a flash crash if no crash is currently active and the book is not empty.
        """
        if self.activeCrashTicks == 0 and self.limitOrderBook.bestBid() is not None:
            self.activeCrashTicks = self.crashDuration
            self.crashCooldown = self.waitTillNextCrash
            self.crashEvents.append(self.timeTick)
