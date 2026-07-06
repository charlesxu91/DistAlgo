from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, List

from distalgo.algorithms.base import Algorithm
from distalgo.algorithms.graph.bfs import BFS
from distalgo.algorithms.graph.connected_components import ConnectedComponents
from distalgo.algorithms.graph.k_hop import KHop
from distalgo.algorithms.graph.k_core import KCore
from distalgo.algorithms.graph.label_propagation import LabelPropagation
from distalgo.algorithms.graph.louvain import Louvain
from distalgo.algorithms.graph.pagerank import PageRank
from distalgo.algorithms.graph.sssp import SSSP
from distalgo.algorithms.graph.triangle_count import TriangleCount
from distalgo.algorithms.ml.kmeans import KMeans
from distalgo.algorithms.ml.linear_regression import LinearRegression


AlgorithmFactory = Callable[..., Algorithm]


@dataclass(frozen=True)
class AlgorithmMetadata:
    name: str
    display_name: str
    category: str
    status: str
    distributed_verified: bool
    verification_level: str
    evidence: str
    notes: str = ""


class AlgorithmRegistry:
    def __init__(self):
        self._factories: Dict[str, AlgorithmFactory] = {}
        self._metadata: Dict[str, AlgorithmMetadata] = {}

    @classmethod
    def default(cls) -> "AlgorithmRegistry":
        registry = cls()
        registry.register(
            "pagerank",
            PageRank,
            AlgorithmMetadata(
                "pagerank",
                "PageRank",
                "graph",
                "distributed_verified",
                True,
                "partitioned_local",
                "tests/test_distributed_algorithms.py",
            ),
        )
        registry.register(
            "sssp",
            SSSP,
            AlgorithmMetadata(
                "sssp",
                "Single-Source Shortest Path",
                "graph",
                "distributed_verified",
                True,
                "pregel_runtime",
                "tests/test_distributed_completion.py",
            ),
        )
        registry.register(
            "bfs",
            BFS,
            AlgorithmMetadata(
                "bfs",
                "Breadth-First Search",
                "graph",
                "distributed_verified",
                True,
                "partitioned_local + ray_actor_adapter",
                "tests/test_project_completion.py; tests/test_ray_actor_runtime.py",
            ),
        )
        registry.register(
            "connected_components",
            ConnectedComponents,
            AlgorithmMetadata(
                "connected_components",
                "Connected Components",
                "graph",
                "distributed_verified",
                True,
                "partitioned_local",
                "tests/test_distributed_algorithms.py",
            ),
        )
        registry.register(
            "k_hop",
            KHop,
            AlgorithmMetadata(
                "k_hop",
                "K-Hop Neighborhood",
                "graph",
                "distributed_verified",
                True,
                "partitioned_local",
                "tests/test_distributed_algorithms.py",
            ),
        )
        registry.register(
            "k_core",
            KCore,
            AlgorithmMetadata(
                "k_core",
                "K-Core",
                "graph",
                "distributed_verified",
                True,
                "partitioned_local",
                "tests/test_project_completion.py",
            ),
        )
        registry.register(
            "label_propagation",
            LabelPropagation,
            AlgorithmMetadata(
                "label_propagation",
                "Label Propagation",
                "graph",
                "distributed_verified",
                True,
                "partitioned_local",
                "tests/test_project_completion.py",
            ),
        )
        registry.register(
            "louvain",
            Louvain,
            AlgorithmMetadata(
                "louvain",
                "Louvain Community Detection",
                "graph",
                "distributed_verified",
                True,
                "partitioned_local",
                "tests/test_distributed_algorithms.py",
            ),
        )
        registry.register(
            "triangle_count",
            TriangleCount,
            AlgorithmMetadata(
                "triangle_count",
                "Triangle Count",
                "graph",
                "distributed_verified",
                True,
                "partitioned_local",
                "tests/test_project_completion.py",
            ),
        )
        registry.register(
            "kmeans",
            KMeans,
            AlgorithmMetadata(
                "kmeans",
                "K-Means",
                "machine_learning",
                "distributed_verified",
                True,
                "partitioned_local",
                "tests/test_distributed_algorithms.py",
            ),
        )
        registry.register(
            "linear_regression",
            LinearRegression,
            AlgorithmMetadata(
                "linear_regression",
                "Linear Regression",
                "machine_learning",
                "distributed_verified",
                True,
                "partitioned_local",
                "tests/test_project_completion.py",
            ),
        )
        return registry

    def register(self, name: str, factory: AlgorithmFactory, metadata: AlgorithmMetadata | None = None) -> None:
        self._factories[name] = factory
        self._metadata[name] = metadata or AlgorithmMetadata(
            name=name,
            display_name=name,
            category="unknown",
            status="local_verified",
            distributed_verified=False,
            verification_level="local_runtime",
            evidence="custom registration",
        )

    def create(self, name: str, params: Dict[str, Any] | None = None) -> Algorithm:
        if name not in self._factories:
            available = ", ".join(sorted(self._factories))
            raise KeyError(f"unknown algorithm {name!r}; available: {available}")
        return self._factories[name](**(params or {}))

    def names(self):
        return sorted(self._factories)

    def metadata(self, name: str) -> AlgorithmMetadata:
        if name not in self._metadata:
            available = ", ".join(sorted(self._metadata))
            raise KeyError(f"unknown algorithm metadata {name!r}; available: {available}")
        return self._metadata[name]

    def metadata_all(self) -> List[AlgorithmMetadata]:
        return [self._metadata[name] for name in self.names()]
