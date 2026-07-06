from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict


class ExecutionModel(str, Enum):
    AGGREGATION = "aggregation"
    GRAPH_MESSAGE = "graph_message"
    MAP_REDUCE_SHUFFLE = "map_reduce_shuffle"
    PARAMETER_SERVER = "parameter_server"
    ALLREDUCE = "allreduce"
    PIPELINE = "pipeline"
    ACTOR_PEER = "actor_peer"


@dataclass(frozen=True)
class AlgorithmSpec:
    name: str
    family: str
    execution_model: ExecutionModel
    communication: str
    checkpoint: str
    requires_gpu: bool = False


@dataclass(frozen=True)
class AlgorithmResult:
    algorithm: str
    iterations: int
    converged: bool
    output: Dict[str, Any]
    metrics: Dict[str, float] = field(default_factory=dict)
