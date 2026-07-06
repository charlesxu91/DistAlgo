from __future__ import annotations

from collections import Counter, defaultdict
from typing import Sequence, Tuple

from distalgo.algorithms.base import Algorithm
from distalgo.core.models import AlgorithmResult, AlgorithmSpec, ExecutionModel

Edge = Tuple[int, int]


class LabelPropagation(Algorithm):
    def __init__(self, max_iterations: int = 50):
        self.max_iterations = max_iterations
        self.spec = AlgorithmSpec(
            name="label_propagation",
            family="graph.community",
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
            for node in sorted(adjacency):
                counts = Counter(labels[neighbor] for neighbor in adjacency[node])
                if not counts:
                    continue
                best_count = max(counts.values())
                best_label = min(label for label, count in counts.items() if count == best_count)
                if best_label != labels[node]:
                    labels[node] = best_label
                    changed = True
            iterations = iteration
            if not changed:
                break

        return AlgorithmResult(
            algorithm=self.spec.name,
            iterations=iterations,
            converged=iterations < self.max_iterations,
            output={"labels": labels},
            metrics={"active_vertices": float(len(labels))},
        )
