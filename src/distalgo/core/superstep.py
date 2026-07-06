from __future__ import annotations

from typing import Any, Sequence

from distalgo.algorithms.base import Algorithm
from distalgo.core.models import AlgorithmResult
from distalgo.core.partition import EdgePartition


class PregelRuntime:
    """BSP/Pregel-style runtime facade for graph-message algorithms.

    The MVP delegates algorithm semantics to plugins while adding superstep and
    partition metrics. Algorithms such as SSSP expose message counts and
    iteration counts; future plugins can move vertex-program callbacks here.
    """

    def run(self, algorithm: Algorithm, data: Sequence[Any], partitions: int = 1) -> AlgorithmResult:
        result = algorithm.run(data, partitions)
        metrics = dict(result.metrics)
        metrics["partitions"] = float(partitions)
        metrics.setdefault("supersteps", float(result.iterations))
        metrics.setdefault("messages_sent", 0.0)
        return AlgorithmResult(
            algorithm=result.algorithm,
            iterations=result.iterations,
            converged=result.converged,
            output=result.output,
            metrics=metrics,
        )
