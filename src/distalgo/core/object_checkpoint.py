from __future__ import annotations

import pickle
from typing import Any


class ObjectCheckpointStore:
    """Checkpoint store for MinIO/S3-compatible clients.

    The client is intentionally tiny for MVP tests: it needs put_object,
    get_object, and object_exists. A boto3 or MinIO wrapper can implement this
    interface without changing runtime code.
    """

    def __init__(self, client, bucket: str, prefix: str = ""):
        self.client = client
        self.bucket = bucket
        self.prefix = prefix.strip("/")

    def save(self, algorithm: str, iteration: int, state: Any) -> None:
        self.client.put_object(self.bucket, self._key(algorithm, iteration), pickle.dumps(state))

    def load(self, algorithm: str, iteration: int) -> Any:
        return pickle.loads(self.client.get_object(self.bucket, self._key(algorithm, iteration)))

    def exists(self, algorithm: str, iteration: int) -> bool:
        return self.client.object_exists(self.bucket, self._key(algorithm, iteration))

    def _key(self, algorithm: str, iteration: int) -> str:
        key = f"{algorithm}/iteration-{iteration}.pkl"
        return f"{self.prefix}/{key}" if self.prefix else key
