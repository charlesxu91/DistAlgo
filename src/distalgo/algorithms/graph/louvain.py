from __future__ import annotations

from collections import defaultdict
from typing import Dict, Sequence, Tuple

from distalgo.algorithms.base import Algorithm
from distalgo.core.models import AlgorithmResult, AlgorithmSpec, ExecutionModel

Edge = Tuple[int, int]


class Louvain(Algorithm):
    """Small deterministic Louvain-style community detection plugin.

    The MVP implementation performs greedy local node moves against modularity.
    It intentionally omits graph coarsening so the behavior stays compact and
    easy to validate before adding a distributed multi-phase implementation.
    """

    def __init__(self, max_passes: int = 20):
        self.max_passes = max_passes
        self.spec = AlgorithmSpec(
            name="louvain",
            family="graph.community",
            execution_model=ExecutionModel.GRAPH_MESSAGE,
            communication="neighbor_message",
            checkpoint="iteration",
        )

    def run(self, data: Sequence[Edge], partitions: int) -> AlgorithmResult:
        adjacency = defaultdict(dict)
        for src, dst in data:
            adjacency[src][dst] = adjacency[src].get(dst, 0.0) + 1.0
            adjacency[dst][src] = adjacency[dst].get(src, 0.0) + 1.0

        nodes = sorted(adjacency)
        communities: Dict[int, int] = {node: node for node in nodes}
        best_modularity = self._modularity(adjacency, communities)
        iterations = 0

        for iteration in range(1, self.max_passes + 1):
            moved = False
            for node in nodes:
                current = communities[node]
                candidate_communities = sorted({communities[neighbor] for neighbor in adjacency[node]} | {current})
                best_for_node = current
                best_for_node_modularity = best_modularity

                for candidate in candidate_communities:
                    if candidate == current:
                        continue
                    trial = dict(communities)
                    trial[node] = candidate
                    score = self._modularity(adjacency, trial)
                    if score > best_for_node_modularity + 1e-12:
                        best_for_node = candidate
                        best_for_node_modularity = score

                if best_for_node != current:
                    communities[node] = best_for_node
                    best_modularity = best_for_node_modularity
                    moved = True

            iterations = iteration
            if not moved:
                break

        normalized = self._normalize_communities(communities)
        return AlgorithmResult(
            algorithm=self.spec.name,
            iterations=iterations,
            converged=iterations < self.max_passes,
            output={"communities": normalized, "modularity": best_modularity},
            metrics={"active_vertices": float(len(nodes)), "edges": float(len(data))},
        )

    def _modularity(self, adjacency, communities: Dict[int, int]) -> float:
        total_edge_weight = sum(sum(neighbors.values()) for neighbors in adjacency.values()) / 2.0
        if total_edge_weight == 0:
            return 0.0

        degrees = {node: sum(neighbors.values()) for node, neighbors in adjacency.items()}
        score = 0.0
        for src, neighbors in adjacency.items():
            for dst, weight in neighbors.items():
                if communities[src] == communities[dst]:
                    score += weight - (degrees[src] * degrees[dst]) / (2.0 * total_edge_weight)
        return score / (2.0 * total_edge_weight)

    @staticmethod
    def _normalize_communities(communities: Dict[int, int]) -> Dict[int, int]:
        remap = {}
        next_id = 0
        normalized = {}
        for node in sorted(communities):
            community = communities[node]
            if community not in remap:
                remap[community] = next_id
                next_id += 1
            normalized[node] = remap[community]
        return normalized
