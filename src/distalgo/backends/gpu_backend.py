from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

from distalgo.backends.gpu import GPUProbe, MultiGpuMode


@dataclass(frozen=True)
class DeviceBackend:
    device: str
    library: str
    reason: str


def choose_backend(probe: GPUProbe, preferred: str = "auto") -> DeviceBackend:
    if preferred not in {"auto", "cpu", "gpu"}:
        raise ValueError("preferred must be one of: auto, cpu, gpu")
    if preferred == "cpu" or not probe.has_cuda:
        return DeviceBackend(device="cpu", library="python", reason="CPU backend is available everywhere.")
    return DeviceBackend(
        device="gpu",
        library="rapids-compatible",
        reason="A CUDA device is visible; RAPIDS/cuGraph/cuML kernels can be plugged into this backend.",
    )


def gpu_capability_report(probe: GPUProbe) -> Dict[str, object]:
    return {
        "device_count": probe.device_count,
        "has_cuda": probe.has_cuda,
        "multi_gpu_mode": probe.multi_gpu_mode.value,
        "logical_multi_worker": probe.multi_gpu_mode == MultiGpuMode.LOGICAL_ONLY,
        "true_multi_gpu_validation": probe.multi_gpu_mode == MultiGpuMode.PHYSICAL_MULTI_GPU,
        "note": probe.virtualization_note,
    }
