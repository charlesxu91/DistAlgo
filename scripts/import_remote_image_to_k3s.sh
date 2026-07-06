#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -lt 1 ]; then
  echo "usage: $0 IMAGE [TAR_PATH]" >&2
  echo "example: $0 rayproject/ray:2.9.0 /tmp/distalgo-ray-2.9.0.tar" >&2
  exit 2
fi

IMAGE="$1"
SAFE_IMAGE="$(printf '%s' "$IMAGE" | tr '/:' '__')"
TAR_PATH="${2:-/tmp/distalgo-${SAFE_IMAGE}.tar}"
PULL_IMAGE="${PULL_IMAGE:-1}"

sudo_run() {
  printf '%s\n' "${DISTALGO_SUDO_PASSWORD:- }" | sudo -S -p "" "$@"
}

header() {
  printf '\n========== %s ==========\n' "$1"
  date
}

header "image import plan"
echo "image=$IMAGE"
echo "tar_path=$TAR_PATH"
echo "pull_image=$PULL_IMAGE"

if [ "$PULL_IMAGE" = "1" ]; then
  header "docker pull"
  docker pull "$IMAGE"
fi

header "docker save"
docker save -o "$TAR_PATH" "$IMAGE"
ls -lh "$TAR_PATH"

header "k3s ctr image import"
sudo_run /usr/local/bin/k3s ctr -n k8s.io images import "$TAR_PATH"

header "imported image snapshot"
sudo_run /usr/local/bin/k3s ctr -n k8s.io images list | grep -F "$IMAGE"
