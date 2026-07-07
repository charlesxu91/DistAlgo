#!/usr/bin/env bash
set -euo pipefail

export KUBECONFIG="${KUBECONFIG:-$HOME/.kube/config}"

header() {
  printf '\n========== %s ==========\n' "$1"
  date
}

wait_for_raycluster() {
  local name="$1"
  local timeout_seconds="${2:-900}"
  local deadline=$((SECONDS + timeout_seconds))
  while [ "$SECONDS" -lt "$deadline" ]; do
    local ready
    ready="$(kubectl get raycluster "$name" -o jsonpath='{.status.state}' 2>/dev/null || true)"
    if [ "$ready" = "ready" ]; then
      return 0
    fi
    kubectl get raycluster "$name" 2>/dev/null || true
    sleep 10
  done
  return 1
}

header "host gpu inventory"
nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader

header "kubernetes gpu resource inventory"
kubectl get nodes -o custom-columns=NAME:.metadata.name,GPU_ALLOCATABLE:.status.allocatable.nvidia\\.com/gpu,GPU_CAPACITY:.status.capacity.nvidia\\.com/gpu

header "kubernetes cuda smoke pod"
kubectl delete pod distalgo-gpu-smoke --ignore-not-found=true >/dev/null 2>&1 || true
cat <<'YAML' | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: distalgo-gpu-smoke
spec:
  restartPolicy: Never
  containers:
  - name: nvidia-smi
    image: nvidia/cuda:12.4.1-base-ubuntu22.04
    imagePullPolicy: IfNotPresent
    command: ["nvidia-smi"]
    resources:
      limits:
        nvidia.com/gpu: 1
YAML
kubectl wait --for=condition=Ready pod/distalgo-gpu-smoke --timeout=300s
kubectl logs distalgo-gpu-smoke

header "apply gpu raycluster"
kubectl delete raycluster distalgo-gpu --ignore-not-found=true >/dev/null 2>&1 || true
cat <<'YAML' | kubectl apply -f -
apiVersion: ray.io/v1
kind: RayCluster
metadata:
  name: distalgo-gpu
  namespace: default
spec:
  rayVersion: "2.9.0"
  headGroupSpec:
    rayStartParams:
      dashboard-host: "0.0.0.0"
    template:
      spec:
        containers:
        - name: ray-head
          image: rayproject/ray:2.9.0
          imagePullPolicy: IfNotPresent
          ports:
          - containerPort: 6379
            name: gcs
          - containerPort: 8265
            name: dashboard
          - containerPort: 10001
            name: client
          resources:
            requests:
              cpu: "500m"
              memory: "1Gi"
            limits:
              cpu: "1"
              memory: "2Gi"
  workerGroupSpecs:
  - groupName: gpu-workers
    replicas: 1
    minReplicas: 1
    maxReplicas: 1
    rayStartParams: {}
    template:
      spec:
        containers:
        - name: ray-worker
          image: rayproject/ray-ml:2.9.0-gpu
          imagePullPolicy: IfNotPresent
          resources:
            requests:
              cpu: "1"
              memory: "4Gi"
              nvidia.com/gpu: "1"
            limits:
              cpu: "4"
              memory: "16Gi"
              nvidia.com/gpu: "1"
YAML

wait_for_raycluster distalgo-gpu 900
kubectl get pods -l ray.io/cluster=distalgo-gpu -o wide

header "ray fractional gpu scheduling smoke"
HEAD_POD="$(kubectl get pod -l ray.io/cluster=distalgo-gpu,ray.io/node-type=head -o jsonpath='{.items[0].metadata.name}')"
kubectl exec "$HEAD_POD" -- python - <<'PY'
import json
import os
import ray

ray.init(address="auto")

@ray.remote(num_gpus=0.25)
def gpu_task(index):
    return {
        "index": index,
        "gpu_ids": ray.get_gpu_ids(),
        "cuda_visible_devices": os.environ.get("CUDA_VISIBLE_DEVICES", ""),
    }

results = ray.get([gpu_task.remote(index) for index in range(2)])
print("DISTALGO_RAY_GPU_RESULT=" + json.dumps(results, sort_keys=True))
if not any(item["gpu_ids"] for item in results):
    raise SystemExit("Ray did not assign a GPU id to fractional GPU tasks")
PY

header "done"
echo "DONE: Kubernetes GPU pod and Ray fractional GPU scheduling smoke passed."
