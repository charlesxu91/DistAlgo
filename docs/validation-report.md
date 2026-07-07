# Validation Report

## Local Validation

Commands run successfully:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
env PYTHONPYCACHEPREFIX=/private/tmp/distalgo-pycache python3 -m compileall src/distalgo scripts tests
make smoke
env CUDA_VISIBLE_DEVICES=0 python3 scripts/probe_gpu.py
docker compose -f deploy/docker-compose.yaml config
```

Latest local test result:

```text
53 tests passed, 2 socket-level HTTP smoke tests skipped when sandbox denied TCP bind.
```

The socket-level HTTP smoke test is environment-specific. The HTTP app route
behavior is covered by direct app tests, and the socket-level test runs when
localhost binding is permitted.

## Remote GPU Smoke Check

SSH validation against `192.168.124.8` passed.

Observed:

```text
host: charles-B850M-EAGLE-WIFI6E-ICE
os: Ubuntu 24.04
kernel: 6.17.0-35-generic
gpu: NVIDIA GeForce RTX 5090, 32607 MiB, driver 580.159.03
```

This validates single-GPU availability for future GPU backend smoke tests. It
does not validate true multi-GPU or NCCL behavior because the host exposes one
physical GPU.

## Remote K3s/KubeRay Snapshot

The remote host has been bootstrapped as a single-node K3s cloud-native test
bed:

```text
K3s: v1.36.2+k3s1
KubeRay operator: Helm release kuberay-operator, chart 1.6.2
NVIDIA device plugin: Helm release nvdp, time-slicing replicas 4
CUDA smoke image: nvidia/cuda:12.4.1-base-ubuntu22.04
```

Validated Kubernetes GPU signal:

```text
nvidia.com/gpu capacity: 4
nvidia.com/gpu allocatable: 4
```

Validated GPU smoke pod output included:

```text
NVIDIA GeForce RTX 5090
32607MiB
```

The `distalgo-gpu-smoke` pod runs `nvidia-smi` through K3s with
`nvidia.com/gpu: 1`, proving the device plugin, K3s containerd runtime, and CUDA
container path.

The repository includes `scripts/remote_gpu_ray_smoke.sh` for this full
Ray-level GPU scheduling check.

Validated KubeRay GPU RayCluster:

```text
RayCluster: default/distalgo-gpu, status ready
Desired workers: 1
Available workers: 1
Ray resources: CPU 1500m, memory 5Gi, GPU 1
Pods: head 1/1 Running, GPU worker 1/1 Running
```

Validated Ray fractional GPU task output:

```text
DISTALGO_RAY_GPU_RESULT=[
  {"cuda_visible_devices": "0", "gpu_ids": [0], "index": 0},
  {"cuda_visible_devices": "0", "gpu_ids": [0], "index": 1}
]
```

This proves that Kubernetes GPU resources, KubeRay worker placement, Ray
cluster membership, and Ray fractional GPU assignment work on the remote RTX
5090 test host.

## Remote K3s MinIO Checkpoint Service

The target K3s cluster runs a MinIO service for object checkpoint storage:

```text
Namespace: distalgo-system
Deployment: distalgo-minio
Service: distalgo-minio:9000
Smoke job: distalgo-minio-smoke
```

The smoke job runs inside the target K3s cluster with `minio/mc`, creates the
`distalgo-checkpoints` bucket, writes a PageRank checkpoint object, reads it
back, and verifies the payload.

Validated output includes:

```text
DISTALGO_MINIO_K3S_SMOKE=passed
```

The repository includes `deploy/kubernetes/minio.yaml` for the deployable
manifest and `scripts/remote_minio_k3s_smoke.sh` for repeatable target-machine
validation.

## Remote RayCluster Execution

The remote K3s cluster also ran a real KubeRay RayCluster:

```text
RayCluster: default/distalgo-ray, status ready
Ray pods: head 1/1 Running, worker 1/1 Running
Ray resources: CPU 2.0, head node + worker node
Remote task result: 42
```

This validates that K3s, KubeRay, and the Ray image path can execute real Ray
remote tasks. Algorithm-level remote execution is represented by the Ray actor
adapter tests and remains the next production-hardening step for large graph
jobs.

## Completed After Remote KubeRay Validation

- MinIO/S3-compatible service integration was implemented with a dependency-free
  SigV4 client, `scripts/minio_service_smoke.py`, K3s manifest, and remote K3s
  smoke validation.
- Optional GPU kernels were implemented for KMeans, PageRank, and BFS frontier
  primitives. The kernels use CuPy when available and otherwise fall back to the
  deterministic CPU backend.
- Deterministic stress benchmarking was implemented in
  `scripts/stress_benchmark.py` for PageRank, SSSP, and KMeans.
- Volcano vGPU + HAMi-core preflight and smoke scripts were added:
  `scripts/remote_volcano_vgpu_preflight.sh` and
  `scripts/remote_volcano_vgpu_smoke.sh`. The smoke script validates
  `volcano.sh/vgpu-*` resources, a single vGPU Pod, a gang-scheduled
  VolcanoJob, and an intentionally oversized Queue case when the advanced GPU
  plugin profile is installed.

## Remaining External Validation

- Validate NCCL/UCX only on a host with multiple physical CUDA devices.
