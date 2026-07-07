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

Latest test result:

```text
45 tests passed, 1 socket-level HTTP smoke test skipped when sandbox denied TCP bind.
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

The repository now includes `scripts/remote_gpu_ray_smoke.sh` to extend this
into a Ray-level GPU scheduling check. It creates a GPU RayCluster and runs
fractional `num_gpus=0.25` Ray tasks. This is the next command to run on the
remote host when image pulls are available.

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

## Remaining External Validation

- Run MinIO service integration instead of the in-memory MinIO-compatible client.
- Run `scripts/remote_gpu_ray_smoke.sh` end-to-end and record the Ray GPU task
  output in this report.
- Validate RAPIDS/cuGraph/cuML kernels after adding GPU implementations.
- Validate NCCL/UCX only on a host with multiple physical CUDA devices.
- Run large-graph performance and stress tests.
