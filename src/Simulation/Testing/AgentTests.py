import unittest
from unittest.mock import MagicMock, patch
from decimal import Decimal

import pandas as pd
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
from Simulation.Agents.AgentParent import AgentParent
from Simulation.Agents.NoisyAgent import NoisyAgent
from Simulation.Agents.MarketMakerAgent import MarketMakerAgent
from Simulation.Agents.FundamentalAgent import FundamentalAgent
from Simulation.Agents.HighFrequencyAgent import HighFrequencyAgent
from Simulation.Agents.MomentumAgent import MomentumAgent
from Simulation.Agents.StopLossAgent import StopLossAgent


class TestAgentParent(unittest.TestCase):
    """
    Tests the base AgentParent class for correct initialisation, updating of cash and quantity on
    buy and sell, and proper recording and copying of trade history.
    """

    def setUp(self):
        self.agent = AgentParent(name="TestAgent", cash=1000.0, quantity=10)

    def testInitialisation(self):
        self.assertEqual(self.agent.cash, Decimal("1000.0"))
        self.assertEqual(self.agent.quantity, 10)
        self.assertTrue(isinstance(self.agent.history, pd.DataFrame))
        self.assertEqual(len(self.agent.history), 0)

    def testBuyUpdatesCashAndQuantity(self):
        self.agent.buy(timeTick=1, price=10.0, amount=5)
        self.assertEqual(self.agent.cash, Decimal("950.0"))
        self.assertEqual(self.agent.quantity, 15)

    def testSellUpdatesCashAndQuantity(self):
        self.agent.sell(timeTick=1, price=20.0, amount=5)
        self.assertEqual(self.agent.cash, Decimal("1100.0"))
        self.assertEqual(self.agent.quantity, 5)

    def testHistoryUpdatesOnBuy(self):
        self.agent.buy(timeTick=1, price=10.0, amount=2)
        history = self.agent.history
        self.assertEqual(len(history), 1)
        row = history.iloc[0]
        self.assertEqual(row["timeTick"], 1)
        self.assertEqual(row["action"], "BUY")
        self.assertEqual(row["price"], 10.0)
        self.assertEqual(row["amount"], 2)
        self.assertEqual(row["cashAfter"], 980.0)
        self.assertEqual(row["quantityAfter"], 12)

    def testHistoryUpdatesOnSell(self):
        self.agent.sell(timeTick=2, price=15.0, amount=3)
        history = self.agent.history
        self.assertEqual(len(history), 1)
        row = history.iloc[0]
        self.assertEqual(row["timeTick"], 2)
        self.assertEqual(row["action"], "SELL")
        self.assertEqual(row["price"], 15.0)
        self.assertEqual(row["amount"], 3)
        self.assertEqual(row["cashAfter"], 1045.0)
        self.assertEqual(row["quantityAfter"], 7)

    def testHistoryIsCopy(self):
        history_copy = self.agent.history
        history_copy.loc[0] = [0, "TEST", 0, 0, 0, 0]
        self.assertEqual(len(self.agent.history), 0)


