#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json

from distalgo.core.minio_client import MinIOCheckpointClient, MinIOClientConfig
from distalgo.core.object_checkpoint import ObjectCheckpointStore


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a MinIO/S3 checkpoint integration smoke test.")
    parser.add_argument("--endpoint", default="http://127.0.0.1:9000")
    parser.add_argument("--access-key", default="distalgo")
    parser.add_argument("--secret-key", default="distalgo-password")
    parser.add_argument("--bucket", default="distalgo-checkpoints")
    parser.add_argument("--prefix", default="smoke")
    args = parser.parse_args()

    client = MinIOCheckpointClient(
        MinIOClientConfig(
            endpoint=args.endpoint,
            access_key=args.access_key,
            secret_key=args.secret_key,
        )
    )
    client.ensure_bucket(args.bucket)
    store = ObjectCheckpointStore(client=client, bucket=args.bucket, prefix=args.prefix)
    payload = {"scores": {1: 0.42, 2: 0.58}, "iteration": 3}
    store.save("pagerank", 3, payload)
    loaded = store.load("pagerank", 3)
    if loaded != payload:
        raise SystemExit(f"checkpoint mismatch: expected={payload!r} actual={loaded!r}")
    print(json.dumps({"status": "passed", "bucket": args.bucket, "prefix": args.prefix}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
