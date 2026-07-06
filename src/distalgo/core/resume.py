from __future__ import annotations

from typing import Any, Sequence

from distalgo.algorithms.base import Algorithm
from distalgo.core.models import AlgorithmResult


class ResumeRuntime:
    def __init__(self, base_runtime, checkpoint_store):
        self.base_runtime = base_runtime
        self.checkpoint_store = checkpoint_store

    def resume_or_run(
        self,
        algorithm: Algorithm,
        data: Sequence[Any],
        partitions: int,
        iteration: int,
    ) -> AlgorithmResult:
        if self.checkpoint_store.exists(algorithm.spec.name, iteration):
            output = self.checkpoint_store.load(algorithm.spec.name, iteration)
            return AlgorithmResult(
                algorithm=algorithm.spec.name,
                iterations=iteration,
                converged=True,
                output=output,
                metrics={"resumed": 1.0},
            )
        return self.base_runtime.run(algorithm, data, partitions)