class TestNoisyAgent(unittest.TestCase):
    """
    Tests NoisyAgent trading behaviour including respecting trade probability, executing buy/sell
    orders correctly, and preventing trades when price is None or resources are insufficient.
    """

    def setUp(self):
        self.agent = NoisyAgent(name="Noisy", cash=1000.0, quantity=10, tradeProbability=1.0, maxTradeNum=5)
        self.market = MagicMock()
        self.limitOrderBook = MagicMock()
        self.market.price = 10.0

    def testNoTradeWhenProbabilityNotMet(self):
        self.agent.tradeProbability = 0.0
        self.agent.step(self.market, self.limitOrderBook, timeTick=1)
        self.limitOrderBook.submitMarketOrder.assert_not_called()

    def testNoTradeWhenPriceNone(self):
        self.market.price = None
        self.agent.step(self.market, self.limitOrderBook, timeTick=1)
        self.limitOrderBook.submitMarketOrder.assert_not_called()

    def testBuyOrderSubmitted(self):
        patcherRandom = patch("random.random", side_effect=[0.0, 0.4])
        patcherRandint = patch("random.randint", return_value=3)
        patcherRandom.start()
        patcherRandint.start()
        self.agent.step(self.market, self.limitOrderBook, timeTick=1)
        self.limitOrderBook.submitMarketOrder.assert_called_once_with("buy", 3, self.agent, 1)
        patcherRandom.stop()
        patcherRandint.stop()

    def testSellOrderSubmitted(self):
        patcherRandom = patch("random.random", side_effect=[0.0, 0.6])
        patcherRandint = patch("random.randint", return_value=4)
        patcherRandom.start()
        patcherRandint.start()
        self.agent.step(self.market, self.limitOrderBook, timeTick=1)
        self.limitOrderBook.submitMarketOrder.assert_called_once_with("sell", 4, self.agent, 1)
        patcherRandom.stop()
        patcherRandint.stop()

    def testBuyNotExecutedIfNotEnoughCash(self):
        self.agent.cash = Decimal("5")
        patcherRandom = patch("random.random", side_effect=[0.0, 0.4])
        patcherRandint = patch("random.randint", return_value=3)
        patcherRandom.start()
        patcherRandint.start()
        self.agent.step(self.market, self.limitOrderBook, timeTick=1)
        self.limitOrderBook.submitMarketOrder.assert_not_called()
        patcherRandom.stop()
        patcherRandint.stop()

    def testSellNotExecutedIfNotEnoughInventory(self):
        self.agent.quantity = 1
        patcherRandom = patch("random.random", side_effect=[0.0, 0.6])
        patcherRandint = patch("random.randint", return_value=3)
        patcherRandom.start()
        patcherRandint.start()
        self.agent.step(self.market, self.limitOrderBook, timeTick=1)
        self.limitOrderBook.submitMarketOrder.assert_not_called()
        patcherRandom.stop()
        patcherRandint.stop()


class TestMarketMakerAgent(unittest.TestCase):
    """
    Tests MarketMakerAgent initialisation, bid/ask price computation based on inventory, cancellation
    of quotes, and submission of limit orders or no action when market price is None.
    """

    def setUp(self):
        self.agent = MarketMakerAgent(
            name="MMAgent",
            cash=1000.0,
            quantity=10,
            spread=0.4,
            maxTradeNum=5,
            inventoryAim=5,
            inventoryCap=20,
            movingWindowForPrices=3,
            withdrawTicks=10,
            durationForWithdrawal=5,
            withdrawCooldownTicks=10,
            withdrawalMinDepth=2,
            checkDepth=2
        )
        self.market = MagicMock()
        self.limitOrderBook = MagicMock()
        self.market.price = 10.0

    def testInitialisation(self):
        self.assertEqual(self.agent.cash, Decimal("1000.0"))
        self.assertEqual(self.agent.quantity, 10)
        self.assertEqual(self.agent.spread, Decimal("0.4"))
        self.assertEqual(self.agent.maxTradeNum, 5)
        self.assertEqual(self.agent.inventoryAim, 5)

    def testCancelQuotes(self):
        self.agent._orderIdBid = 1
        self.agent._orderIdAsk = 2
        self.agent._cancelQuotes(self.limitOrderBook)
        self.limitOrderBook.cancelOrder.assert_any_call(1)
        self.limitOrderBook.cancelOrder.assert_any_call(2)
        self.assertIsNone(self.agent._orderIdBid)
        self.assertIsNone(self.agent._orderIdAsk)

    def testComputeBidAsk(self):
        self.agent.quantity = 0
        bid, ask = self.agent._computeBidAsk(Decimal("10"))
        self.assertTrue(bid > 0)
        self.assertTrue(ask > bid)

        self.agent.quantity = self.agent.inventoryCap
        bid2, ask2 = self.agent._computeBidAsk(Decimal("10"))
        self.assertTrue(bid2 < bid)  # bid decreases when inventory at cap

    def testStepSubmitsOrders(self):
        self.agent._pricesList = [Decimal("10"), Decimal("10")]
        with patch("random.randint", side_effect=[2, 2]):
            self.agent.step(self.market, self.limitOrderBook, timeTick=1)
        self.assertIsNotNone(self.agent._orderIdBid)
        self.assertIsNotNone(self.agent._orderIdAsk)
        self.limitOrderBook.submitLimitOrder.assert_any_call(
            "buy", self.agent._prevBid, 2, self.agent, 1
        )
        self.limitOrderBook.submitLimitOrder.assert_any_call(
            "sell", self.agent._prevAsk, 2, self.agent, 1
        )

    def testStepDoesNothingWhenPriceNone(self):
        self.market.price = None
        self.agent.step(self.market, self.limitOrderBook, timeTick=1)
        self.assertEqual(len(self.agent._pricesList), 0)


