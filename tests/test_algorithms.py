import unittest

from distalgo.algorithms.graph.connected_components import ConnectedComponents
from distalgo.algorithms.graph.k_hop import KHop
from distalgo.algorithms.graph.pagerank import PageRank
from distalgo.algorithms.ml.kmeans import KMeans
from distalgo.core.runtime import LocalRuntime


class AlgorithmPluginTest(unittest.TestCase):
    def test_pagerank_scores_sum_to_one_and_rank_center_node_highest(self):
        graph = [(1, 2), (2, 3), (3, 1), (2, 1), (1, 3)]
        result = LocalRuntime.in_memory().run(PageRank(max_iterations=30), graph, partitions=2)
        scores = result.output["scores"]

        self.assertAlmostEqual(sum(scores.values()), 1.0, places=6)
        self.assertGreater(scores[1], scores[2])
        self.assertGreater(scores[1], scores[3])

    def test_connected_components_finds_disconnected_subgraphs(self):
        graph = [(1, 2), (2, 3), (10, 11)]
        result = LocalRuntime.in_memory().run(ConnectedComponents(max_iterations=10), graph, partitions=2)

        components = result.output["components"]
        self.assertEqual(components[1], components[2])
        self.assertEqual(components[2], components[3])
        self.assertEqual(components[10], components[11])
        self.assertNotEqual(components[1], components[10])

    def test_k_hop_returns_reachable_neighbors_within_depth(self):
        graph = [(1, 2), (2, 3), (3, 4), (2, 5)]
        result = LocalRuntime.in_memory().run(KHop(sources=[1], hops=2), graph, partitions=2)

        self.assertEqual(result.output["neighbors"][1], [2, 3, 5])

    def test_kmeans_clusters_points_and_reports_assignments(self):
        points = [(0.0, 0.0), (0.1, -0.1), (9.9, 10.1), (10.0, 10.0)]
        result = LocalRuntime.in_memory().run(KMeans(k=2, max_iterations=6, tolerance=0.0), points, partitions=2)

        centers = sorted(result.output["centers"])
        self.assertAlmostEqual(centers[0][0], 0.05, places=2)
        self.assertAlmostEqual(centers[0][1], -0.05, places=2)
        self.assertAlmostEqual(centers[1][0], 9.95, places=2)
        self.assertAlmostEqual(centers[1][1], 10.05, places=2)
        self.assertEqual(len(result.output["assignments"]), 4)


if __name__ == "__main__":
    unittest.main()
