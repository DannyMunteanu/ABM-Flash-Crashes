import mesa
from typing import Any, cast


class MesaAgentWrapper(mesa.Agent):
    """
    Wraps a standard agent for use in a Mesa simulation.
    Delegates the step execution to the inner agent while providing access to the simulation model.
    """

    def __init__(self, model: mesa.Model, inner: Any) -> None:
        """
        Initialise the MesaAgentWrapper.
        Parameters:
            model: The Mesa simulation model instance.
            inner: The actual agent instance to wrap.
        """
        super().__init__(model)
        self.inner = inner

    def step(self) -> None:
        """
        Executes a single simulation step for the wrapped agent.
        Delegates the step call to the inner agent with the market, order book, and current simulation tick.
        """
        model = cast("FlashCrashModel", self.model)
        self.inner.step(model.market, model.limitOrderBook, model.timeTick)
