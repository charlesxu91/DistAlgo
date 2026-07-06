from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any, Dict

from distalgo.core.job import AlgorithmJob, JobRunner


class JobAPI:
    def __init__(self, runner: JobRunner):
        self.runner = runner

    def run_json(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        try:
            job = AlgorithmJob(
                algorithm=payload["algorithm"],
                params=dict(payload.get("params", {})),
                partitions=int(payload.get("partitions", 1)),
                data=payload["data"],
            )
            result = self.runner.run(job)
            return {"state": "completed", "result": self._jsonable(result)}
        except Exception as exc:  # pragma: no cover - exact exceptions are surfaced to caller.
            return {"state": "failed", "error": str(exc)}

    def _jsonable(self, value: Any) -> Any:
        if is_dataclass(value):
            return self._jsonable(asdict(value))
        if isinstance(value, dict):
            return {str(key): self._jsonable(item) for key, item in value.items()}
        if isinstance(value, (list, tuple)):
            return [self._jsonable(item) for item in value]
        return value
