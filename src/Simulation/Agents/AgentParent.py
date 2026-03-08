import pandas as pd
from decimal import Decimal


class AgentParent:
    """
    AgentParent acts as a blueprint, which all other agents inherit from.
    It stores the unique identifier, cash balance, asset holdings, and a history of executed trades.
    """

    def __init__(self, name: str, cash: float = 0.0, quantity: int = 0):
        """
        Initialises an AgentParent.
        Parameters:
            name: Unique string identifier.
            cash: Starting amount of liquidity.
            quantity: Starting amount of assets held.
        """
        self._name = name
        self._cash = Decimal(str(cash))
        self._quantity = quantity
        self._history = pd.DataFrame(
            columns=[
                "timeTick",
                "action",
                "price",
                "amount",
                "cashAfter",
                "quantityAfter"
            ]
        )

    @property
    def cash(self) -> Decimal:
        """
        Getter method returns the current amount of cash.
        """
        return self._cash

    @cash.setter
    def cash(self, value: float) -> None:
        """
        Setter method updates the amount of cash.
        """
        self._cash = Decimal(str(value))

    @property
    def quantity(self) -> int:
        """
        Getter method returns the quantity of assets currently held.
        """
        return self._quantity

    @quantity.setter
    def quantity(self, value: int) -> None:
        """
        Setter method updates the quantity of assets held.
        """
        self._quantity = value

    @property
    def history(self) -> pd.DataFrame:
        """
        Getter method returns a copy of the DataFrame that stores the trade history.
        """
        return self._history.copy()

    def buy(self, timeTick: int, price: float, amount: int) -> None:
        """
        Executes a buy transaction for the agent, once an order is filled in LogOrderBook.
        Cash is reduced by the total cost and asset quantity increases.
        Parameters:
            timeTick: Current point in time for the simulation.
            price: Execution price of the trade.
            amount: Quantity of assets purchased.
        """
        decimalPrice = Decimal(str(price))
        totalCost = decimalPrice * amount
        self._cash -= totalCost
        self._quantity += amount
        self.updateHistory(timeTick, "BUY", decimalPrice, amount)

    def sell(self, timeTick: int, price: float, amount: int) -> None:
        """
        Executes a sell transaction for the agent, once an order is filled in LogOrderBook.
        Cash increases by the total revenue and asset quantity decreases.
        Parameters:
            timeTick: Current point in time for the simulation.
            price: Execution price of the trade.
            amount: Quantity of assets sold.
        """
        decimalPrice = Decimal(str(price))
        totalRevenue = decimalPrice * amount
        self._cash += totalRevenue
        self._quantity -= amount
        self.updateHistory(timeTick, "SELL", decimalPrice, amount)

    def updateHistory(self, timeTick: int, action: str, price: Decimal, amount: int):
        """
        Appends a new entry, represented as a new DataFrame, to the existing history data structure.
        Parameters:
            timeTick: Current point in time for the simulation.
            action: Can either be Buy or Sell.
            price: Execution price of the trade.
            amount: Quantity traded.
        """
        newRow = pd.DataFrame([{
            "timeTick": timeTick,
            "action": action,
            "price": float(price),
            "amount": amount,
            "cashAfter": float(self._cash),
            "quantityAfter": self._quantity
        }])
        self._history = pd.concat([self._history, newRow], ignore_index=True)
