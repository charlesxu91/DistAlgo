#!/usr/bin/env bash
set -euo pipefail

LOG_FILE="${LOG_FILE:-/tmp/distalgo-k3s-fix.log}"
exec > >(tee -a "$LOG_FILE") 2>&1

sudo_run() {
  printf '%s\n' "${DISTALGO_SUDO_PASSWORD:- }" | sudo -S -p "" "$@"
}

header() {
  printf '\n========== %s ==========\n' "$1"
  date
}

export KUBECONFIG="$HOME/.kube/config"

header "configure k3s registry mirrors"
cat >/tmp/distalgo-registries.yaml <<'YAML'
mirrors:
  docker.io:
    endpoint:
      - "https://docker.m.daocloud.io"
      - "https://docker.1panel.live"
      - "https://docker.1ms.run"
      - "https://docker.xuanyuan.me"
      - "https://registry-1.docker.io"
  registry.k8s.io:
    endpoint:
      - "https://k8s.m.daocloud.io"
      - "https://registry.k8s.io"
  nvcr.io:
    endpoint:
      - "https://nvcr.m.daocloud.io"
      - "https://nvcr.io"
  ghcr.io:
    endpoint:
      - "https://ghcr.m.daocloud.io"
      - "https://ghcr.io"
  quay.io:
    endpoint:
      - "https://quay.m.daocloud.io"
      - "https://quay.io"
YAML

sudo_run mkdir -p /etc/rancher/k3s
sudo_run install -m 0644 /tmp/distalgo-registries.yaml /etc/rancher/k3s/registries.yaml

header "configure k3s default nvidia runtime"
if [ -x /usr/bin/nvidia-container-runtime ] || [ -x /usr/local/bin/nvidia-container-runtime ]; then
  cat >/tmp/distalgo-k3s-nvidia-runtime.toml <<'TOML'
[plugins.'io.containerd.cri.v1.runtime'.containerd]
  default_runtime_name = 'nvidia'
TOML
  sudo_run mkdir -p /var/lib/rancher/k3s/agent/etc/containerd/config-v3.toml.d
  sudo_run install -m 0644 /tmp/distalgo-k3s-nvidia-runtime.toml /var/lib/rancher/k3s/agent/etc/containerd/config-v3.toml.d/10-nvidia-default.toml
else
  echo "WARN: nvidia-container-runtime is not installed; GPU pods may fail until NVIDIA container toolkit is configured."
fi

sudo_run systemctl restart k3s

header "wait for k3s"
for _ in {1..90}; do
  if kubectl get nodes >/dev/null 2>&1; then
    break
  fi
  sleep 2
done
kubectl get nodes -o wide

NODE_NAME="$(kubectl get nodes -o jsonpath='{.items[0].metadata.name}')"
kubectl label node "$NODE_NAME" nvidia.com/gpu.present=true feature.node.kubernetes.io/pci-10de.present=true --overwrite
kubectl get node "$NODE_NAME" --show-labels

header "restart system pods"
kubectl -n kube-system delete pod -l k8s-app=kube-dns --ignore-not-found=true
kubectl -n kube-system delete pod -l k8s-app=metrics-server --ignore-not-found=true
kubectl -n kube-system delete pod -l app=local-path-provisioner --ignore-not-found=true

header "wait for kube-system pods"
for _ in {1..120}; do
  kubectl get pods -n kube-system -o wide
  not_ready="$(kubectl get pods -n kube-system --no-headers 2>/dev/null | awk '$3 !~ /Running|Completed/ {print}' | wc -l | tr -d ' ')"
  if [ "${not_ready:-1}" = "0" ]; then
    break
  fi
  sleep 5
done

header "nvidia device plugin"
kubectl -n kube-system rollout restart ds/nvdp-nvidia-device-plugin || true
kubectl -n kube-system rollout status ds/nvdp-nvidia-device-plugin --timeout=300s || true
kubectl -n kube-system get pods -l app.kubernetes.io/name=nvidia-device-plugin -o wide || true
kubectl get nodes -o custom-columns=NAME:.metadata.name,GPU_ALLOCATABLE:.status.allocatable.nvidia\\.com/gpu,GPU_CAPACITY:.status.capacity.nvidia\\.com/gpu || true

header "install kuberay operator with retry"
helm repo add kuberay https://ray-project.github.io/kuberay-helm/ >/dev/null 2>&1 || true
helm repo update kuberay
for i in {1..5}; do
  if helm upgrade --install kuberay-operator kuberay/kuberay-operator --namespace kuberay-system --create-namespace; then
    break
  fi
  echo "kuberay helm install failed; retry $i"
  sleep 20
done
kubectl -n kuberay-system rollout status deployment/kuberay-operator --timeout=300s
kubectl get crd | grep ray.io

header "apply raycluster"
cat >/tmp/distalgo-raycluster.yaml <<'YAML'
apiVersion: ray.io/v1
kind: RayCluster
metadata:
  name: distalgo-ray
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
  - groupName: cpu-workers
    replicas: 1
    minReplicas: 1
    maxReplicas: 2
    rayStartParams: {}
    template:
      spec:
        containers:
        - name: ray-worker
          image: rayproject/ray:2.9.0
          imagePullPolicy: IfNotPresent
          resources:
            requests:
              cpu: "500m"
              memory: "1Gi"
            limits:
              cpu: "1"
              memory: "2Gi"
YAML

kubectl apply -f /tmp/distalgo-raycluster.yaml
kubectl wait --for=condition=Ready pod -l ray.io/cluster=distalgo-ray --timeout=600s || true

header "gpu smoke pod"
kubectl delete pod distalgo-gpu-smoke --ignore-not-found=true >/dev/null 2>&1 || true
cat >/tmp/distalgo-gpu-smoke.yaml <<'YAML'
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
kubectl apply -f /tmp/distalgo-gpu-smoke.yaml || true
kubectl wait --for=condition=Ready pod/distalgo-gpu-smoke --timeout=300s || true
kubectl logs distalgo-gpu-smoke || true

header "final status"
helm list -A
kubectl get nodes -o wide
kubectl get pods -A -o wide
kubectl get rayclusters -A || true
kubectl get events -A --sort-by=.lastTimestamp | tail -60
