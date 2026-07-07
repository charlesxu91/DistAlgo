from __future__ import annotations

from collections import defaultdict
from typing import Dict, Sequence, Tuple

from distalgo.algorithms.base import Algorithm
from distalgo.backends.accelerated import pagerank_kernel
from distalgo.core.models import AlgorithmResult, AlgorithmSpec, ExecutionModel

Edge = Tuple[int, int]


class PageRank(Algorithm):
    def __init__(
        self,
        damping: float = 0.85,
        max_iterations: int = 50,
        tolerance: float = 1e-8,
        use_gpu: bool = False,
    ):
        self.damping = damping
        self.max_iterations = max_iterations
        self.tolerance = tolerance
        self.use_gpu = use_gpu
        self.spec = AlgorithmSpec(
            name="pagerank",
            family="graph.ranking",
            execution_model=ExecutionModel.GRAPH_MESSAGE,
            communication="neighbor_message",
            checkpoint="iteration",
        )

    def run(self, data: Sequence[Edge], partitions: int) -> AlgorithmResult:
        if self.use_gpu:
            kernel = pagerank_kernel(data, self.damping, self.max_iterations, self.tolerance, prefer_gpu=True)
            return AlgorithmResult(
                algorithm=self.spec.name,
                iterations=int(kernel.metrics.get("iterations", 0.0)),
                converged=bool(kernel.metrics.get("converged", 1.0)),
                output=kernel.output,
                metrics={
                    "active_vertices": kernel.metrics.get("active_vertices", 0.0),
                    "edges": kernel.metrics.get("edges", float(len(data))),
                    "accelerated_backend": 1.0,
                    "gpu_device": 1.0 if kernel.device == "gpu" else 0.0,
                },
            )

        nodes = sorted({node for edge in data for node in edge})
        if not nodes:
            return AlgorithmResult(self.spec.name, 0, True, {"scores": {}}, {})

        outgoing: Dict[int, set[int]] = defaultdict(set)
        incoming: Dict[int, set[int]] = defaultdict(set)
        for src, dst in data:
            outgoing[src].add(dst)
            incoming[dst].add(src)
            outgoing.setdefault(dst, set())
            incoming.setdefault(src, set())

        n = len(nodes)
        scores = {node: 1.0 / n for node in nodes}
        converged = False
        iterations = 0
        for iteration in range(1, self.max_iterations + 1):
            dangling_mass = sum(scores[node] for node in nodes if not outgoing[node]) / n
            next_scores = {}
            for node in nodes:
                rank = (1.0 - self.damping) / n
                rank += self.damping * dangling_mass
                rank += self.damping * sum(
                    scores[src] / len(outgoing[src]) for src in incoming[node] if outgoing[src]
                )
                next_scores[node] = rank
            delta = sum(abs(next_scores[node] - scores[node]) for node in nodes)
            scores = next_scores
            iterations = iteration
            if delta <= self.tolerance:
                converged = True
                break

        total = sum(scores.values())
        if total:
            scores = {node: value / total for node, value in scores.items()}

        return AlgorithmResult(
            algorithm=self.spec.name,
            iterations=iterations,
            converged=converged,
            output={"scores": scores},
            metrics={"active_vertices": float(n), "edges": float(len(data))},
        )
