import tempfile
import unittest
from pathlib import Path

from distalgo.algorithms.ml.kmeans import KMeans
from distalgo.core.checkpoint import FileCheckpointStore
from distalgo.core.metrics import MetricsRegistry
from distalgo.core.models import ExecutionModel
from distalgo.core.runtime import LocalRuntime


class CoreRuntimeTest(unittest.TestCase):
    def test_runtime_executes_algorithm_and_records_checkpoint_and_metrics(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            checkpoint_store = FileCheckpointStore(Path(tmpdir))
            metrics = MetricsRegistry()
            runtime = LocalRuntime(checkpoint_store=checkpoint_store, metrics=metrics)
            algorithm = KMeans(k=2, max_iterations=5, tolerance=0.0)

            result = runtime.run(
                algorithm,
                data=[(0.0, 0.0), (0.2, 0.1), (9.8, 10.1), (10.0, 10.0)],
                partitions=2,
            )

            self.assertEqual(algorithm.spec.execution_model, ExecutionModel.AGGREGATION)
            self.assertEqual(result.algorithm, "kmeans")
            self.assertEqual(result.iterations, 5)
            self.assertEqual(len(result.output["centers"]), 2)
            self.assertTrue(checkpoint_store.exists("kmeans", 5))
            rendered_metrics = metrics.to_prometheus_text()
            self.assertIn("distalgo_iterations_total", rendered_metrics)
            self.assertIn('algorithm="kmeans"', rendered_metrics)


if __name__ == "__main__":
    unittest.main()
