#!/usr/bin/env bash
set -euo pipefail

NAMESPACE="${NAMESPACE:-distalgo-volcano-vgpu}"
ROOT_DIR="${ROOT_DIR:-$HOME/DistAlgo}"
MANIFEST_DIR="${MANIFEST_DIR:-$ROOT_DIR/deploy/volcano-vgpu}"

header() {
  printf '\n== %s ==\n' "$1"
}

require_resource() {
  local node="$1"
  local resource="$2"
  local value
  value="$(kubectl get node "$node" -o "jsonpath={.status.allocatable['${resource//./\\.}']}" 2>/dev/null || true)"
  if [[ -z "$value" ]]; then
    echo "MISSING_RESOURCE: $resource is not registered on node $node"
    return 1
  fi
  echo "$resource=$value"
}

wait_pod_ready() {
  local pod="$1"
  kubectl -n "$NAMESPACE" wait --for=condition=Ready "pod/$pod" --timeout=300s
}

header "cluster snapshot"
kubectl get node -o wide
NODE_NAME="$(kubectl get nodes -o jsonpath='{.items[0].metadata.name}')"
kubectl get pod -A | grep -E 'volcano|hami|vgpu' || true

header "volcano vgpu resources"
require_resource "$NODE_NAME" "volcano.sh/vgpu-number"
require_resource "$NODE_NAME" "volcano.sh/vgpu-memory"
require_resource "$NODE_NAME" "volcano.sh/vgpu-cores"

header "apply namespace and queue"
kubectl apply -f "$MANIFEST_DIR/namespace.yaml"
kubectl apply -f "$MANIFEST_DIR/queue.yaml"
kubectl get queue gpu-small-queue -o yaml

header "single vgpu pod"
kubectl -n "$NAMESPACE" delete pod distalgo-volcano-vgpu-single --ignore-not-found=true
kubectl apply -f "$MANIFEST_DIR/vgpu-pod.yaml"
wait_pod_ready distalgo-volcano-vgpu-single
kubectl -n "$NAMESPACE" logs distalgo-volcano-vgpu-single

header "volcanojob gang scheduling success"
kubectl -n "$NAMESPACE" delete vcjob distalgo-vgpu-gang --ignore-not-found=true || true
kubectl apply -f "$MANIFEST_DIR/vcjob-vgpu-gang.yaml"
sleep 8
kubectl -n "$NAMESPACE" get vcjob,podgroup,pod -o wide
kubectl -n "$NAMESPACE" get vcjob distalgo-vgpu-gang -o jsonpath='{.status.state.phase}{"\n"}' | grep -E 'Running|Completed'

header "volcanojob insufficient resources"
kubectl -n "$NAMESPACE" delete vcjob distalgo-vgpu-gang-insufficient --ignore-not-found=true || true
kubectl apply -f "$MANIFEST_DIR/vcjob-vgpu-insufficient.yaml"
sleep 8
kubectl -n "$NAMESPACE" get vcjob,podgroup,pod -o wide
kubectl -n "$NAMESPACE" describe podgroup -l volcano.sh/job-name=distalgo-vgpu-gang-insufficient || true

echo "DONE: Volcano vGPU + HAMi-core smoke validation passed."
