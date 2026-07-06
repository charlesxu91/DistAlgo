from __future__ import annotations

from collections import defaultdict
from typing import Dict, Sequence, Tuple

from distalgo.algorithms.base import Algorithm
from distalgo.core.models import AlgorithmResult, AlgorithmSpec, ExecutionModel

WeightedEdge = Tuple[int, int, float]


class SSSP(Algorithm):
    def __init__(self, source: int, max_iterations: int = 100):
        self.source = source
        self.max_iterations = max_iterations
        self.spec = AlgorithmSpec(
            name="sssp",
            family="graph.traversal",
            execution_model=ExecutionModel.GRAPH_MESSAGE,
            communication="neighbor_message",
            checkpoint="iteration",
        )

    def run(self, data: Sequence[WeightedEdge], partitions: int) -> AlgorithmResult:
        adjacency = defaultdict(list)
        nodes = {self.source}
        for src, dst, weight in data:
            adjacency[src].append((dst, float(weight)))
            nodes.update((src, dst))

        distances: Dict[int, float] = {node: float("inf") for node in nodes}
        distances[self.source] = 0.0
        active = {self.source: 0.0}
        messages_sent = 0
        iterations = 0

        for iteration in range(1, self.max_iterations + 1):
            next_active: Dict[int, float] = {}
            for node, distance in active.items():
                for neighbor, weight in adjacency.get(node, []):
                    candidate = distance + weight
                    messages_sent += 1
                    if candidate < distances.get(neighbor, float("inf")):
                        distances[neighbor] = candidate
                        if candidate < next_active.get(neighbor, float("inf")):
                            next_active[neighbor] = candidate
            iterations = iteration
            active = next_active
            if not active:
                break

        return AlgorithmResult(
            algorithm=self.spec.name,
            iterations=iterations,
            converged=not active,
            output={"distances": distances},
            metrics={
                "active_vertices": float(len(nodes)),
                "messages_sent": float(messages_sent),
            },
        )