class TestFundamentalAgent(unittest.TestCase):
    """
    Tests FundamentalAgent trading logic to buy when the asset is undervalued, sell when overvalued,
    and skip trades when insufficient cash or inventory is present or price is None.
    """

    def setUp(self):
        self.agent = FundamentalAgent(name="FundAgent", cash=1000.0, quantity=10, maxTradeSize=5)
        self.market = MagicMock()
        self.limitOrderBook = MagicMock()
        self.market.price = 10.0
        self.market.fundamentalPrice = 12.0

    def testInitialisation(self):
        self.assertEqual(self.agent.cash, Decimal("1000.0"))
        self.assertEqual(self.agent.quantity, 10)
        self.assertEqual(self.agent.maxTradeSize, 5)

    def testStepDoesNothingWhenPriceNone(self):
        self.market.price = None
        self.agent.step(self.market, self.limitOrderBook, timeTick=1)
        self.limitOrderBook.submitMarketOrder.assert_not_called()

    def testStepBuysWhenUndervalued(self):
        self.market.price = 8.0
        self.market.fundamentalPrice = 10.0
        with patch("random.randint", return_value=3):
            self.agent.step(self.market, self.limitOrderBook, timeTick=1)
        self.limitOrderBook.submitMarketOrder.assert_called_once_with("buy", 3, self.agent, 1)

    def testStepDoesNotBuyIfNotEnoughCash(self):
        self.market.price = 8.0
        self.market.fundamentalPrice = 10.0
        self.agent.cash = Decimal("5")
        with patch("random.randint", return_value=3):
            self.agent.step(self.market, self.limitOrderBook, timeTick=1)
        self.limitOrderBook.submitMarketOrder.assert_not_called()

    def testStepSellsWhenOvervalued(self):
        self.market.price = 12.0
        self.market.fundamentalPrice = 10.0
        with patch("random.randint", return_value=3):
            self.agent.step(self.market, self.limitOrderBook, timeTick=1)
        self.limitOrderBook.submitMarketOrder.assert_called_once_with("sell", 3, self.agent, 1)

    def testStepDoesNotSellIfNotEnoughInventory(self):
        self.market.price = 12.0
        self.market.fundamentalPrice = 10.0
        self.agent.quantity = 2
        with patch("random.randint", return_value=3):
            self.agent.step(self.market, self.limitOrderBook, timeTick=1)
        self.limitOrderBook.submitMarketOrder.assert_not_called()


