from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Sequence

from distalgo.algorithms.registry import AlgorithmRegistry
from distalgo.core.data import load_edges_csv, load_json_dataset
from distalgo.core.models import AlgorithmResult


@dataclass(frozen=True)
class AlgorithmJob:
    algorithm: str
    data: Sequence[Any]
    params: Dict[str, Any] = field(default_factory=dict)
    partitions: int = 1


def load_job(path: Path) -> AlgorithmJob:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if "data" in payload:
        data = payload["data"]
    else:
        data_path = Path(payload["data_path"])
        data_format = payload.get("data_format", "json")
        if data_format == "edges_csv":
            data = load_edges_csv(data_path)
        elif data_format == "json":
            data = load_json_dataset(data_path)
        else:
            raise ValueError(f"unsupported data_format: {data_format}")
    return AlgorithmJob(
        algorithm=payload["algorithm"],
        params=dict(payload.get("params", {})),
        partitions=int(payload.get("partitions", 1)),
        data=data,
    )


class JobRunner:
    def __init__(self, runtime, registry: AlgorithmRegistry | None = None):
        self.runtime = runtime
        self.registry = registry or AlgorithmRegistry.default()

    def run(self, job: AlgorithmJob) -> AlgorithmResult:
        algorithm = self.registry.create(job.algorithm, job.params)
        return self.runtime.run(algorithm, job.data, job.partitions)
