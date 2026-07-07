#!/usr/bin/env bash
set -euo pipefail

header() {
  printf '\n== %s ==\n' "$1"
}

header "host gpu"
nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader || true

header "kubernetes"
kubectl version --client=true
kubectl get node -o wide
NODE_NAME="$(kubectl get nodes -o jsonpath='{.items[0].metadata.name}')"

header "gpu plugins"
kubectl get ds -A | grep -E 'nvidia|hami|vgpu|volcano' || true
kubectl get pod -A | grep -E 'nvidia|hami|vgpu|volcano' || true

header "registered gpu resources"
kubectl get node "$NODE_NAME" -o yaml | grep -E 'nvidia.com/gpu|volcano.sh/vgpu|nvidia.com/gpumem|nvidia.com/gpucores' || true

cat <<'NOTE'
Decision rule:
- If only nvidia.com/gpu is present, the current cluster is still on the default
  NVIDIA device-plugin time-slicing profile.
- Volcano vGPU validation requires volcano.sh/vgpu-number,
  volcano.sh/vgpu-memory, and volcano.sh/vgpu-cores to be registered.
- Do not run multiple GPU device plugins on the same node unless this is an
  intentional plugin switch test.
NOTE
