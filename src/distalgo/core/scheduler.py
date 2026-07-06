from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from enum import Enum
from typing import Any, Deque, Dict, Optional
from uuid import uuid4

from distalgo.core.job import AlgorithmJob, JobRunner
from distalgo.core.models import AlgorithmResult


class JobState(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class JobStatus:
    job_id: str
    state: JobState
    result: Optional[AlgorithmResult] = None
    error: Optional[str] = None


class FifoScheduler:
    def __init__(self, runner: JobRunner):
        self.runner = runner
        self.queue: Deque[str] = deque()
        self.jobs: Dict[str, AlgorithmJob] = {}
        self.statuses: Dict[str, JobStatus] = {}

    def submit(self, payload: Dict[str, Any]) -> str:
        job_id = str(uuid4())
        job = AlgorithmJob(
            algorithm=payload["algorithm"],
            params=dict(payload.get("params", {})),
            partitions=int(payload.get("partitions", 1)),
            data=payload["data"],
        )
        self.jobs[job_id] = job
        self.statuses[job_id] = JobStatus(job_id=job_id, state=JobState.QUEUED)
        self.queue.append(job_id)
        return job_id

    def run_next(self) -> Optional[JobStatus]:
        if not self.queue:
            return None
        job_id = self.queue.popleft()
        self.statuses[job_id].state = JobState.RUNNING
        try:
            result = self.runner.run(self.jobs[job_id])
            self.statuses[job_id] = JobStatus(job_id=job_id, state=JobState.COMPLETED, result=result)
        except Exception as exc:
            self.statuses[job_id] = JobStatus(job_id=job_id, state=JobState.FAILED, error=str(exc))
        return self.statuses[job_id]

    def status(self, job_id: str) -> JobStatus:
        return self.statuses[job_id]
