import json
import threading
import unittest
import urllib.request

from distalgo.cli import _build_server
from distalgo.core.benchmark import BenchmarkRunner
from distalgo.core.job import JobRunner
from distalgo.core.report import ProjectReport
from distalgo.core.runtime import LocalRuntime
from distalgo.core.server import DistAlgoHTTPApp


class FinalCompletionTest(unittest.TestCase):
    def test_actual_http_server_serves_health_algorithms_jobs_and_metrics(self):
        app = DistAlgoHTTPApp(JobRunner(LocalRuntime.in_memory()))
        try:
            server = _build_server(app, "127.0.0.1", 0)
        except PermissionError as exc:
            self.skipTest(f"socket bind is not permitted in this sandbox: {exc}")
        port = server.server_address[1]
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            health = urllib.request.urlopen(f"http://127.0.0.1:{port}/healthz", timeout=5)
            algorithms = urllib.request.urlopen(f"http://127.0.0.1:{port}/algorithms", timeout=5)
            request = urllib.request.Request(
                f"http://127.0.0.1:{port}/jobs",
                data=json.dumps({"algorithm": "sssp", "params": {"source": 1}, "data": [[1, 2, 1.0]]}).encode(
                    "utf-8"
                ),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            job = urllib.request.urlopen(request, timeout=5)
            metrics = urllib.request.urlopen(f"http://127.0.0.1:{port}/metrics", timeout=5)

            self.assertEqual(health.status, 200)
            self.assertIn("sssp", algorithms.read().decode("utf-8"))
            self.assertIn('"state": "completed"', job.read().decode("utf-8"))
            self.assertIn("distalgo_jobs_total", metrics.read().decode("utf-8"))
        finally:
            server.shutdown()
            server.server_close()

    def test_benchmark_runner_returns_stable_summary(self):
        summary = BenchmarkRunner().run_default()

        self.assertGreaterEqual(summary["jobs"], 3)
        self.assertGreater(summary["total_iterations"], 0)
        self.assertIn("pagerank", summary["algorithms"])
        self.assertIn("sssp", summary["algorithms"])

    def test_project_report_marks_local_completion_and_external_gaps(self):
        report = ProjectReport().render()

        self.assertIn("Local project completion: 100%", report)
        self.assertIn("Remote RTX 5090 host/CUDA smoke validation: passed", report)
        self.assertIn("Remote K3s GPU pod validation: passed", report)
        self.assertIn("Remote K3s/KubeRay CPU RayCluster execution: passed", report)
        self.assertIn("Ray actor fractional GPU resource seam: implemented and locally tested", report)
        self.assertIn("GPU algorithm kernels", report)
        self.assertIn("External production validation remaining", report)
        self.assertIn("Multi-GPU NCCL", report)


if __name__ == "__main__":
    unittest.main()
