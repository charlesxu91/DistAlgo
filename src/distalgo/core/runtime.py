from __future__ import annotations

from typing import Any, Sequence

from distalgo.algorithms.base import Algorithm
from distalgo.core.checkpoint import MemoryCheckpointStore
from distalgo.core.metrics import MetricsRegistry
from distalgo.core.models import AlgorithmResult


class LocalRuntime:
    def __init__(self, checkpoint_store=None, metrics: MetricsRegistry | None = None):
        self.checkpoint_store = checkpoint_store or MemoryCheckpointStore()
        self.metrics = metrics or MetricsRegistry()

    @classmethod
    def in_memory(cls) -> "LocalRuntime":
        return cls()

    def run(self, algorithm: Algorithm, data: Sequence[Any], partitions: int = 1) -> AlgorithmResult:
        if partitions <= 0:
            raise ValueError("partitions must be positive")
        result = algorithm.run(data, partitions)
        self.checkpoint_store.save(result.algorithm, result.iterations, result.output)
        labels = {"algorithm": result.algorithm, "model": algorithm.spec.execution_model.value}
        self.metrics.increment("distalgo_iterations_total", result.iterations, labels)
        self.metrics.increment("distalgo_jobs_total", 1, labels)
        for metric_name, value in result.metrics.items():
            self.metrics.set_gauge(f"distalgo_{metric_name}", value, {"algorithm": result.algorithm})
        return result
