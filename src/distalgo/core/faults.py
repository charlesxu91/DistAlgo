from __future__ import annotations

from typing import Any, Sequence

from distalgo.algorithms.base import Algorithm
from distalgo.core.models import AlgorithmResult


class InjectedFault(RuntimeError):
    pass


class KillOnceFault:
    def __init__(self, message: str):
        self.message = message
        self.triggered = False

    def maybe_raise(self) -> None:
        if not self.triggered:
            self.triggered = True
            raise InjectedFault(self.message)


class FaultInjectingRuntime:
    def __init__(self, base_runtime, checkpoint_store, fault: KillOnceFault):
        self.base_runtime = base_runtime
        self.checkpoint_store = checkpoint_store
        self.fault = fault

    def run_with_recovery(self, algorithm: Algorithm, data: Sequence[Any], partitions: int) -> AlgorithmResult:
        retries = 0
        try:
            self.fault.maybe_raise()
            result = self.base_runtime.run(algorithm, data, partitions)
        except InjectedFault:
            retries += 1
            result = self.base_runtime.run(algorithm, data, partitions)
        metrics = dict(result.metrics)
        metrics["retries"] = float(retries)
        return AlgorithmResult(
            algorithm=result.algorithm,
            iterations=result.iterations,
            converged=result.converged,
            output=result.output,
            metrics=metrics,
        )
