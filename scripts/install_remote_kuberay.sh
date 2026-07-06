#!/usr/bin/env bash
set -euo pipefail

LOG_FILE="${LOG_FILE:-/tmp/distalgo-kuberay-install.log}"
exec > >(tee -a "$LOG_FILE") 2>&1

sudo_run() {
  printf '%s\n' "${DISTALGO_SUDO_PASSWORD:- }" | sudo -S -p "" "$@"
}

wait_for_rollout() {
  local resource="$1"
  local namespace="$2"
  local timeout="${3:-300s}"
  kubectl -n "$namespace" rollout status "$resource" --timeout="$timeout"
}

header() {
  printf '\n========== %s ==========\n' "$1"
  date
}

header "host inventory"
hostname
cat /etc/os-release || true
nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader || true
docker --version || true

header "install or verify k3s"
if ! command -v k3s >/dev/null 2>&1; then
  curl --connect-timeout 20 --max-time 180 -sfL https://get.k3s.io -o /tmp/install-k3s.sh
  chmod +x /tmp/install-k3s.sh
  K3S_VERSION="${K3S_VERSION:-v1.36.2+k3s1}"
  K3S_URL="${K3S_URL:-https://rancher-mirror.rancher.cn/k3s/${K3S_VERSION}/k3s}"
  curl --connect-timeout 20 --max-time 600 -fL "$K3S_URL" -o /tmp/k3s
  sudo_run install -m 0755 /tmp/k3s /usr/local/bin/k3s
  sudo_run env INSTALL_K3S_SKIP_DOWNLOAD=true INSTALL_K3S_EXEC="--disable traefik --write-kubeconfig-mode 644" /tmp/install-k3s.sh
else
  echo "k3s already installed"
  sudo_run systemctl enable --now k3s
fi

mkdir -p "$HOME/.kube"
sudo_run cp /etc/rancher/k3s/k3s.yaml "$HOME/.kube/config"
sudo_run chown "$USER:$USER" "$HOME/.kube/config"
export KUBECONFIG="$HOME/.kube/config"

kubectl version --client
for _ in {1..60}; do
  if kubectl get nodes >/dev/null 2>&1; then
    break
  fi
  sleep 2
done
kubectl get nodes -o wide

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

header "install or verify helm"
if ! command -v helm >/dev/null 2>&1; then
  HELM_VERSION="${HELM_VERSION:-v3.15.4}"
  curl --connect-timeout 20 --max-time 300 -fL "https://get.helm.sh/helm-${HELM_VERSION}-linux-amd64.tar.gz" -o /tmp/helm-linux-amd64.tar.gz
  tar -xzf /tmp/helm-linux-amd64.tar.gz -C /tmp
  sudo_run install -m 0755 /tmp/linux-amd64/helm /usr/local/bin/helm
else
  helm version
fi
helm version

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
sleep 10

header "install nvidia device plugin with time-slicing"
helm repo add nvdp https://nvidia.github.io/k8s-device-plugin >/dev/null 2>&1 || true
helm repo update nvdp

cat >/tmp/nvidia-device-plugin-values.yaml <<'YAML'
config:
  map:
    default: |-
      version: v1
      sharing:
        timeSlicing:
          renameByDefault: false
          failRequestsGreaterThanOne: false
          resources:
          - name: nvidia.com/gpu
            replicas: 4
YAML

helm upgrade --install nvdp nvdp/nvidia-device-plugin \
  --namespace kube-system \
  -f /tmp/nvidia-device-plugin-values.yaml

wait_for_rollout ds/nvdp-nvidia-device-plugin kube-system 300s || true
kubectl get pods -n kube-system -l app.kubernetes.io/name=nvidia-device-plugin -o wide || true

header "install kuberay operator"
helm repo add kuberay https://ray-project.github.io/kuberay-helm/ >/dev/null 2>&1 || true
helm repo update kuberay
helm upgrade --install kuberay-operator kuberay/kuberay-operator \
  --namespace kuberay-system \
  --create-namespace

wait_for_rollout deployment/kuberay-operator kuberay-system 300s
kubectl get pods -n kuberay-system -o wide

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
kubectl get rayclusters -A
kubectl get pods -A -o wide

header "gpu resource snapshot"
kubectl get nodes -o custom-columns=NAME:.metadata.name,GPU_ALLOCATABLE:.status.allocatable.nvidia\\.com/gpu,GPU_CAPACITY:.status.capacity.nvidia\\.com/gpu || true
kubectl describe node "$(kubectl get nodes -o jsonpath='{.items[0].metadata.name}')" | grep -A8 -E 'Capacity:|Allocatable:|nvidia.com/gpu' || true

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
echo "DONE: distalgo K3s + NVIDIA device plugin + KubeRay bootstrap finished."
