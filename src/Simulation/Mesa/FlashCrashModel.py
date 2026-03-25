import mesa
from mesa import DataCollector
from decimal import Decimal
import random
import numpy as np
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
    Data collection can be disabled via the collectData flag for faster batch simulation runs.
    """
    def __init__(
            self,
            numberOfMarketMakerAgents: int = 15,
            numberOfNoisyAgents: int = 7,
            numberOfFundamentalAgents: int = 3,
            numberOfHighFrequencyAgents: int = 2,
            numberOfMomentumAgents: int = 3,
            numberOfStopLossAgents: int = 3,
            fundamentalVolatility: float = 0.2,
            marketMakerSpread: float = 0.7,
            seed: Optional[int] = None,
            crashProbability: float = 0.002,
            crashDuration: int = 25,
            noCrashBefore: int = 250,
            waitTillNextCrash: int = 350,
            marketMakerStepProbability: float = 0.9,
            noisyStepProbability: float = 0.5,
            fundamentalStepProbability: float = 0.02,
            highFrequencyStepProbability: float = 1.0,
            momentumStepProbability: float = 0.33,
            stopLossStepProbability: float = 0.5,
            collectData: bool = True,
    ) -> None:
        """
        Initialise the FlashCrashModel with the specified agent counts and market parameters.
        Parameters:
            numberOfMarketMakerAgents: Number of market maker agents.
            numberOfNoisyAgents: Number of noisy trading agents.
            numberOfFundamentalAgents: Number of fundamental-value trading agents.
            numberOfHighFrequencyAgents: Number of high-frequency trading agents.
            numberOfMomentumAgents: Number of momentum trading agents.
            numberOfStopLossAgents: Number of stop-loss agents.
            fundamentalVolatility: Standard deviation for fundamental price updates.
            marketMakerSpread: Default spread for market maker agents.
            seed: Optional random seed for reproducibility.
            crashProbability: Probability per step of triggering a flash crash.
            crashDuration: Duration (in ticks) of a flash crash.
            noCrashBefore: Minimum number of ticks before the first crash can occur.
            waitTillNextCrash: Cooldown period before another crash may happen.
            marketMakerStepProbability: Fraction of market maker agents that act each tick.
            noisyStepProbability: Fraction of noisy agents that act each tick.
            fundamentalStepProbability: Fraction of fundamental agents that act each tick.
            highFrequencyStepProbability: Fraction of high-frequency agents that act each tick.
            momentumStepProbability: Fraction of momentum agents that act each tick.
            stopLossStepProbability: Fraction of stop-loss agents that act each tick.
            collectData: If True, enables the DataCollector for dashboard use. Set to False for
                         batch runner simulations to avoid per-tick overhead on unused metrics.
        """
        super().__init__(seed=seed)
        self.limitOrderBook = LimitOrderBook()
        self.market = Market(self.limitOrderBook, fundamentalVolatility=fundamentalVolatility)
        self.timeTick = 0
        self.crashWindows: List[Tuple[int, int]] = []
        self.currentCrashStart: Optional[int] = None
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
                f"Market Maker Agent #{index}", cash=500000, quantity=60,
                spread=0.2, maxTradeNum=10, inventoryAim=60,
                inventoryCoefficient=0.005, inventoryCap=120,
                movingWindowForPrices=random.randint(10, 20),
                withdrawTicks=random.randint(3, 6),
                durationForWithdrawal=2,
                withdrawCooldownTicks=random.randint(10, 20),
                withdrawalMinDepth=8,
                inventoryPressureTicks=2,
                checkDepth=5,
            )
            for index in range(numberOfMarketMakerAgents)
        ]
        self.noisy = [
            NoisyAgent(
                f"Noisy Agent #{index}", cash=10000, quantity=15,
                tradeProbability=0.5, maxTradeNum=3
            )
            for index in range(numberOfNoisyAgents)
        ]
        self.fundamental = [
            FundamentalAgent(
                f"Fundamental Agent #{index}", cash=10000, quantity=15,
                maxTradeSize=2
            )
            for index in range(numberOfFundamentalAgents)
        ]
        self.highFrequency = [
            HighFrequencyAgent(
                f"High Frequency Agent #{index}", cash=500000, quantity=50,
                maxTradeNum=20,
                tradeProbability=1.0,
                inventoryCap=200,
                bufferBeforeReachingCap=20,
                downtrendWindow=3,
            )
            for index in range(numberOfHighFrequencyAgents)
        ]
        self.momentum = [
            MomentumAgent(
                f"Momentum agent #{index}", cash=25000, quantity=60,
                shortWindow=5,
                longWindow=20,
                tradeSize=5,
                maxPosition=120,
                momentumThreshold=0.005,
                cooldownTicks=5
            )
            for index in range(numberOfMomentumAgents)
        ]
        self.stopLoss = [
            StopLossAgent(
                f"Stop Loss Agent #{index}", cash=50000, quantity=20,
                stopLossPct=0.04,
                takeProfitPct=0.08,
                tradeSize=5,
                maxPosition=40,
                cooldownTicks=5,
                initialEntryPrice=round(random.uniform(95.0, 105.0), 2),
                stopTriggeredTimeout=50,
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
        self._panicPool: List[AgentParent] = (
                self.noisy
                + self.fundamental
                + self.highFrequency
                + self.momentum
                + self.stopLoss
        ) or self.allInner
        self.mesaAgents = [MesaAgentWrapper(self, agent) for agent in self.allInner]
        self._innerToWrapper: Dict[int, MesaAgentWrapper] = {
            id(w.inner): w for w in self.mesaAgents
        }
        self._wrappersByType: Dict[str, Tuple[List[MesaAgentWrapper], float]] = {
            "marketMaker":   ([self._innerToWrapper[id(a)] for a in self.marketMakers],   marketMakerStepProbability),
            "noisy":         ([self._innerToWrapper[id(a)] for a in self.noisy],          noisyStepProbability),
            "fundamental":   ([self._innerToWrapper[id(a)] for a in self.fundamental],    fundamentalStepProbability),
            "highFrequency": ([self._innerToWrapper[id(a)] for a in self.highFrequency],  highFrequencyStepProbability),
            "momentum":      ([self._innerToWrapper[id(a)] for a in self.momentum],       momentumStepProbability),
            "stopLoss":      ([self._innerToWrapper[id(a)] for a in self.stopLoss],       stopLossStepProbability),
        }
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
        ) if collectData else None
        if self.dataCollector:
            self.dataCollector.collect(self)

    def _sampleActiveWrappers(self) -> List[MesaAgentWrapper]:
        """
        Samples the subset of agents that will act this tick using per-type step probabilities.
        Each type uses vectorised Bernoulli sampling to select active agents, then the combined
        list is shuffled. One market maker is always guaranteed as the first agent to act.
        """
        active: List[MesaAgentWrapper] = []
        for wrappers, prob in self._wrappersByType.values():
            if not wrappers or prob <= 0.0:
                continue
            if prob >= 1.0:
                active.extend(wrappers)
            else:
                mask = np.random.random(len(wrappers)) < prob
                active.extend(w for w, selected in zip(wrappers, mask) if selected)
        random.shuffle(active)
        marketMakerWrappers, _ = self._wrappersByType["marketMaker"]
        if marketMakerWrappers:
            leader = random.choice(marketMakerWrappers)
            if leader in active:
                active.remove(leader)
            active.insert(0, leader)
        return active

    def step(self) -> None:
        """
        Advances the simulation by one tick and updates the fundamental price and market price.
        Step also checks for flash crash conditions, and performs panic selling if a crash is triggered.
        Each tick, only a sampled subset of agents act determined by per-type step probabilities.
        Panic selling is distributed across all non-market-maker agent types so that HFT, momentum,
        and stop-loss agents contribute proportionally to crash severity when present.
        """
        self.timeTick += 1
        tick = self.timeTick
        self.market.updateFundamental()
        for wrapper in self._sampleActiveWrappers():
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
                self.currentCrashStart = tick
        if self.activeCrashTicks > 0:
            if self.limitOrderBook.bestBid() is None:
                self.activeCrashTicks = 0
            else:
                panicSeller = random.choice(self._panicPool)
                for _ in range(self.perTickSellSweep):
                    if self.limitOrderBook.bestBid() is None:
                        break
                    bidDepth: int = self.limitOrderBook.depth("buy", levels=self.bidLiquidityDepth) or 0
                    if bidDepth <= 0:
                        break
                    panicSize: int = min(
                        max(self.basePressure, int(float(self.shockAmount) * float(bidDepth))),
                        int(Decimal(bidDepth) * self.maxSell),
                    )
                    if panicSize > 0:
                        self.limitOrderBook.submitMarketOrder("sell", panicSize, panicSeller, tick)
                self.activeCrashTicks -= 1
                if self.activeCrashTicks == 0 and self.currentCrashStart is not None:
                    self.crashWindows.append((self.currentCrashStart, tick))
                    self.currentCrashStart = None
        self.market.updatePrice(tick)
        if self.dataCollector:
            self.dataCollector.collect(self)

    def getOrderBookSnapshot(self, levels: int = 10) -> Tuple[List[Dict[str, float]], List[Dict[str, float]]]:
        """
        Returns the top N levels of the bid and ask sides.
        Both sides, are coupled as a tuple, and are a list of dictionaries for each order.
        Parameters:
            levels: Number of top price levels to return for each side.
        """
        bids = list(self.limitOrderBook.sortedBidPrices[:levels])
        asks = list(self.limitOrderBook.sortedAskPrices[:levels])
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
            self.currentCrashStart = self.timeTick