class TestHighFrequencyAgent(unittest.TestCase):
    """
    Tests HighFrequencyAgent initialisation, trading probability, inventory-aware order sizes,
    bid and ask calculation, cancellation of quotes, trend detection, and behaviour in uptrends and downtrends.
    """

    def setUp(self):
        self.agent = HighFrequencyAgent(
            name="HFAgent",
            cash=1000.0,
            quantity=10,
            maxTradeNum=3,
            tradeProbability=1.0,
            inventoryCap=20,
            bufferBeforeReachingCap=4,
            downtrendWindow=3
        )
        self.market = MagicMock()
        self.limitOrderBook = MagicMock()
        self.market.priceHistory = [10.0, 10.5, 10.7]
        self.market.price = 10.0
        self.limitOrderBook.bestBid.return_value = 9.95
        self.limitOrderBook.bestAsk.return_value = 10.05

    def testInitialisation(self):
        self.assertEqual(self.agent.cash, Decimal("1000.0"))
        self.assertEqual(self.agent.quantity, 10)
        self.assertEqual(self.agent._maxTradeNum, 3)
        self.assertEqual(self.agent._tradeProbability, 1.0)
        self.assertEqual(self.agent._inventoryCap, 20)

    def testShouldTradeRespectsProbability(self):
        self.agent._tradeProbability = 0.0
        self.assertFalse(self.agent._shouldTrade())
        self.agent._tradeProbability = 1.0
        self.assertTrue(self.agent._shouldTrade())

    def testNeedsToSellTriggersSellWhenNearCap(self):
        self.agent.quantity = 18
        with patch("random.randint", return_value=2):
            result = self.agent._needsToSell(self.limitOrderBook, timeTick=1)
        self.assertTrue(result)
        self.limitOrderBook.submitMarketOrder.assert_called_with("sell", 2, self.agent, 1)

    def testNeedsToSellDoesNotSellIfBelowThreshold(self):
        self.agent.quantity = 10
        result = self.agent._needsToSell(self.limitOrderBook, timeTick=1)
        self.assertFalse(result)
        self.limitOrderBook.submitMarketOrder.assert_not_called()

    def testCalculateBidAskRegularAndAggressive(self):
        midPrice = Decimal("10.0")
        bid, ask = self.agent._calculateBidAsk(midPrice)
        self.assertEqual(bid, Decimal("9.99"))
        self.assertEqual(ask, Decimal("10.01"))
        bidAgg, askAgg = self.agent._calculateBidAsk(midPrice, aggressive=True)
        self.assertEqual(bidAgg, Decimal("10.0"))
        self.assertEqual(askAgg, Decimal("10.01"))

    def testCalculateSizesRespectsInventoryCap(self):
        self.agent.quantity = 18
        with patch("random.randint", return_value=3):
            bidSize, askSize = self.agent._calculateSizes()
        self.assertEqual(bidSize, 2)
        self.assertEqual(askSize, 3)

    def testCancelQuotesClearsOrders(self):
        self.agent._orderIdBid = 1
        self.agent._orderIdAsk = 2
        self.agent._cancelQuotes(self.limitOrderBook)
        self.limitOrderBook.cancelOrder.assert_any_call(1)
        self.limitOrderBook.cancelOrder.assert_any_call(2)
        self.assertIsNone(self.agent._orderIdBid)
        self.assertIsNone(self.agent._orderIdAsk)

    def testIsInDowntrendAndUptrend(self):
        self.market.priceHistory = [10.0, 11.0, 12.0, 9.0]
        self.assertTrue(self.agent._isInDowntrend(self.market))
        self.assertFalse(self.agent._isInUptrend(self.market))
        self.market.priceHistory = [10.0, 11.0, 9.0, 12.0]
        self.assertTrue(self.agent._isInUptrend(self.market))
        self.assertFalse(self.agent._isInDowntrend(self.market))

    def testStepDoesNothingIfNotTradingOrNoPrice(self):
        self.agent._tradeProbability = 0.0
        self.agent.step(self.market, self.limitOrderBook, timeTick=1)
        self.limitOrderBook.submitLimitOrder.assert_not_called()
        self.agent._tradeProbability = 1.0
        self.market.price = None
        self.agent.step(self.market, self.limitOrderBook, timeTick=1)
        self.limitOrderBook.submitLimitOrder.assert_not_called()

    def testStepSuppressesBidInDowntrend(self):
        self.market.priceHistory = [10.0, 11.0, 12.0, 9.0]
        with patch("random.randint", side_effect=[2, 2]):
            self.agent.step(self.market, self.limitOrderBook, timeTick=1)
        args = self.limitOrderBook.submitLimitOrder.call_args_list
        bids = [call for call in args if call[0][0] == "buy"]
        self.assertEqual(len(bids), 0)

    def testStepMaxBidInUptrend(self):
        self.market.priceHistory = [10.0, 11.0, 9.0, 12.0]
        self.agent.quantity = 10
        with patch("random.randint", side_effect=[2, 2]):
            self.agent.step(self.market, self.limitOrderBook, timeTick=1)
        args = self.limitOrderBook.submitLimitOrder.call_args_list
        bids = [call for call in args if call[0][0] == "buy"]
        self.assertTrue(len(bids) > 0)


