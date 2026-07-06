import csv
import json
import tempfile
import unittest
from pathlib import Path

from distalgo.algorithms.graph.pagerank import PageRank
from distalgo.core.api import JobAPI
from distalgo.core.checkpoint import MemoryCheckpointStore
from distalgo.core.job import JobRunner, load_job
from distalgo.core.resume import ResumeRuntime
from distalgo.core.scheduler import JobState, JobStatus, FifoScheduler
from distalgo.core.runtime import LocalRuntime


class ServiceFeatureTest(unittest.TestCase):
    def test_load_job_supports_edge_csv_data_path(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            edges_path = Path(tmpdir) / "edges.csv"
            with edges_path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=["src", "dst"])
                writer.writeheader()
                writer.writerow({"src": "1", "dst": "2"})
                writer.writerow({"src": "2", "dst": "3"})

            job_path = Path(tmpdir) / "job.json"
            job_path.write_text(
                json.dumps(
                    {
                        "algorithm": "pagerank",
                        "params": {"max_iterations": 5},
                        "data_path": str(edges_path),
                        "data_format": "edges_csv",
                    }
                ),
                encoding="utf-8",
            )

            job = load_job(job_path)

            self.assertEqual(job.data, [(1, 2), (2, 3)])

    def test_fifo_scheduler_tracks_queued_running_and_completed_jobs(self):
        scheduler = FifoScheduler(JobRunner(LocalRuntime.in_memory()))
        first = scheduler.submit({"algorithm": "pagerank", "data": [(1, 2), (2, 1)]})
        second = scheduler.submit({"algorithm": "kmeans", "params": {"k": 1}, "data": [(1.0, 2.0)]})

        self.assertEqual(scheduler.status(first).state, JobState.QUEUED)
        scheduler.run_next()
        scheduler.run_next()

        self.assertEqual(scheduler.status(first).state, JobState.COMPLETED)
        self.assertEqual(scheduler.status(second).state, JobState.COMPLETED)
        self.assertEqual(scheduler.status(first).result.algorithm, "pagerank")

    def test_job_api_runs_payload_and_returns_jsonable_result(self):
        api = JobAPI(JobRunner(LocalRuntime.in_memory()))

        response = api.run_json({"algorithm": "k_core", "params": {"k": 1}, "data": [(1, 2)]})

        self.assertEqual(response["state"], "completed")
        self.assertEqual(response["result"]["algorithm"], "k_core")

    def test_resume_runtime_returns_checkpointed_result_without_recomputing(self):
        checkpoint_store = MemoryCheckpointStore()
        checkpoint_store.save("pagerank", 3, {"scores": {1: 0.75, 2: 0.25}})
        runtime = ResumeRuntime(
            base_runtime=LocalRuntime(checkpoint_store=checkpoint_store),
            checkpoint_store=checkpoint_store,
        )

        result = runtime.resume_or_run(PageRank(max_iterations=3), [(1, 2), (2, 1)], partitions=1, iteration=3)

        self.assertEqual(result.output["scores"][1], 0.75)
        self.assertEqual(result.iterations, 3)
        self.assertTrue(result.converged)

    def test_service_deployment_includes_api_and_gpu_worker_manifest(self):
        service = Path("deploy/kubernetes/distalgo-service.yaml").read_text(encoding="utf-8")
        gpu_cluster = Path("deploy/kuberay/raycluster-gpu.yaml").read_text(encoding="utf-8")

        self.assertIn("kind: Service", service)
        self.assertIn("distalgo", service)
        self.assertIn("nvidia.com/gpu", gpu_cluster)


if __name__ == "__main__":
    unittest.main()
