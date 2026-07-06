from __future__ import annotations

from typing import Sequence, Tuple

from distalgo.algorithms.base import Algorithm
from distalgo.core.models import AlgorithmResult, AlgorithmSpec, ExecutionModel

Sample = Tuple[Sequence[float], float]


class LinearRegression(Algorithm):
    def __init__(self, learning_rate: float = 0.01, max_iterations: int = 500):
        self.learning_rate = learning_rate
        self.max_iterations = max_iterations
        self.spec = AlgorithmSpec(
            name="linear_regression",
            family="ml.regression",
            execution_model=ExecutionModel.AGGREGATION,
            communication="allreduce_or_coordinator",
            checkpoint="iteration",
        )

    def run(self, data: Sequence[Sample], partitions: int) -> AlgorithmResult:
        samples = [(tuple(float(v) for v in features), float(target)) for features, target in data]
        if not samples:
            raise ValueError("linear regression requires at least one sample")
        dimensions = len(samples[0][0])
        weights = [0.0 for _ in range(dimensions)]
        bias = 0.0
        n = float(len(samples))

        for _ in range(self.max_iterations):
            grad_w = [0.0 for _ in range(dimensions)]
            grad_b = 0.0
            for features, target in samples:
                prediction = sum(w * x for w, x in zip(weights, features)) + bias
                error = prediction - target
                for index, value in enumerate(features):
                    grad_w[index] += error * value
                grad_b += error
            for index in range(dimensions):
                weights[index] -= self.learning_rate * grad_w[index] / n
            bias -= self.learning_rate * grad_b / n

        mse = sum(
            (sum(w * x for w, x in zip(weights, features)) + bias - target) ** 2
            for features, target in samples
        ) / n
        return AlgorithmResult(
            algorithm=self.spec.name,
            iterations=self.max_iterations,
            converged=True,
            output={"weights": weights, "bias": bias, "mse": mse},
            metrics={"samples": float(len(samples)), "mse": mse},
        )
