from __future__ import annotations

from collections import defaultdict, deque
from typing import Dict, List, Sequence, Tuple

from distalgo.algorithms.base import Algorithm
from distalgo.core.models import AlgorithmResult, AlgorithmSpec, ExecutionModel

Edge = Tuple[int, int]


class KHop(Algorithm):
    def __init__(self, sources: Sequence[int], hops: int):
        if hops < 0:
            raise ValueError("hops must be non-negative")
        self.sources = list(sources)
        self.hops = hops
        self.spec = AlgorithmSpec(
            name="k_hop",
            family="graph.neighborhood",
            execution_model=ExecutionModel.GRAPH_MESSAGE,
            communication="neighbor_message",
            checkpoint="final",
        )

    def run(self, data: Sequence[Edge], partitions: int) -> AlgorithmResult:
        adjacency = defaultdict(list)
        for src, dst in data:
            adjacency[src].append(dst)

        neighborhoods: Dict[int, List[int]] = {}
        for source in self.sources:
            seen = {source}
            queue = deque([(source, 0)])
            while queue:
                node, depth = queue.popleft()
                if depth == self.hops:
                    continue
                for neighbor in adjacency.get(node, []):
                    if neighbor not in seen:
                        seen.add(neighbor)
                        queue.append((neighbor, depth + 1))
            neighborhoods[source] = sorted(seen - {source})

        return AlgorithmResult(
            algorithm=self.spec.name,
            iterations=self.hops,
            converged=True,
            output={"neighbors": neighborhoods},
            metrics={"sources": float(len(self.sources))},
        )