class TestMomentumAgent(unittest.TestCase):
    """
    Tests MomentumAgent for correct rolling mean calculation, signal generation, maintenance of price
    history, trading respecting cooldowns and position limits, and correct trade execution or skipping.
    """

    def setUp(self):
        self.agent = MomentumAgent(
            name="MomentumAgent",
            cash=1000.0,
            quantity=10,
            shortWindow=2,
            longWindow=3,
            tradeSize=3,
            maxPosition=20,
            momentumThreshold=0.01,
            cooldownTicks=1
        )
        self.market = MagicMock()
        self.limitOrderBook = MagicMock()
        self.limitOrderBook.bestAsk.return_value = 10.0

    def testInitialisation(self):
        self.assertEqual(self.agent.cash, Decimal("1000.0"))
        self.assertEqual(self.agent.quantity, 10)
        self.assertEqual(self.agent.shortWindow, 2)
        self.assertEqual(self.agent.longWindow, 3)
        self.assertEqual(self.agent.tradeSize, 3)
        self.assertEqual(self.agent.maxPosition, 20)
        self.assertEqual(self.agent.momentumThreshold, Decimal("0.01"))

    def testRollingMeanReturnsNoneIfNotEnoughHistory(self):
        self.agent._prices = [1]
        self.assertIsNone(self.agent._rollingMean(2))

    def testRollingMeanComputesCorrectly(self):
        self.agent._prices = [1, 2, 3]
        self.assertEqual(self.agent._rollingMean(3), Decimal("2"))

    def testSignalReturnsBuySellOrNone(self):
        self.agent._prices = [10, 12, 13]
        self.agent.shortWindow = 2
        self.agent.longWindow = 3
        self.agent.momentumThreshold = Decimal("0.01")
        self.assertEqual(self.agent._signal(), "buy")
        self.agent._prices = [13, 12, 10]
        self.assertEqual(self.agent._signal(), "sell")
        self.agent._prices = [10, 10, 10]
        self.assertIsNone(self.agent._signal())

    def testUpdatePriceHistoryMaintainsLongWindow(self):
        self.agent.longWindow = 3
        self.agent._prices = [1, 2, 3]
        self.agent._updatePriceHistory(4)
        self.assertEqual(self.agent._prices, [2, 3, 4])

    def testCanTradeRespectsCooldown(self):
        self.agent._lastTradeTick = 5
        self.agent.cooldownTicks = 3
        self.assertFalse(self.agent._canTrade(7))
        self.assertTrue(self.agent._canTrade(8))

    def testComputeTradeSizeRespectsMaxPositionAndInventory(self):
        self.agent.quantity = 18
        self.agent.tradeSize = 5
        self.agent.maxPosition = 20
        self.assertEqual(self.agent._computeTradeSize("buy"), 2)
        self.assertEqual(self.agent._computeTradeSize("sell"), 5)
        self.agent.quantity = 0
        self.assertEqual(self.agent._computeTradeSize("sell"), 0)

    def testComputeAffordableSizeLimitsByCash(self):
        self.agent._cash = Decimal("15")
        self.limitOrderBook.bestAsk.return_value = 10
        self.assertEqual(self.agent._computeAffordableSize(self.limitOrderBook, 2), 1)
        self.limitOrderBook.bestAsk.return_value = 20
        self.assertEqual(self.agent._computeAffordableSize(self.limitOrderBook, 2), 0)

    def testExecuteTradeUpdatesLastTradeTick(self):
        self.limitOrderBook.submitMarketOrder.return_value = (Decimal("10"), 3)
        self.agent._lastTradeTick = 0
        self.agent._executeTrade("buy", 3, self.limitOrderBook, 5)
        self.assertEqual(self.agent._lastTradeTick, 5)

    def testStepExecutesTradeCorrectly(self):
        self.agent._prices = [10, 11, 12]
        self.agent.shortWindow = 2
        self.agent.longWindow = 3
        self.agent.momentumThreshold = Decimal("0.01")
        self.agent.tradeSize = 3
        self.agent.maxPosition = 20
        self.agent._lastTradeTick = -999
        self.limitOrderBook.submitMarketOrder.return_value = (Decimal("10"), 3)
        self.market.price = 13
        self.agent.step(self.market, self.limitOrderBook, timeTick=1)
        self.limitOrderBook.submitMarketOrder.assert_called()

    def testStepDoesNothingIfPriceNone(self):
        self.market.price = None
        self.agent.step(self.market, self.limitOrderBook, timeTick=1)
        self.limitOrderBook.submitMarketOrder.assert_not_called()


