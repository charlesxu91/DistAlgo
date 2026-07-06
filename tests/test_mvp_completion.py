import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from distalgo.algorithms.graph.louvain import Louvain
from distalgo.backends.ray_runtime import RayRuntime
from distalgo.core.job import JobRunner, load_job
from distalgo.core.object_checkpoint import ObjectCheckpointStore
from distalgo.core.prometheus import MetricsHTTPServer
from distalgo.core.runtime import LocalRuntime


class FakeObjectClient:
    def __init__(self):
        self.objects = {}

    def put_object(self, bucket, key, body):
        self.objects[(bucket, key)] = body

    def get_object(self, bucket, key):
        return self.objects[(bucket, key)]

    def object_exists(self, bucket, key):
        return (bucket, key) in self.objects


class FakeRay:
    def __init__(self):
        self.initialized = False

    def init(self, **kwargs):
        self.initialized = True
        self.init_kwargs = kwargs

    def shutdown(self):
        self.initialized = False


class MVPCompletionTest(unittest.TestCase):
    def test_louvain_detects_two_dense_communities(self):
        graph = [
            (1, 2),
            (2, 3),
            (1, 3),
            (10, 11),
            (11, 12),
            (10, 12),
            (3, 10),
        ]

        result = LocalRuntime.in_memory().run(Louvain(max_passes=8), graph, partitions=2)
        communities = result.output["communities"]

        self.assertEqual(communities[1], communities[2])
        self.assertEqual(communities[2], communities[3])
        self.assertEqual(communities[10], communities[11])
        self.assertEqual(communities[11], communities[12])
        self.assertNotEqual(communities[1], communities[10])
        self.assertIn("modularity", result.output)

    def test_job_runner_loads_json_job_and_dispatches_registered_algorithm(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            job_path = Path(tmpdir) / "job.json"
            job_path.write_text(
                json.dumps(
                    {
                        "algorithm": "kmeans",
                        "params": {"k": 2, "max_iterations": 4, "tolerance": 0.0},
                        "partitions": 2,
                        "data": [[0.0, 0.0], [0.1, 0.0], [9.9, 10.0], [10.0, 10.1]],
                    }
                ),
                encoding="utf-8",
            )

            job = load_job(job_path)
            result = JobRunner(LocalRuntime.in_memory()).run(job)

            self.assertEqual(result.algorithm, "kmeans")
            self.assertEqual(len(result.output["centers"]), 2)

    def test_cli_runs_job_and_writes_json_result(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            job_path = Path(tmpdir) / "job.json"
            output_path = Path(tmpdir) / "result.json"
            job_path.write_text(
                json.dumps(
                    {
                        "algorithm": "pagerank",
                        "params": {"max_iterations": 10},
                        "partitions": 2,
                        "data": [[1, 2], [2, 3], [3, 1], [1, 3]],
                    }
                ),
                encoding="utf-8",
            )

            completed = subprocess.run(
                [sys.executable, "-m", "distalgo.cli", "run", str(job_path), "--output", str(output_path)],
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            payload = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["algorithm"], "pagerank")
            self.assertIn("scores", payload["output"])

    def test_ray_runtime_uses_injected_ray_and_preserves_algorithm_result(self):
        fake_ray = FakeRay()
        runtime = RayRuntime(ray_module=fake_ray)

        result = runtime.run(Louvain(max_passes=3), [(1, 2), (2, 3), (10, 11)], partitions=2)

        self.assertTrue(fake_ray.initialized)
        self.assertEqual(result.algorithm, "louvain")

    def test_object_checkpoint_store_supports_minio_style_client(self):
        client = FakeObjectClient()
        store = ObjectCheckpointStore(client=client, bucket="checkpoints", prefix="jobs")

        store.save("pagerank", 2, {"scores": {1: 0.5, 2: 0.5}})

        self.assertTrue(store.exists("pagerank", 2))
        self.assertEqual(store.load("pagerank", 2)["scores"][1], 0.5)

    def test_metrics_http_server_exposes_prometheus_text(self):
        runtime = LocalRuntime.in_memory()
        runtime.run(Louvain(max_passes=2), [(1, 2), (2, 3)], partitions=1)

        server = MetricsHTTPServer(runtime.metrics)
        body = server.render()

        self.assertIn("distalgo_jobs_total", body)
        self.assertIn('algorithm="louvain"', body)


if __name__ == "__main__":
    unittest.main()
