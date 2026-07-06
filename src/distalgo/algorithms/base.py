from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Sequence

from distalgo.core.models import AlgorithmResult, AlgorithmSpec


class Algorithm(ABC):
    """Base interface implemented by graph and ML algorithm plugins."""

    spec: AlgorithmSpec

    @abstractmethod
    def run(self, data: Sequence[Any], partitions: int) -> AlgorithmResult:
        raise NotImplementedError
