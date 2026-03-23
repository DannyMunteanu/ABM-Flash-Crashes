import unittest
from decimal import Decimal
from unittest.mock import patch
import sys
import os
import pandas as pd

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
from Simulation.Market.Order import Order
from Simulation.Market.LimitOrderBook import LimitOrderBook
from Simulation.Market.Market import Market
from Simulation.Agents.AgentParent import AgentParent


class TestOrder(unittest.TestCase):
    """
    Tests the Order class for correct initialisation of order attributes,
    proper access via properties, and setting of order size.
    """

    def setUp(self):
        self.agent = AgentParent("TestAgent", 1000.0, 10)
        self.order = Order(
            orderId=1,
            sequenceNumber=10,
            side="buy",
            price=Decimal("50.0"),
            size=5,
            agent=self.agent,
            timeTick=1
        )

    def testProperties(self):
        self.assertEqual(self.order.orderId, 1)
        self.assertEqual(self.order.sequenceNumber, 10)
        self.assertEqual(self.order.side, "buy")
        self.assertEqual(self.order.price, Decimal("50.0"))
        self.assertEqual(self.order.size, 5)
        self.assertIs(self.order.agent, self.agent)
        self.assertEqual(self.order.timeTick, 1)

    def testSizeSetter(self):
        self.order.size = 7
        self.assertEqual(self.order.size, 7)


class TestLimitOrderBook(unittest.TestCase):
    """
    Tests the LimitOrderBook for correct submission of limit and market orders,
    order matching, cancellation, bid and ask price calculation, depth queries,
    mid-price, spread and trade history recording.
    """

    def setUp(self):
        self.book = LimitOrderBook()
        self.agent1 = AgentParent("Agent1", 1000.0, 10)
        self.agent2 = AgentParent("Agent2", 1000.0, 10)

    def testSubmitMarketOrderExecutesAgainstBest(self):
        self.book.submitLimitOrder("sell", Decimal("10.0"), 5, self.agent2, 1)
        avg_price, filled = self.book.submitMarketOrder("buy", 3, self.agent1, 2)
        self.assertEqual(filled, 3)
        self.assertAlmostEqual(float(avg_price), 10.0)

    def testCancelOrderRemovesFromBook(self):
        orderId = self.book.submitLimitOrder("buy", Decimal("10.0"), 5, self.agent1, 1)
        self.assertTrue(self.book.cancelOrder(orderId))
        self.assertNotIn(orderId, self.book._orders)

    def testBestBidBestAskMidPriceSpread(self):
        self.book.submitLimitOrder("buy", Decimal("9.0"), 5, self.agent1, 1)
        self.book.submitLimitOrder("sell", Decimal("11.0"), 5, self.agent2, 1)
        self.assertEqual(self.book.bestBid(), Decimal("9.0"))
        self.assertEqual(self.book.bestAsk(), Decimal("11.0"))
        self.assertEqual(self.book.midPrice(), 10.0)
        self.assertEqual(self.book.spread(), 2.0)

    def testDepthReturnsCorrectSum(self):
        self.book.submitLimitOrder("buy", Decimal("10.0"), 3, self.agent1, 1)
        self.book.submitLimitOrder("buy", Decimal("9.0"), 2, self.agent1, 1)
        self.assertEqual(self.book.depth("buy", 2), 5)

    def testTradeHistoryReturnsDataFrame(self):
        self.book.submitLimitOrder("buy", Decimal("10.0"), 1, self.agent1, 1)
        df = self.book.tradeHistory()
        self.assertIsInstance(df, pd.DataFrame)


class TestMarket(unittest.TestCase):
    """
    Tests the Market class for correct initialisation, fundamental price updates,
    and price updates using trades, order book state, and microstructure noise.
    """

    def setUp(self):
        self.book = LimitOrderBook()
        self.market = Market(
            self.book,
            initialFundamental=100.0,
            fundamentalVolatility=0.2,
            noiseStandard=0.01,
            initialPrice=100.0
        )

    def testInitialisation(self):
        self.assertEqual(float(self.market.fundamentalPrice), 100.0)
        self.assertEqual(float(self.market.price), 100.0)
        self.assertEqual(self.market.priceHistory[-1], 100.0)
        self.assertEqual(self.market.fundamentalHistory[-1], 100.0)

    def testUpdateFundamentalPositive(self):
        for _ in range(10):
            self.market.updateFundamental()
            self.assertGreater(self.market.fundamentalPrice, 0)

    @patch("random.gauss", return_value=0.0)
    def testUpdatePriceUsesLastTradeOrMidPrice(self, mock_gauss):
        mid = self.market.updatePrice(1)
        self.assertIsInstance(mid, float)
        self.book._trades.append({"price": 105.0, "size": 1, "aggressor": "buy"})
        new_price = self.market.updatePrice(2)
        self.assertAlmostEqual(new_price, 105.0, places=2)


if __name__ == "__main__":
    unittest.main()
