from __future__ import annotations

from collections import defaultdict
from typing import Iterable, Sequence, Tuple

from distalgo.algorithms.base import Algorithm
from distalgo.core.models import AlgorithmResult, AlgorithmSpec, ExecutionModel

Edge = Tuple[int, int]


class ConnectedComponents(Algorithm):
    def __init__(self, max_iterations: int = 100):
        self.max_iterations = max_iterations
        self.spec = AlgorithmSpec(
            name="connected_components",
            family="graph.connectivity",
            execution_model=ExecutionModel.GRAPH_MESSAGE,
            communication="neighbor_message",
            checkpoint="iteration",
        )

    def run(self, data: Sequence[Edge], partitions: int) -> AlgorithmResult:
        adjacency = defaultdict(set)
        for src, dst in data:
            adjacency[src].add(dst)
            adjacency[dst].add(src)

        labels = {node: node for node in adjacency}
        iterations = 0
        for iteration in range(1, self.max_iterations + 1):
            changed = False
            next_labels = dict(labels)
            for node, neighbors in adjacency.items():
                candidate = min([labels[node]] + [labels[neighbor] for neighbor in neighbors])
                if candidate < next_labels[node]:
                    next_labels[node] = candidate
                    changed = True
            labels = next_labels
            iterations = iteration
            if not changed:
                break

        return AlgorithmResult(
            algorithm=self.spec.name,
            iterations=iterations,
            converged=iterations < self.max_iterations,
            output={"components": labels},
            metrics={"active_vertices": float(len(labels))},
        )
