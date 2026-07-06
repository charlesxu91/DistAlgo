from __future__ import annotations

from collections import defaultdict, deque
from typing import Sequence, Tuple

from distalgo.algorithms.base import Algorithm
from distalgo.core.models import AlgorithmResult, AlgorithmSpec, ExecutionModel

Edge = Tuple[int, int]


class BFS(Algorithm):
    def __init__(self, source: int):
        self.source = source
        self.spec = AlgorithmSpec(
            name="bfs",
            family="graph.traversal",
            execution_model=ExecutionModel.GRAPH_MESSAGE,
            communication="neighbor_message",
            checkpoint="final",
        )

    def run(self, data: Sequence[Edge], partitions: int) -> AlgorithmResult:
        adjacency = defaultdict(list)
        nodes = set()
        for src, dst in data:
            adjacency[src].append(dst)
            adjacency[dst].append(src)
            nodes.update((src, dst))

        distances = {self.source: 0}
        queue = deque([self.source])
        while queue:
            node = queue.popleft()
            for neighbor in sorted(adjacency[node]):
                if neighbor not in distances:
                    distances[neighbor] = distances[node] + 1
                    queue.append(neighbor)

        return AlgorithmResult(
            algorithm=self.spec.name,
            iterations=max(distances.values()) if distances else 0,
            converged=True,
            output={"distances": distances},
            metrics={"active_vertices": float(len(nodes))},
        )
