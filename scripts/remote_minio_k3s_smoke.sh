#!/usr/bin/env bash
set -euo pipefail

NAMESPACE="${NAMESPACE:-distalgo-system}"
MINIO_USER="${MINIO_USER:-distalgo}"
MINIO_PASSWORD="${MINIO_PASSWORD:-distalgo-password}"
BUCKET="${BUCKET:-distalgo-checkpoints}"

header() {
  printf '\n== %s ==\n' "$1"
}

header "cluster snapshot"
kubectl get node -o wide

header "deploy minio service"
kubectl apply -f - <<EOF
apiVersion: v1
kind: Namespace
metadata:
  name: ${NAMESPACE}
---
apiVersion: v1
kind: Secret
metadata:
  name: distalgo-minio-secret
  namespace: ${NAMESPACE}
type: Opaque
stringData:
  MINIO_ROOT_USER: ${MINIO_USER}
  MINIO_ROOT_PASSWORD: ${MINIO_PASSWORD}
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: distalgo-minio
  namespace: ${NAMESPACE}
  labels:
    app.kubernetes.io/name: distalgo-minio
    app.kubernetes.io/part-of: distalgo
spec:
  replicas: 1
  selector:
    matchLabels:
      app.kubernetes.io/name: distalgo-minio
  template:
    metadata:
      labels:
        app.kubernetes.io/name: distalgo-minio
        app.kubernetes.io/part-of: distalgo
    spec:
      containers:
        - name: minio
          image: quay.io/minio/minio:RELEASE.2024-01-16T16-07-38Z
          imagePullPolicy: IfNotPresent
          args:
            - server
            - /data
            - --console-address
            - :9001
          envFrom:
            - secretRef:
                name: distalgo-minio-secret
          ports:
            - name: api
              containerPort: 9000
            - name: console
              containerPort: 9001
          readinessProbe:
            httpGet:
              path: /minio/health/ready
              port: api
            initialDelaySeconds: 5
            periodSeconds: 5
          livenessProbe:
            httpGet:
              path: /minio/health/live
              port: api
            initialDelaySeconds: 10
            periodSeconds: 10
          volumeMounts:
            - name: data
              mountPath: /data
      volumes:
        - name: data
          emptyDir: {}
---
apiVersion: v1
kind: Service
metadata:
  name: distalgo-minio
  namespace: ${NAMESPACE}
  labels:
    app.kubernetes.io/name: distalgo-minio
    app.kubernetes.io/part-of: distalgo
spec:
  selector:
    app.kubernetes.io/name: distalgo-minio
  ports:
    - name: api
      port: 9000
      targetPort: api
    - name: console
      port: 9001
      targetPort: console
EOF

kubectl -n "$NAMESPACE" rollout status deployment/distalgo-minio --timeout=300s
kubectl -n "$NAMESPACE" get deploy,svc,pod -l app.kubernetes.io/part-of=distalgo -o wide

header "cluster-internal object checkpoint roundtrip"
kubectl -n "$NAMESPACE" delete job distalgo-minio-smoke --ignore-not-found=true
kubectl -n "$NAMESPACE" apply -f - <<EOF
apiVersion: batch/v1
kind: Job
metadata:
  name: distalgo-minio-smoke
  labels:
    app.kubernetes.io/name: distalgo-minio-smoke
    app.kubernetes.io/part-of: distalgo
spec:
  backoffLimit: 1
  template:
    metadata:
      labels:
        app.kubernetes.io/name: distalgo-minio-smoke
        app.kubernetes.io/part-of: distalgo
    spec:
      restartPolicy: Never
      containers:
        - name: mc
          image: quay.io/minio/mc:RELEASE.2024-01-16T16-06-34Z
          imagePullPolicy: IfNotPresent
          env:
            - name: MINIO_USER
              valueFrom:
                secretKeyRef:
                  name: distalgo-minio-secret
                  key: MINIO_ROOT_USER
            - name: MINIO_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: distalgo-minio-secret
                  key: MINIO_ROOT_PASSWORD
          command:
            - /bin/sh
            - -ec
            - |
              mc alias set distalgo http://distalgo-minio.${NAMESPACE}.svc.cluster.local:9000 "\$MINIO_USER" "\$MINIO_PASSWORD"
              mc mb --ignore-existing distalgo/${BUCKET}
              printf '{"algorithm":"pagerank","iteration":1,"scores":{"1":0.5,"2":0.5}}\n' > /tmp/checkpoint.json
              mc cp /tmp/checkpoint.json distalgo/${BUCKET}/smoke/pagerank/iteration-1.json
              payload="\$(mc cat distalgo/${BUCKET}/smoke/pagerank/iteration-1.json)"
              case "\$payload" in
                *'"algorithm":"pagerank"'*) ;;
                *) echo "unexpected checkpoint payload: \$payload" >&2; exit 1 ;;
              esac
              echo DISTALGO_MINIO_K3S_SMOKE=passed
EOF

kubectl -n "$NAMESPACE" wait --for=condition=complete job/distalgo-minio-smoke --timeout=180s
kubectl -n "$NAMESPACE" logs job/distalgo-minio-smoke

echo "DONE: target K3s MinIO service checkpoint smoke validation passed."
