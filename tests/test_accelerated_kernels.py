import unittest

from distalgo.algorithms.graph.pagerank import PageRank
from distalgo.algorithms.ml.kmeans import KMeans
from distalgo.backends.accelerated import bfs_frontier_kernel, kmeans_kernel, pagerank_kernel
from distalgo.core.runtime import LocalRuntime


class AcceleratedKernelTest(unittest.TestCase):
    def test_kmeans_kernel_matches_expected_clusters_with_optional_gpu_backend(self):
        result = kmeans_kernel(
            [(0.0, 0.0), (0.1, 0.0), (10.0, 10.0), (10.1, 10.0)],
            k=2,
            max_iterations=10,
            tolerance=1e-8,
            prefer_gpu=True,
        )

        self.assertEqual(len(result.output["centers"]), 2)
        self.assertEqual(sorted(result.output["assignments"]), [0, 0, 1, 1])
        self.assertIn(result.device, {"cpu", "gpu"})

    def test_pagerank_kernel_produces_normalized_scores(self):
        result = pagerank_kernel([(1, 2), (2, 3), (3, 1), (1, 3)], 0.85, 20, 1e-8, prefer_gpu=True)

        self.assertEqual(set(result.output["scores"]), {1, 2, 3})
        self.assertAlmostEqual(sum(result.output["scores"].values()), 1.0)

    def test_bfs_frontier_kernel_reports_distances(self):
        result = bfs_frontier_kernel([(1, 2), (2, 3), (1, 4)], source=1, prefer_gpu=True)

        self.assertEqual(result.output["distances"][3], 2)
        self.assertEqual(result.output["distances"][4], 1)

    def test_algorithms_can_use_accelerated_backend_without_changing_output_shape(self):
        runtime = LocalRuntime.in_memory()

        kmeans = runtime.run(
            KMeans(k=2, use_gpu=True),
            [(0.0, 0.0), (0.1, 0.0), (10.0, 10.0), (10.1, 10.0)],
            partitions=2,
        )
        pagerank = runtime.run(PageRank(use_gpu=True), [(1, 2), (2, 3), (3, 1)], partitions=2)

        self.assertIn("centers", kmeans.output)
        self.assertIn("scores", pagerank.output)
        self.assertEqual(kmeans.metrics["accelerated_backend"], 1.0)
        self.assertEqual(pagerank.metrics["accelerated_backend"], 1.0)


if __name__ == "__main__":
    unittest.main()
