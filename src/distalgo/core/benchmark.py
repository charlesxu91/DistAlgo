from __future__ import annotations

from dataclasses import asdict
from time import perf_counter
from typing import Dict, List

from distalgo.core.job import AlgorithmJob, JobRunner
from distalgo.core.runtime import LocalRuntime


class BenchmarkRunner:
    def __init__(self, runner: JobRunner | None = None):
        self.runner = runner or JobRunner(LocalRuntime.in_memory())

    def run_default(self) -> Dict[str, object]:
        jobs = [
            AlgorithmJob("pagerank", [(1, 2), (2, 3), (3, 1), (1, 3)], {"max_iterations": 10}, 2),
            AlgorithmJob("sssp", [(1, 2, 2.0), (2, 3, 1.0), (3, 4, 2.0)], {"source": 1}, 2),
            AlgorithmJob("kmeans", [(0.0, 0.0), (0.1, 0.0), (10.0, 10.0)], {"k": 2}, 2),
        ]
        started = perf_counter()
        results = [self.runner.run(job) for job in jobs]
        elapsed_ms = (perf_counter() - started) * 1000.0
        return {
            "jobs": len(results),
            "algorithms": [result.algorithm for result in results],
            "total_iterations": sum(result.iterations for result in results),
            "elapsed_ms": elapsed_ms,
        }
