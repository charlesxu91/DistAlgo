from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Any, Dict, Optional

from distalgo.algorithms.registry import AlgorithmRegistry
from distalgo.core.api import JobAPI
from distalgo.core.job import JobRunner


@dataclass(frozen=True)
class HTTPResponse:
    status: int
    body: str
    headers: Dict[str, str]

    @property
    def json(self) -> Dict[str, Any]:
        return json.loads(self.body)


class DistAlgoHTTPApp:
    def __init__(self, runner: JobRunner, registry: AlgorithmRegistry | None = None):
        self.runner = runner
        self.registry = registry or AlgorithmRegistry.default()
        self.api = JobAPI(runner)

    def handle(self, method: str, path: str, body: Optional[str] = None) -> HTTPResponse:
        method = method.upper()
        if method == "GET" and path == "/healthz":
            return self._json(200, {"status": "ok"})
        if method == "GET" and path == "/algorithms":
            return self._json(
                200,
                {
                    "algorithms": self.registry.names(),
                    "metadata": [asdict(item) for item in self.registry.metadata_all()],
                },
            )
        if method == "POST" and path == "/jobs":
            payload = json.loads(body or "{}")
            return self._json(200, self.api.run_json(payload))
        if method == "GET" and path == "/metrics":
            body_text = self.runner.runtime.metrics.to_prometheus_text()
            return HTTPResponse(200, body_text, {"Content-Type": "text/plain; version=0.0.4"})
        return self._json(404, {"error": "not found"})

    def _json(self, status: int, payload: Dict[str, Any]) -> HTTPResponse:
        return HTTPResponse(
            status=status,
            body=json.dumps(payload, ensure_ascii=False, sort_keys=True),
            headers={"Content-Type": "application/json"},
        )
