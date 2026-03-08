from decimal import Decimal
from ..Agents.AgentParent import AgentParent


class Order:
    """
    Order represents a single order in the limit order book.
    Each order has a unique identifier and a sequence number to enforce first in first out within a price level.
    Tracks the buy or sell side , limit price, quantity, submitting agent, and time of submission.
    """

    def __init__(
        self,
        orderId: int,
        sequenceNumber: int,
        side: str,
        price: Decimal,
        size: int,
        agent: AgentParent,
        timeTick: int
    ) -> None:
        """
        Initialise an Order.
        Parameters:
            orderId: Unique integer identifier for this order.
            sequenceNumber: Sequence number to maintain first in first out ordering at a given price level.
            side: buy or sell, indicating order type.
            price: Decimal representing the limit price for this order.
            size: Integer quantity of units to buy or sell.
            agent: Reference to the AgentParent instance placing the order.
            timeTick: Simulation time step when this order was submitted.
        """
        self._orderId: int = orderId
        self._sequenceNumber: int = sequenceNumber
        self._side: str = side  # "buy" or "sell"
        self._price: Decimal = price
        self._size: int = size
        self._agent: AgentParent = agent
        self._timeTick: int = timeTick

    @property
    def orderId(self) -> int:
        """
        Returns the unique order ID of this order.
        """
        return self._orderId

    @property
    def sequenceNumber(self) -> int:
        """
        Returns the sequence number of the order.
        The sequence number enforces strict first in first out priority among orders at the same price level.
        """
        return self._sequenceNumber

    @property
    def side(self) -> str:
        """
        Returns the side of the order buy or sell.
        """
        return self._side

    @property
    def price(self) -> Decimal:
        """
        Returns the limit price for this order.
        """
        return self._price

    @property
    def size(self) -> int:
        """
        Returns the current quantity of the order.
        """
        return self._size

    @property
    def agent(self) -> AgentParent:
        """
        Returns the agent who submitted this order.
        """
        return self._agent

    @property
    def timeTick(self) -> int:
        """
        Returns the simulation time step at which the order was submitted.
        """
        return self._timeTick

    @size.setter
    def size(self, value: int) -> None:
        """
        Set the order quantity.
        Parameters:
            value: New size of the order.
        """
        self._size = value
