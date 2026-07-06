from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class RayResourcePlan:
    cpus: int = 1
    gpus: float = 0
    memory_mb: int = 0

    def to_ray_options(self) -> Dict[str, float]:
        options: Dict[str, float] = {"num_cpus": self.cpus}
        if self.gpus:
            options["num_gpus"] = self.gpus
        return options

    def to_kubernetes_limits(self) -> Dict[str, str]:
        limits = {"cpu": str(self.cpus)}
        if self.memory_mb:
            limits["memory"] = f"{self.memory_mb}Mi"
        if self.gpus:
            limits["nvidia.com/gpu"] = str(int(self.gpus)) if self.gpus == int(self.gpus) else str(self.gpus)
        return limits
