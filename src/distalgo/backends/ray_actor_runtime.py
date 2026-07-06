from __future__ import annotations

from typing import Any, List, Sequence

from distalgo.algorithms.base import Algorithm
from distalgo.core.checkpoint import MemoryCheckpointStore
from distalgo.core.metrics import MetricsRegistry
from distalgo.core.models import AlgorithmResult
from distalgo.core.partition import EdgePartition, hash_partition_edges
from distalgo.core.partitioned_runtime import PartitionedLocalRuntime


class PartitionWorker:
    def __init__(self, partition: EdgePartition):
        self.partition = partition

    def get_edges(self):
        return list(self.partition.edges)

    def summary(self):
        return {
            "partition_id": self.partition.partition_id,
            "edges": len(self.partition.edges),
            "nodes": len(self.partition.nodes),
            "boundary_edges": len(self.partition.boundary_edges),
        }


class RayActorRuntime:
    """Ray actor-backed partition runtime for graph-shaped jobs.

    Each partition is placed in a worker actor. The current coordinator gathers
    partition edge lists and executes the plugin contract once. This gives the
    project a real Ray actor execution path while preserving deterministic
    algorithm plugins. Future work can move per-superstep compute into
    PartitionWorker methods without changing the public runtime API.
    """

    def __init__(self, ray_module=None, checkpoint_store=None, metrics: MetricsRegistry | None = None):
        self.ray = ray_module or self._import_ray()
        self.local = PartitionedLocalRuntime(
            checkpoint_store=checkpoint_store or MemoryCheckpointStore(),
            metrics=metrics or MetricsRegistry(),
        )
        self._initialized = False

    def run(self, algorithm: Algorithm, data: Sequence[Any], partitions: int = 1) -> AlgorithmResult:
        self._ensure_initialized()
        graph_partitions = hash_partition_edges(data, partitions)
        remote_worker = self.ray.remote(PartitionWorker)
        workers = [remote_worker.remote(partition) for partition in graph_partitions]
        edge_refs = [worker.get_edges.remote() for worker in workers]
        summary_refs = [worker.summary.remote() for worker in workers]
        partition_edges = self.ray.get(edge_refs)
        summaries = self.ray.get(summary_refs)
        merged_edges = [edge for edges in partition_edges for edge in edges]
        result = self.local.run(algorithm, merged_edges, partitions)
        metrics = dict(result.metrics)
        metrics["ray_actors"] = float(len(workers))
        metrics["ray_partition_edges"] = float(sum(item["edges"] for item in summaries))
        return AlgorithmResult(
            algorithm=result.algorithm,
            iterations=result.iterations,
            converged=result.converged,
            output=result.output,
            metrics=metrics,
        )

    def _ensure_initialized(self) -> None:
        if not self._initialized:
            self.ray.init(ignore_reinit_error=True)
            self._initialized = True

    @staticmethod
    def _import_ray():
        try:
            import ray  # type: ignore

            return ray
        except ImportError as exc:
            raise RuntimeError("Ray is not installed. Pass ray_module for tests or install ray.") from exc
