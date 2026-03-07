import mesa
from mesa import DataCollector
from decimal import Decimal
import random
import sys, os

#Path setup so relative imports inside Agents/ and lob_and_market/ work ────
_here = os.path.dirname(os.path.abspath(__file__))
if _here not in sys.path:
    sys.path.insert(0, os.path.dirname(_here))

from flash_crash_sim.lob_and_market.LimitOrderBook import LimitOrderBook
from flash_crash_sim.lob_and_market.Market import Market
from flash_crash_sim.Agents.MarketMakerAgent import MarketMakerAgent
from flash_crash_sim.Agents.NoisyAgent import NoisyAgent
from flash_crash_sim.Agents.FundamentalAgent import FundamentalAgent
from flash_crash_sim.Agents.HFTAgent import HFTAgent
from flash_crash_sim.Agents.MomentumAgent import MomentumAgent
from flash_crash_sim.Agents.StopLossAgent import StopLossAgent


# Thin Mesa wrapper so each agent is also a mesa.Agent
class MesaAgentWrapper(mesa.Agent):
    """Wraps any existing agent so Mesa can track it."""
    def __init__(self, model, inner):
        super().__init__(model)
        self.inner = inner

    def step(self, market, lob, timeTick):
        self.inner.step(market, lob, timeTick)


