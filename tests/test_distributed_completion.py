import json
import tempfile
import unittest
from pathlib import Path

from distalgo.algorithms.graph.sssp import SSSP
from distalgo.algorithms.registry import AlgorithmRegistry
from distalgo.core.checkpoint import FileCheckpointStore
from distalgo.core.faults import FaultInjectingRuntime, KillOnceFault
from distalgo.core.job import AlgorithmJob, JobRunner
from distalgo.core.runtime import LocalRuntime
from distalgo.core.server import DistAlgoHTTPApp
from distalgo.core.superstep import PregelRuntime


class DistributedCompletionTest(unittest.TestCase):
    def test_pregel_runtime_executes_sssp_with_superstep_metrics(self):
        result = PregelRuntime().run(
            SSSP(source=1),
            [(1, 2, 2.0), (1, 3, 8.0), (2, 3, 1.0), (3, 4, 2.0)],
            partitions=2,
        )

        self.assertEqual(result.output["distances"][4], 5.0)
        self.assertGreaterEqual(result.iterations, 3)
        self.assertEqual(result.metrics["partitions"], 2.0)
        self.assertGreater(result.metrics["messages_sent"], 0.0)

    def test_sssp_is_registered_and_runs_from_json_job(self):
        result = JobRunner(LocalRuntime.in_memory()).run(
            AlgorithmJob(
                algorithm="sssp",
                params={"source": 1},
                partitions=2,
                data=[(1, 2, 2.0), (2, 3, 1.0)],
            )
        )

        self.assertEqual(result.output["distances"][3], 3.0)

    def test_registry_creates_sssp_algorithm(self):
        algorithm = AlgorithmRegistry.default().create("sssp", {"source": 1})

        self.assertEqual(algorithm.spec.name, "sssp")

    def test_http_app_handles_health_algorithms_jobs_and_metrics(self):
        app = DistAlgoHTTPApp(JobRunner(LocalRuntime.in_memory()))

        health = app.handle("GET", "/healthz")
        algorithms = app.handle("GET", "/algorithms")
        job = app.handle(
            "POST",
            "/jobs",
            json.dumps({"algorithm": "k_core", "params": {"k": 1}, "data": [[1, 2]]}),
        )
        metrics = app.handle("GET", "/metrics")

        self.assertEqual(health.status, 200)
        self.assertIn("sssp", algorithms.json["algorithms"])
        self.assertEqual(job.json["state"], "completed")
        self.assertIn("distalgo_jobs_total", metrics.body)

    def test_fault_injecting_runtime_recovers_from_single_kill_with_checkpoint(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            checkpoint_store = FileCheckpointStore(Path(tmpdir))
            runtime = FaultInjectingRuntime(
                base_runtime=LocalRuntime(checkpoint_store=checkpoint_store),
                checkpoint_store=checkpoint_store,
                fault=KillOnceFault("simulated worker loss"),
            )

            result = runtime.run_with_recovery(SSSP(source=1), [(1, 2, 1.0), (2, 3, 1.0)], partitions=2)

            self.assertEqual(result.output["distances"][3], 2.0)
            self.assertEqual(result.metrics["retries"], 1.0)

    def test_compose_file_contains_minio_prometheus_and_distalgo(self):
        compose = Path("deploy/docker-compose.yaml").read_text(encoding="utf-8")

        self.assertIn("minio:", compose)
        self.assertIn("prometheus:", compose)
        self.assertIn("distalgo:", compose)


if __name__ == "__main__":
    unittest.main()
