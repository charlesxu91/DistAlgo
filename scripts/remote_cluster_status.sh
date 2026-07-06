#!/usr/bin/env bash
set -euo pipefail

export KUBECONFIG="${KUBECONFIG:-$HOME/.kube/config}"

header() {
  printf '\n========== %s ==========\n' "$1"
  date
}

header "host"
hostname
cat /etc/os-release | grep -E '^(PRETTY_NAME|VERSION_ID)=' || true
nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader || true

header "kubernetes"
kubectl version --client=true
kubectl get nodes -o wide
kubectl get nodes -o custom-columns=NAME:.metadata.name,GPU_ALLOCATABLE:.status.allocatable.nvidia\\.com/gpu,GPU_CAPACITY:.status.capacity.nvidia\\.com/gpu || true

header "helm"
helm list -A || true

header "pods"
kubectl get pods -A -o wide

header "ray"
kubectl get crd | grep ray.io || true
kubectl get rayclusters -A || true

header "gpu smoke"
kubectl get pod distalgo-gpu-smoke -o wide || true
kubectl logs distalgo-gpu-smoke || true
