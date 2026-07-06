from __future__ import annotations

from typing import Any, Sequence

from distalgo.algorithms.base import Algorithm
from distalgo.core.checkpoint import MemoryCheckpointStore
from distalgo.core.metrics import MetricsRegistry
from distalgo.core.models import AlgorithmResult
from distalgo.core.partition import hash_partition_edges
from distalgo.core.runtime import LocalRuntime


class PartitionedLocalRuntime(LocalRuntime):
    @classmethod
    def in_memory(cls) -> "PartitionedLocalRuntime":
        return cls(checkpoint_store=MemoryCheckpointStore(), metrics=MetricsRegistry())

    def run(self, algorithm: Algorithm, data: Sequence[Any], partitions: int = 1) -> AlgorithmResult:
        result = super().run(algorithm, data, partitions)
        partition_metrics = self._partition_metrics(data, partitions)
        merged_metrics = dict(result.metrics)
        merged_metrics.update(partition_metrics)
        return AlgorithmResult(
            algorithm=result.algorithm,
            iterations=result.iterations,
            converged=result.converged,
            output=result.output,
            metrics=merged_metrics,
        )

    def _partition_metrics(self, data: Sequence[Any], partitions: int):
        if not data or not self._looks_like_edge(data[0]):
            return {"partitions": float(partitions), "boundary_edges": 0.0}
        graph_partitions = hash_partition_edges(data, partitions)
        return {
            "partitions": float(partitions),
            "boundary_edges": float(sum(len(part.boundary_edges) for part in graph_partitions)),
        }

    @staticmethod
    def _looks_like_edge(item: Any) -> bool:
        return (
            isinstance(item, tuple)
            and len(item) == 2
            and isinstance(item[0], int)
            and isinstance(item[1], int)
        )
