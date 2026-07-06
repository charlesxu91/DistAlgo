from __future__ import annotations

from collections import defaultdict
from typing import Sequence, Tuple

from distalgo.algorithms.base import Algorithm
from distalgo.core.models import AlgorithmResult, AlgorithmSpec, ExecutionModel

Edge = Tuple[int, int]


class TriangleCount(Algorithm):
    def __init__(self):
        self.spec = AlgorithmSpec(
            name="triangle_count",
            family="graph.mining",
            execution_model=ExecutionModel.MAP_REDUCE_SHUFFLE,
            communication="shuffle",
            checkpoint="final",
        )

    def run(self, data: Sequence[Edge], partitions: int) -> AlgorithmResult:
        adjacency = defaultdict(set)
        for src, dst in data:
            if src == dst:
                continue
            adjacency[src].add(dst)
            adjacency[dst].add(src)

        count = 0
        nodes = sorted(adjacency)
        for index, a in enumerate(nodes):
            for b in nodes[index + 1 :]:
                if b not in adjacency[a]:
                    continue
                for c in nodes:
                    if c <= b:
                        continue
                    if c in adjacency[a] and c in adjacency[b]:
                        count += 1

        return AlgorithmResult(
            algorithm=self.spec.name,
            iterations=1,
            converged=True,
            output={"triangle_count": count},
            metrics={"active_vertices": float(len(nodes)), "triangles": float(count)},
        )
