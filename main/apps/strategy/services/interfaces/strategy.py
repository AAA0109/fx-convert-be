from abc import ABC, abstractmethod
from typing import List, Tuple


class HedgingStrategyInterface(ABC):
    @abstractmethod
    def get_positions_to_hedge(self) -> List[Tuple[str, float]]:
        """
        Returns a list of tuples representing instruments and their corresponding positions to hedge.

        Returns:
            List of tuples where each tuple contains:
                - Instrument identifier (e.g., symbol or name)
                - Position to hedge (e.g., quantity or exposure)
        """
        raise NotImplementedError("Method get_positions_to_hedge must be implemented by concrete subclass.")

    @abstractmethod
    def calculate_hedging_cost(self) -> float:
        """
        Calculates the cost associated with executing the hedging strategy.

        Returns:
            The total cost of executing the hedging strategy.
        """
        raise NotImplementedError("Method calculate_hedging_cost must be implemented by concrete subclass.")
