from __future__ import annotations

from typing import Any, Sequence

from distalgo.algorithms.base import Algorithm
from distalgo.core.checkpoint import MemoryCheckpointStore
from distalgo.core.metrics import MetricsRegistry
from distalgo.core.models import AlgorithmResult
from distalgo.core.runtime import LocalRuntime


class RayRuntime:
    """Ray runtime adapter with optional dependency injection for tests.

    This MVP adapter initializes Ray and preserves the same algorithm contract as
    LocalRuntime. The next implementation step is to split algorithms into
    remote partition actors; keeping the adapter boundary now prevents algorithm
    plugins from importing Ray directly.
    """

    def __init__(self, ray_module=None, checkpoint_store=None, metrics: MetricsRegistry | None = None):
        self.ray = ray_module or self._import_ray()
        self.local = LocalRuntime(
            checkpoint_store=checkpoint_store or MemoryCheckpointStore(),
            metrics=metrics or MetricsRegistry(),
        )
        self._initialized = False

    def run(self, algorithm: Algorithm, data: Sequence[Any], partitions: int = 1) -> AlgorithmResult:
        self._ensure_initialized()
        return self.local.run(algorithm, data, partitions)

    @property
    def metrics(self) -> MetricsRegistry:
        return self.local.metrics

    def shutdown(self) -> None:
        if self._initialized and hasattr(self.ray, "shutdown"):
            self.ray.shutdown()
        self._initialized = False

    def _ensure_initialized(self) -> None:
        if not self._initialized and hasattr(self.ray, "init"):
            self.ray.init(ignore_reinit_error=True)
            self._initialized = True

    @staticmethod
    def _import_ray():
        try:
            import ray  # type: ignore

            return ray
        except ImportError as exc:
            raise RuntimeError(
                "Ray is not installed. Install ray or pass an injected ray_module for tests."
            ) from exc
