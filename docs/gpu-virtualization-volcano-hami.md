# Volcano vGPU + HAMi GPU Virtualization

This document records the DistAlgo decision on Volcano + HAMi after reviewing
the remote K3s validation and the supplied field article screenshots.

## Recommendation

Volcano vGPU + HAMi-core is a viable optional GPU virtualization path for
DistAlgo. It should be treated as an advanced cloud-native scheduler profile,
not as the default MVP path.

The default DistAlgo remote GPU path remains:

```text
K3s + NVIDIA device plugin time-slicing + KubeRay + Ray GPU resources
```

The advanced queue/gang/vGPU path is:

```text
Kubernetes/K3s
  + Volcano Scheduler
  + Volcano deviceshare plugin
  + volcano-vgpu-device-plugin
  + HAMi-core
```

This path is useful when a deployment needs all of these at the same time:

- one physical GPU split into multiple vGPU shares;
- per-container GPU memory and core limits;
- multi-worker gang scheduling for graph/ML jobs;
- queue-level GPU quotas for teams or tenants;
- Kubernetes-native batch semantics through `VolcanoJob` and `PodGroup`.

## Resource Names

Do not mix the two resource APIs.

| Route | Scheduler | Resource names |
| --- | --- | --- |
| NVIDIA device plugin / time-slicing | default Kubernetes or KubeRay | `nvidia.com/gpu` |
| Ordinary HAMi | HAMi scheduler/webhook/device plugin | `nvidia.com/gpu`, `nvidia.com/gpumem`, `nvidia.com/gpucores` |
| Volcano vGPU + HAMi-core | Volcano scheduler + deviceshare | `volcano.sh/vgpu-number`, `volcano.sh/vgpu-memory`, `volcano.sh/vgpu-cores` |

For the Volcano vGPU route, Pods and VolcanoJobs must use:

```yaml
schedulerName: volcano
resources:
  limits:
    volcano.sh/vgpu-number: 1
    volcano.sh/vgpu-memory: 2000
    volcano.sh/vgpu-cores: 30
```

The node must expose matching resources such as:

```text
volcano.sh/vgpu-number
volcano.sh/vgpu-memory
volcano.sh/vgpu-cores
```

`volcano.sh/vgpu-number` is a logical vGPU share count, not a physical GPU
count.

## DistAlgo Integration Model

DistAlgo should model GPU scheduling as a runtime profile rather than hard-code
one Kubernetes resource name into algorithms.

Proposed job-level accelerator contract:

```yaml
accelerator:
  profile: nvidia_timeslicing | volcano_vgpu
  gpu_count: 1
  gpu_memory_mib: 2000
  gpu_cores_percent: 30
  scheduler_name: volcano
  queue: gpu-small-queue
  gang_min_available: 2
```

Adapter behavior:

| Profile | Runtime mapping |
| --- | --- |
| `nvidia_timeslicing` | emit `nvidia.com/gpu` requests/limits; suitable for current K3s + KubeRay smoke tests |
| `volcano_vgpu` | emit `schedulerName: volcano`, `volcano.sh/vgpu-*`, optional `queue`, and optional `minAvailable` |

Algorithm code should not import Volcano, HAMi, or Kubernetes APIs. The runtime
adapter owns those manifests.

## Validation Checklist

The Volcano vGPU profile is not considered validated until these checks pass on
the target cluster:

1. Volcano scheduler is running and the `deviceshare` plugin has
   `deviceshare.VGPUEnable: true`.
2. The volcano vGPU device plugin registers `volcano.sh/vgpu-*` resources on
   the GPU node.
3. A single Pod with `schedulerName: volcano` and `volcano.sh/vgpu-*` limits can
   run `nvidia-smi`.
4. The container sees HAMi-core injected limits such as
   `CUDA_DEVICE_MEMORY_LIMIT_0` and `CUDA_DEVICE_SM_LIMIT`.
5. A VolcanoJob with `minAvailable: 2` and two GPU workers enters `Running`
   only when both workers can be scheduled.
6. An intentionally oversized VolcanoJob remains `Inqueue` / `Pending` with
   `NotEnoughResources` instead of launching only part of the gang.
7. A Queue with `capability` limits accepts jobs inside the quota and holds jobs
   outside the quota.

## Known Pitfalls

- Do not deploy multiple GPU device plugins on the same node unless the
  interaction is intentional and tested. NVIDIA device plugin, ordinary HAMi
  device plugin, and Volcano vGPU device plugin can register different resources
  and confuse scheduling assumptions.
- `NotEnoughResources` with a PodGroup in `Inqueue` can be correct gang
  scheduling behavior, not a failure.
- Queue `capability` is a queue-level upper bound. It does not replace
  `resources.limits` on the Pod or VolcanoJob.
- `schedulerName: volcano` is required for Volcano-managed Pods and jobs.
- Resource names in YAML must match the names actually registered on the node.

## Current Project Status

- Validated on 2026-07-07: K3s + NVIDIA device plugin time-slicing + KubeRay
  + Ray fractional GPU task scheduling on the remote RTX 5090 host.
- Implemented in repository: Volcano vGPU example manifests plus
  `scripts/remote_volcano_vgpu_preflight.sh` and
  `scripts/remote_volcano_vgpu_smoke.sh`.
- Validation rule: run the smoke script only after the cluster intentionally
  switches to a Volcano vGPU/HAMi-core GPU plugin profile and the node exposes
  `volcano.sh/vgpu-number`, `volcano.sh/vgpu-memory`, and
  `volcano.sh/vgpu-cores`. The preflight script keeps this check
  non-destructive for the current NVIDIA device-plugin time-slicing profile.

## Sources

- HAMi project: https://github.com/Project-HAMi/HAMi
- HAMi documentation: https://project-hami.io/docs/
- Volcano project: https://github.com/volcano-sh/volcano
- Volcano documentation: https://volcano.sh/en/docs/
- Supplied field article screenshots:
  `HAMi + Volcano vGPU 实战：单卡 GPU 共享、Gang Scheduling 与 Queue 资源限制验证`
