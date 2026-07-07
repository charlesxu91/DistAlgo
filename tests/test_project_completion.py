import csv
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from distalgo.algorithms.graph.bfs import BFS
from distalgo.algorithms.graph.k_core import KCore
from distalgo.algorithms.graph.label_propagation import LabelPropagation
from distalgo.algorithms.graph.triangle_count import TriangleCount
from distalgo.algorithms.ml.linear_regression import LinearRegression
from distalgo.algorithms.registry import AlgorithmRegistry
from distalgo.core.data import load_edges_csv, load_json_dataset
from distalgo.core.partition import hash_partition_edges
from distalgo.core.partitioned_runtime import PartitionedLocalRuntime


class ProjectCompletionTest(unittest.TestCase):
    def test_hash_partition_edges_is_deterministic_and_covers_all_edges(self):
        edges = [(1, 2), (2, 3), (4, 5), (5, 6), (8, 1)]

        first = hash_partition_edges(edges, partitions=3)
        second = hash_partition_edges(edges, partitions=3)

        self.assertEqual(first, second)
        self.assertEqual(sum(len(part.edges) for part in first), len(edges))
        self.assertEqual(sorted(part.partition_id for part in first), [0, 1, 2])
        self.assertTrue(any(part.boundary_edges for part in first))

    def test_partitioned_runtime_records_partition_metrics(self):
        runtime = PartitionedLocalRuntime.in_memory()

        result = runtime.run(BFS(source=1), [(1, 2), (2, 3), (4, 5)], partitions=2)

        self.assertEqual(result.output["distances"][3], 2)
        self.assertEqual(result.metrics["partitions"], 2.0)
        self.assertGreaterEqual(result.metrics["boundary_edges"], 0.0)

    def test_bfs_label_propagation_triangle_count_and_k_core(self):
        graph = [(1, 2), (2, 3), (1, 3), (3, 4), (10, 11)]
        runtime = PartitionedLocalRuntime.in_memory()

        bfs = runtime.run(BFS(source=1), graph, partitions=2)
        labels = runtime.run(LabelPropagation(max_iterations=10), graph, partitions=2)
        triangles = runtime.run(TriangleCount(), graph, partitions=2)
        core = runtime.run(KCore(k=2), graph, partitions=2)

        self.assertEqual(bfs.output["distances"][4], 2)
        self.assertEqual(labels.output["labels"][1], labels.output["labels"][4])
        self.assertEqual(triangles.output["triangle_count"], 1)
        self.assertEqual(core.output["nodes"], [1, 2, 3])

    def test_linear_regression_fits_simple_line(self):
        result = PartitionedLocalRuntime.in_memory().run(
            LinearRegression(learning_rate=0.05, max_iterations=200),
            [([0.0], 1.0), ([1.0], 3.0), ([2.0], 5.0), ([3.0], 7.0)],
            partitions=2,
        )

        self.assertAlmostEqual(result.output["weights"][0], 2.0, places=1)
        self.assertAlmostEqual(result.output["bias"], 1.0, places=1)

    def test_data_loaders_read_csv_edges_and_json_dataset(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = Path(tmpdir) / "edges.csv"
            with csv_path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=["src", "dst"])
                writer.writeheader()
                writer.writerow({"src": "1", "dst": "2"})
                writer.writerow({"src": "2", "dst": "3"})

            json_path = Path(tmpdir) / "dataset.json"
            json_path.write_text(json.dumps([[1, 2], [2, 3]]), encoding="utf-8")

            self.assertEqual(load_edges_csv(csv_path), [(1, 2), (2, 3)])
            self.assertEqual(load_json_dataset(json_path), [[1, 2], [2, 3]])

    def test_registry_contains_project_completion_algorithms(self):
        names = AlgorithmRegistry.default().names()

        for name in [
            "bfs",
            "label_propagation",
            "triangle_count",
            "k_core",
            "linear_regression",
        ]:
            self.assertIn(name, names)

    def test_cli_lists_algorithms(self):
        completed = subprocess.run(
            [sys.executable, "-m", "distalgo.cli", "list-algorithms"],
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("louvain", completed.stdout)
        self.assertIn("linear_regression", completed.stdout)

    def test_cli_lists_algorithm_status(self):
        completed = subprocess.run(
            [sys.executable, "-m", "distalgo.cli", "list-algorithms", "--status"],
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("distributed_verified", completed.stdout)
        self.assertIn("kmeans", completed.stdout)

    def test_deployment_manifests_include_kuberay_and_prometheus(self):
        ray_cluster = Path("deploy/kuberay/raycluster.yaml").read_text(encoding="utf-8")
        prometheus = Path("deploy/observability/prometheus-config.yaml").read_text(encoding="utf-8")
        gpu_smoke = Path("scripts/remote_gpu_ray_smoke.sh").read_text(encoding="utf-8")
        volcano_queue = Path("deploy/volcano-vgpu/queue.yaml").read_text(encoding="utf-8")
        volcano_job = Path("deploy/volcano-vgpu/vcjob-vgpu-gang.yaml").read_text(encoding="utf-8")
        volcano_doc = Path("docs/gpu-virtualization-volcano-hami.md").read_text(encoding="utf-8")

        self.assertIn("kind: RayCluster", ray_cluster)
        self.assertIn("distalgo-head", ray_cluster)
        self.assertIn("/metrics", prometheus)
        self.assertIn("num_gpus=0.25", gpu_smoke)
        self.assertIn("nvidia.com/gpu: \"1\"", gpu_smoke)
        self.assertIn("kind: Queue", volcano_queue)
        self.assertIn("volcano.sh/vgpu-memory", volcano_queue)
        self.assertIn("schedulerName: volcano", volcano_job)
        self.assertIn("minAvailable: 2", volcano_job)
        self.assertIn("HAMi-core", volcano_doc)


if __name__ == "__main__":
    unittest.main()
