from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict
from urllib.error import HTTPError
from urllib.parse import quote, urlparse
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class MinIOClientConfig:
    endpoint: str
    access_key: str
    secret_key: str
    region: str = "us-east-1"


class MinIOCheckpointClient:
    """Small S3-compatible object client for MinIO checkpoint smoke tests.

    The implementation intentionally covers the object-store operations used by
    ObjectCheckpointStore: create bucket, put object, get object, and head
    object. It uses AWS SigV4 and the Python standard library so the framework
    can validate MinIO integration without requiring boto3 or the MinIO SDK.
    """

    def __init__(self, config: MinIOClientConfig, timeout: float = 10.0):
        self.config = config
        self.timeout = timeout
        parsed = urlparse(config.endpoint)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("endpoint must be an http(s) URL")
        self._endpoint = config.endpoint.rstrip("/")
        self._host = parsed.netloc

    def ensure_bucket(self, bucket: str) -> None:
        if self.bucket_exists(bucket):
            return
        self._request("PUT", self._bucket_path(bucket), b"")

    def bucket_exists(self, bucket: str) -> bool:
        try:
            self._request("HEAD", self._bucket_path(bucket), b"")
            return True
        except HTTPError as exc:
            if exc.code == 404:
                return False
            raise

    def put_object(self, bucket: str, key: str, body: bytes) -> None:
        self._request("PUT", self._object_path(bucket, key), body)

    def get_object(self, bucket: str, key: str) -> bytes:
        return self._request("GET", self._object_path(bucket, key), b"")

    def object_exists(self, bucket: str, key: str) -> bool:
        try:
            self._request("HEAD", self._object_path(bucket, key), b"")
            return True
        except HTTPError as exc:
            if exc.code == 404:
                return False
            raise

    def _request(self, method: str, path: str, body: bytes) -> bytes:
        now = datetime.now(timezone.utc)
        payload_hash = hashlib.sha256(body).hexdigest()
        headers = {
            "Host": self._host,
            "x-amz-content-sha256": payload_hash,
            "x-amz-date": now.strftime("%Y%m%dT%H%M%SZ"),
        }
        headers["Authorization"] = self._authorization(method, path, headers, payload_hash, now)
        request = Request(self._endpoint + path, data=body if method in {"PUT", "POST"} else None, method=method)
        for key, value in headers.items():
            request.add_header(key, value)
        with urlopen(request, timeout=self.timeout) as response:  # noqa: S310 - endpoint is user supplied by CLI.
            return response.read()

    def _authorization(self, method: str, path: str, headers: Dict[str, str], payload_hash: str, now: datetime) -> str:
        date = now.strftime("%Y%m%d")
        scope = f"{date}/{self.config.region}/s3/aws4_request"
        signed_headers = "host;x-amz-content-sha256;x-amz-date"
        canonical_headers = (
            f"host:{headers['Host']}\n"
            f"x-amz-content-sha256:{headers['x-amz-content-sha256']}\n"
            f"x-amz-date:{headers['x-amz-date']}\n"
        )
        canonical_request = "\n".join(
            [method, path, "", canonical_headers, signed_headers, payload_hash]
        )
        string_to_sign = "\n".join(
            [
                "AWS4-HMAC-SHA256",
                headers["x-amz-date"],
                scope,
                hashlib.sha256(canonical_request.encode("utf-8")).hexdigest(),
            ]
        )
        signature = hmac.new(
            self._signing_key(date),
            string_to_sign.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        return (
            "AWS4-HMAC-SHA256 "
            f"Credential={self.config.access_key}/{scope}, "
            f"SignedHeaders={signed_headers}, Signature={signature}"
        )

    def _signing_key(self, date: str) -> bytes:
        key = ("AWS4" + self.config.secret_key).encode("utf-8")
        for message in (date, self.config.region, "s3", "aws4_request"):
            key = hmac.new(key, message.encode("utf-8"), hashlib.sha256).digest()
        return key

    @staticmethod
    def _bucket_path(bucket: str) -> str:
        return "/" + quote(bucket, safe="")

    @staticmethod
    def _object_path(bucket: str, key: str) -> str:
        quoted_key = "/".join(quote(segment, safe="") for segment in key.split("/"))
        return f"/{quote(bucket, safe='')}/{quoted_key}"
