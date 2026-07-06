from __future__ import annotations

from collections import defaultdict
from typing import Sequence, Tuple

from distalgo.algorithms.base import Algorithm
from distalgo.core.models import AlgorithmResult, AlgorithmSpec, ExecutionModel

Edge = Tuple[int, int]


class KCore(Algorithm):
    def __init__(self, k: int):
        if k < 0:
            raise ValueError("k must be non-negative")
        self.k = k
        self.spec = AlgorithmSpec(
            name="k_core",
            family="graph.community",
            execution_model=ExecutionModel.GRAPH_MESSAGE,
            communication="neighbor_message",
            checkpoint="final",
        )

    def run(self, data: Sequence[Edge], partitions: int) -> AlgorithmResult:
        adjacency = defaultdict(set)
        for src, dst in data:
            adjacency[src].add(dst)
            adjacency[dst].add(src)

        remaining = set(adjacency)
        changed = True
        iterations = 0
        while changed:
            changed = False
            iterations += 1
            to_remove = [
                node
                for node in remaining
                if sum(1 for neighbor in adjacency[node] if neighbor in remaining) < self.k
            ]
            if to_remove:
                changed = True
                remaining.difference_update(to_remove)

        return AlgorithmResult(
            algorithm=self.spec.name,
            iterations=iterations,
            converged=True,
            output={"nodes": sorted(remaining)},
            metrics={"active_vertices": float(len(remaining))},
        )
