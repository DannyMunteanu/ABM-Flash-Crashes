import pandas as pd
from decimal import Decimal

class AgentParent:
    def __init__(self, name: str, cash: float = 0.0, quantity: int = 0):
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
        return self._cash

    @cash.setter
    def cash(self, value: float) -> None:
        self._cash = Decimal(str(value))

    @property
    def quantity(self) -> int:
        return self._quantity

    @quantity.setter
    def quantity(self, value: int) -> None:
        self._quantity = value

    @property
    def history(self) -> pd.DataFrame:
        return self._history.copy()

    def buy(self, timeTick: int, price: float, amount: int) -> None:
        decimalPrice = Decimal(str(price))
        totalCost = decimalPrice * amount
        self._cash -= totalCost
        self._quantity += amount
        self.updateHistory(timeTick, "BUY", decimalPrice, amount)

    def sell(self, timeTick: int, price: float, amount: int) -> None:
        decimalPrice = Decimal(str(price))
        totalRevenue = decimalPrice * amount
        self._cash += totalRevenue
        self._quantity -= amount
        self.updateHistory(timeTick, "SELL", decimalPrice, amount)

    def updateHistory(self, timeTick: int, action: str, price: Decimal, amount: int):
        newRow = pd.DataFrame([{
            "timeTick": timeTick,
            "action": action,
            "price": float(price),
            "amount": amount,
            "cashAfter": float(self._cash),
            "quantityAfter": self._quantity
        }])
        self._history = pd.concat([self._history, newRow], ignore_index=True)
