# Volcano vGPU Examples

These manifests are an optional validation harness for the advanced DistAlgo GPU
profile:

```text
Volcano Scheduler + deviceshare + volcano-vgpu-device-plugin + HAMi-core
```

They are not required for the default K3s/KubeRay MVP path.

Apply only after the target cluster already exposes these node resources:

```text
volcano.sh/vgpu-number
volcano.sh/vgpu-memory
volcano.sh/vgpu-cores
```

Recommended validation order:

```bash
kubectl apply -f deploy/volcano-vgpu/namespace.yaml
kubectl apply -f deploy/volcano-vgpu/queue.yaml
kubectl apply -f deploy/volcano-vgpu/vgpu-pod.yaml
kubectl apply -f deploy/volcano-vgpu/vcjob-vgpu-gang.yaml
kubectl apply -f deploy/volcano-vgpu/vcjob-vgpu-insufficient.yaml
```

Expected behavior:

- `vgpu-pod.yaml`: single Pod runs with `schedulerName: volcano`.
- `vcjob-vgpu-gang.yaml`: both workers run together when resources are enough.
- `vcjob-vgpu-insufficient.yaml`: PodGroup stays `Inqueue` / `Pending` with
  `NotEnoughResources`, proving gang scheduling avoids partial worker launch.
- `queue.yaml`: limits the queue's total vGPU resource capability.

Clean up:

```bash
kubectl delete -f deploy/volcano-vgpu/vcjob-vgpu-insufficient.yaml --ignore-not-found
kubectl delete -f deploy/volcano-vgpu/vcjob-vgpu-gang.yaml --ignore-not-found
kubectl delete -f deploy/volcano-vgpu/vgpu-pod.yaml --ignore-not-found
kubectl delete -f deploy/volcano-vgpu/queue.yaml --ignore-not-found
```
