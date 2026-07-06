from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Sequence, Set, Tuple

Edge = Tuple[int, int]


@dataclass(frozen=True)
class EdgePartition:
    partition_id: int
    edges: List[Edge]
    nodes: Set[int]
    boundary_edges: List[Edge]


def hash_partition_edges(edges: Sequence[Edge], partitions: int) -> List[EdgePartition]:
    if partitions <= 0:
        raise ValueError("partitions must be positive")
    buckets: List[List[Edge]] = [[] for _ in range(partitions)]
    for src, dst in edges:
        buckets[min(src, dst) % partitions].append((src, dst))

    result = []
    for partition_id, bucket in enumerate(buckets):
        nodes = {node for edge in bucket for node in edge}
        boundary = [
            edge
            for edge in bucket
            if (edge[0] % partitions) != (edge[1] % partitions)
        ]
        result.append(EdgePartition(partition_id=partition_id, edges=bucket, nodes=nodes, boundary_edges=boundary))
    return result