#flash crash model
class FlashCrashModel(mesa.Model):

    def __init__(
        self,
        n_market_maker=15,
        n_noisy=7,
        n_fundamental=3,
        n_hft=2,
        n_momentum=3,
        n_stoploss=3,
        fundamental_vol=0.2,
        mm_spread=0.7,
        seed=None,
        # Flash crash params
        crash_prob=0.002,
        crash_duration=25,
        no_crash_before=250,
        wait_till_next_crash=350,
    ):
        super().__init__(seed=seed)

        self.lob = LimitOrderBook()
        self.market = Market(self.lob, fundamentalVol=fundamental_vol)
        self.timeTick = 0

        # Flash crash state
        self.crash_prob = crash_prob
        self.crash_duration = crash_duration
        self.no_crash_before = no_crash_before
        self.wait_till_next_crash = wait_till_next_crash
        self.active_crash_ticks = 0
        self.crash_cooldown = 0
        self.crash_events = []  # list of ticks where a crash started

        # Crash mechanics (from main.py)
        self._bid_liquidity_depth = 25
        self._shock_amount = Decimal("25")
        self._base_pressure = 80
        self._max_sell = Decimal("0.98")
        self._per_tick_sell_sweep = 6

        #Create inner agents
        self._market_makers = [
            MarketMakerAgent(
                f"MM_{i}", cash=5000, quantity=50,
                spread=mm_spread, maxTradeNum=7, inventoryAim=50,
                inventoryCoefficient=0.001, inventoryCap=500,
                movingWindowForPrices=random.randint(95, 105),
                withdrawTicks=random.randint(30, 35),
                durationForWithdrawal=10,
                withdrawCooldownTicks=random.randint(80, 120),
                withdrawalMinDepth=35, inventoryPressureTicks=5, checkDepth=10,
            ) for i in range(n_market_maker)
        ]
        self._noisy = [
            NoisyAgent(f"NOISE_{i}", cash=5000, quantity=50,
                       tradeProbability=0.5, maxTradeNum=4)
            for i in range(n_noisy)
        ]
        self._fundamental = [
            FundamentalAgent(f"FUND_{i}", cash=5000, quantity=50, maxTradeSize=3)
            for i in range(n_fundamental)
        ]
        self._hft = [
            HFTAgent(f"HFT_{i}", cash=5000, quantity=5, maxTradeNum=3,
                     tradeProbability=1.0, inventoryCap=40, bufferBeforeReachingCap=4)
            for i in range(n_hft)
        ]
        self._momentum = [
            MomentumAgent(f"MOM_{i}", cash=5000, quantity=50,
                          shortWindow=5, longWindow=20, tradeSize=2,
                          maxPosition=50, momentumThreshold=0.002, cooldownTicks=3)
            for i in range(n_momentum)
        ]
        self._stoploss = [
            StopLossAgent(f"SL_{i}", cash=5000, quantity=50,
                          stopLossPct=0.03, takeProfitPct=0.05,
                          tradeSize=5, maxPosition=50, cooldownTicks=10)
            for i in range(n_stoploss)
        ]

        self._all_inner = (self._market_makers + self._noisy + self._fundamental
                           + self._hft + self._momentum + self._stoploss)

        # Wrap each inner agent for Mesa tracking
        for inner in self._all_inner:
            MesaAgentWrapper(model=self, inner=inner)

        #Data Collection
        self.datacollector = DataCollector(
            model_reporters={
                "MidPrice":    lambda m: m.lob.midPrice(),
                "Fundamental": lambda m: float(m.market.fundamentalPrice),
                "BestBid":     lambda m: float(m.lob.bestBid()) if m.lob.bestBid() else None,
                "BestAsk":     lambda m: float(m.lob.bestAsk()) if m.lob.bestAsk() else None,
                "Spread":      lambda m: m.lob.spread(),
                "BidDepth":    lambda m: m.lob.depth("buy", levels=10),
                "AskDepth":    lambda m: m.lob.depth("sell", levels=10),
                "TradeCount":  lambda m: len(m.lob.trades),
                "CrashActive": lambda m: 1 if m.active_crash_ticks > 0 else 0,
            }
        )
        self.datacollector.collect(self)

    # Step 
    def step(self):
        self.timeTick += 1
        t = self.timeTick

        self.market.updateFundamental()

        # Shuffle: market maker always gets priority
        agents = list(self._all_inner)
        random.shuffle(agents)
        if self._market_makers:
            chosen_mm = random.choice(self._market_makers)
            agents.remove(chosen_mm)
            agents.insert(0, chosen_mm)

        for a in agents:
            a.step(self.market, self.lob, t)

        #Flash crash logic 
        if self.crash_cooldown > 0:
            self.crash_cooldown -= 1
        else:
            if (
                t >= self.no_crash_before
                and self.active_crash_ticks == 0
                and self.lob.bestBid() is not None
                and (self.lob.depth("buy", levels=3) or 0) >= 20
                and random.random() < self.crash_prob
            ):
                self.active_crash_ticks = self.crash_duration
                self.crash_cooldown = self.wait_till_next_crash
                self.crash_events.append(t)

        if self.active_crash_ticks > 0:
            if self.lob.bestBid() is None:
                self.active_crash_ticks = 0
            else:
                if self._fundamental:
                    aggressor = random.choice(self._fundamental)
                elif self._noisy:
                    aggressor = random.choice(self._noisy)
                else:
                    aggressor = random.choice(self._all_inner)

                for _ in range(self._per_tick_sell_sweep):
                    if self.lob.bestBid() is None:
                        break
                    bid_d = self.lob.depth("buy", levels=self._bid_liquidity_depth) or 0
                    available = sum(self.lob.bidQty.values())
                    if available <= 0:
                        available = bid_d
                    if available <= 0:
                        break
                    panic_size = min(
                        int(max(self._base_pressure, float(self._shock_amount) * float(bid_d))),
                        int(Decimal(available) * self._max_sell),
                    )
                    if panic_size > 0:
                        self.lob.submitMarketOrder("sell", panic_size, aggressor, t)

                self.active_crash_ticks -= 1

        self.market.updatePrice(t)
        self.datacollector.collect(self)

    #Helper fns
    def get_order_book_snapshot(self, levels=10):
        bids = sorted(self.lob.bids.keys(), reverse=True)[:levels]
        asks = sorted(self.lob.asks.keys())[:levels]
        bid_data = [{"price": float(p), "qty": self.lob.bidQty[p], "side": "bid"} for p in bids]
        ask_data = [{"price": float(p), "qty": self.lob.askQty[p], "side": "ask"} for p in asks]
        return bid_data, ask_data

    def get_recent_trades(self, n=20):
        return self.lob.trades[-n:] if self.lob.trades else []

    def trigger_manual_crash(self):
        """Called from the UI to manually trigger a flash crash."""
        if self.active_crash_ticks == 0 and self.lob.bestBid() is not None:
            self.active_crash_ticks = self.crash_duration
            self.crash_cooldown = self.wait_till_next_crash
            self.crash_events.append(self.timeTick)