class TestStopLossAgent(unittest.TestCase):
    """
    Tests StopLossAgent initialisation, triggering of stop-loss and take-profit exits,
    enforcement of stop-triggered cooldowns, and step method correctly executing exits or entries.
    """

    def setUp(self):
        self.agent = StopLossAgent(
            name="StopLossAgent",
            cash=1000.0,
            quantity=10,
            stopLossPct=0.1,
            takeProfitPct=0.2,
            tradeSize=5,
            maxPosition=20,
            cooldownTicks=1,
            initialEntryPrice=10.0,
            stopTriggeredTimeout=5
        )
        self.market = MagicMock()
        self.limitOrderBook = MagicMock()
        self.limitOrderBook.bestAsk.return_value = 10.0

    def testInitialisation(self):
        self.assertEqual(self.agent.cash, Decimal("1000.0"))
        self.assertEqual(self.agent.quantity, 10)
        self.assertEqual(self.agent._entryPrice, Decimal("10.0"))
        self.assertFalse(self.agent._stopTriggered)

    def testTryExitTriggersTakeProfit(self):
        self.limitOrderBook.submitMarketOrder.return_value = (Decimal("12"), 5)
        exited = self.agent._tryExit(12.0, self.limitOrderBook, 1)
        self.assertTrue(exited)
        self.assertIsNone(self.agent._entryPrice)
        self.assertFalse(self.agent._stopTriggered)
        self.assertEqual(self.agent._lastTradeTick, 1)

    def testTryExitTriggersStopLoss(self):
        self.limitOrderBook.submitMarketOrder.return_value = (Decimal("8"), 5)
        exited = self.agent._tryExit(8.0, self.limitOrderBook, 2)
        self.assertTrue(exited)
        self.assertIsNone(self.agent._entryPrice)
        self.assertTrue(self.agent._stopTriggered)
        self.assertEqual(self.agent._stopExitPrice, Decimal("8.0"))
        self.assertEqual(self.agent._lastTradeTick, 2)

    def testStepExecutesExitOrEnter(self):
        self.agent._entryPrice = Decimal("10.0")
        self.agent._quantity = 5
        self.limitOrderBook.submitMarketOrder.return_value = (Decimal("12"), 5)
        self.market.price = 12.0
        self.agent._lastTradeTick = -999
        self.agent.step(self.market, self.limitOrderBook, 1)
        self.assertEqual(self.agent._lastTradeTick, 1)
        self.assertIsNone(self.agent._entryPrice)


if __name__ == "__main__":
    unittest.main()
