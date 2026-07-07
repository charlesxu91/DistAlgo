# GPU Validation

The target GPU validation host is expected to have one RTX 5090 with 32 GB VRAM.
That machine is useful for validating GPU-aware execution, but it cannot validate
true physical multi-GPU behavior by itself.

## What One 5090 Can Validate

- CUDA visibility.
- GPU worker placement declarations.
- Ray task or actor resource options such as `num_gpus=1`.
- Logical multi-worker scheduling with fractional GPU requests.
- Single-GPU RAPIDS, CuPy, PyTorch, or cuGraph backend smoke tests.
- GPU metrics export through DCGM in a K8s deployment.
- Kubernetes GPU resource advertisement with NVIDIA device-plugin time-slicing.
- KubeRay scheduling on a GPU-capable cloud-native node.

## What One 5090 Cannot Validate

- True multi-GPU NCCL collectives.
- Cross-device allreduce.
- Multi-node GPU topology.
- NVLink or PCIe multi-GPU behavior.
- GPU sharding correctness across physical devices.

## Virtual Multi-GPU Boundary

There are two different ideas that often get mixed together:

`Logical multi-worker on one GPU`
: Multiple workers share one physical GPU. Ray can model this with fractional
GPU resources. This validates scheduling and isolation assumptions, but not
multi-GPU algorithms.

`Physical multi-GPU`
: Two or more visible CUDA devices participate in communication or data
parallelism. This is required for NCCL, UCX, and real allreduce validation.

The `GPUProbe` helper reports this distinction:

```bash
CUDA_VISIBLE_DEVICES=0 python3 scripts/probe_gpu.py
```

When `CUDA_VISIBLE_DEVICES` is not set, the helper also attempts to read real
device names from `nvidia-smi`. This keeps the local probe useful on normal CUDA
hosts where the driver exposes devices without an explicit environment filter.

Expected mode on one GPU:

```text
multi_gpu_mode=logical_only
```

The MVP does not require a remote GPU to pass the local test suite. Remote GPU
validation should be a smoke check for `scripts/probe_gpu.py`, Ray resource
declarations, and later GPU kernels. True multi-GPU validation must wait for a
host with multiple physical CUDA devices.

`distalgo.backends.gpu_backend` now exposes a dependency-free backend selector.
It chooses the CPU backend when CUDA is absent and a RAPIDS-compatible backend
when a CUDA device is visible. This is an integration seam, not a substitute for
real cuGraph/cuML kernels.

## Remote K3s Validation Runbook

The remote RTX 5090 host uses K3s as the single-node cloud-native substrate.
K3s is sufficient for this MVP because the product boundary is algorithm
execution on Kubernetes, not the Kubernetes distribution itself.

Bootstrap or repair the remote substrate:

```bash
ssh charles@192.168.124.8 'bash -s' < scripts/install_remote_kuberay.sh
ssh charles@192.168.124.8 'bash -s' < scripts/fix_remote_k3s_kuberay.sh
```

If image pulls are slow or blocked inside K3s, pull with Docker first and import
the image into K3s containerd:

```bash
ssh charles@192.168.124.8 'bash -s -- rayproject/ray:2.9.0' < scripts/import_remote_image_to_k3s.sh
ssh charles@192.168.124.8 'bash -s -- nvidia/cuda:12.4.1-base-ubuntu22.04' < scripts/import_remote_image_to_k3s.sh
```

Collect a remote status snapshot:

```bash
ssh charles@192.168.124.8 'bash -s' < scripts/remote_cluster_status.sh
```

Run the GPU scheduling smoke test:

```bash
ssh charles@192.168.124.8 'bash -s' < scripts/remote_gpu_ray_smoke.sh
```

This script validates three separate layers:

1. `nvidia-smi` sees the physical RTX 5090 on the host.
2. A Kubernetes pod with `nvidia.com/gpu: 1` can run `nvidia-smi`.
3. A KubeRay RayCluster with a GPU worker can run Ray tasks declared with
   `@ray.remote(num_gpus=0.25)`.

Passing this script proves GPU resource scheduling and Ray GPU assignment. It
still does not prove that DistAlgo graph/ML kernels use CUDA internally.

Expected K3s GPU signal after NVIDIA device-plugin time-slicing:

```text
GPU_ALLOCATABLE   GPU_CAPACITY
4                 4
```

This is four logical Kubernetes GPU slots backed by one physical RTX 5090. It is
valid for scheduling tests, but it is not evidence of four physical devices.

## Optional Volcano vGPU + HAMi-core Path

When DistAlgo needs queue-level GPU quotas, gang scheduling, and per-container
GPU memory/core limits, use the optional Volcano vGPU profile instead of the
default NVIDIA time-slicing profile.

Key difference:

```text
default path:  nvidia.com/gpu
Volcano path: volcano.sh/vgpu-number, volcano.sh/vgpu-memory, volcano.sh/vgpu-cores
```

The Volcano path also requires `schedulerName: volcano` and a running Volcano
scheduler with the `deviceshare` plugin enabled. See
[Volcano vGPU + HAMi GPU virtualization](gpu-virtualization-volcano-hami.md) and
the sample manifests in `deploy/volcano-vgpu/`.

## Recommended Roadmap

Phase 1:

- Keep algorithms CPU deterministic.
- Add GPU resource specs to job declarations.
- Validate local runtime and Ray resource planning.

Phase 2:

- Add optional GPU kernels for KMeans and selected graph primitives.
- Use single-GPU RAPIDS or CuPy smoke tests on the 5090 host.

Phase 3:

- Add multi-GPU tests only when at least two physical CUDA devices are available.
- Validate NCCL/UCX separately from algorithm semantics.
