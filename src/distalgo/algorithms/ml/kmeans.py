from __future__ import annotations

import math
from typing import List, Sequence, Tuple

from distalgo.algorithms.base import Algorithm
from distalgo.core.models import AlgorithmResult, AlgorithmSpec, ExecutionModel

Point = Tuple[float, ...]


class KMeans(Algorithm):
    def __init__(self, k: int, max_iterations: int = 100, tolerance: float = 1e-4):
        if k <= 0:
            raise ValueError("k must be positive")
        self.k = k
        self.max_iterations = max_iterations
        self.tolerance = tolerance
        self.spec = AlgorithmSpec(
            name="kmeans",
            family="ml.clustering",
            execution_model=ExecutionModel.AGGREGATION,
            communication="allreduce_or_coordinator",
            checkpoint="iteration",
        )

    def run(self, data: Sequence[Point], partitions: int) -> AlgorithmResult:
        points = [tuple(float(value) for value in point) for point in data]
        if len(points) < self.k:
            raise ValueError("k cannot exceed number of points")

        centers = list(points[: self.k])
        assignments: List[int] = [0 for _ in points]
        converged = False
        iterations = 0

        for iteration in range(1, self.max_iterations + 1):
            assignments = [self._nearest(point, centers) for point in points]
            next_centers = []
            for cluster in range(self.k):
                members = [point for point, assigned in zip(points, assignments) if assigned == cluster]
                if not members:
                    next_centers.append(centers[cluster])
                    continue
                dimensions = len(members[0])
                next_centers.append(
                    tuple(sum(point[index] for point in members) / len(members) for index in range(dimensions))
                )

            shift = sum(self._distance(left, right) for left, right in zip(centers, next_centers))
            centers = next_centers
            iterations = iteration
            if self.tolerance > 0 and shift <= self.tolerance:
                converged = True
                break

        return AlgorithmResult(
            algorithm=self.spec.name,
            iterations=iterations,
            converged=converged,
            output={"centers": centers, "assignments": assignments},
            metrics={"clusters": float(self.k), "points": float(len(points))},
        )

    def _nearest(self, point: Point, centers: Sequence[Point]) -> int:
        distances = [self._distance(point, center) for center in centers]
        return min(range(len(distances)), key=distances.__getitem__)

    @staticmethod
    def _distance(left: Point, right: Point) -> float:
        return math.sqrt(sum((a - b) ** 2 for a, b in zip(left, right)))
