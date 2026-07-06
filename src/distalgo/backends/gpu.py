from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Mapping, Optional, Sequence


class MultiGpuMode(str, Enum):
    UNAVAILABLE = "unavailable"
    LOGICAL_ONLY = "logical_only"
    PHYSICAL_MULTI_GPU = "physical_multi_gpu"


@dataclass(frozen=True)
class GPUProbe:
    device_names: Sequence[str]
    env: Mapping[str, str]

    @classmethod
    def from_environment(cls, env: Optional[Mapping[str, str]] = None) -> "GPUProbe":
        environment = dict(env or {})
        visible = environment.get("CUDA_VISIBLE_DEVICES")
        if not visible:
            return cls(device_names=[], env=environment)
        devices = [item.strip() for item in visible.split(",") if item.strip()]
        return cls(device_names=[f"cuda:{device}" for device in devices], env=environment)

    @property
    def device_count(self) -> int:
        return len(self.device_names)

    @property
    def has_cuda(self) -> bool:
        return self.device_count > 0

    @property
    def multi_gpu_mode(self) -> MultiGpuMode:
        if self.device_count == 0:
            return MultiGpuMode.UNAVAILABLE
        if self.device_count == 1:
            return MultiGpuMode.LOGICAL_ONLY
        return MultiGpuMode.PHYSICAL_MULTI_GPU

    @property
    def virtualization_note(self) -> str:
        if self.multi_gpu_mode == MultiGpuMode.PHYSICAL_MULTI_GPU:
            return "Multiple visible CUDA devices can validate multi-GPU placement and collective communication."
        if self.multi_gpu_mode == MultiGpuMode.LOGICAL_ONLY:
            return "One physical GPU can validate multi-worker scheduling with fractional GPU resources, not true NCCL multi-GPU behavior."
        return "No CUDA devices are visible; only CPU execution can be validated."
