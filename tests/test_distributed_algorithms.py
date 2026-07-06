import unittest

from distalgo.algorithms.graph.connected_components import ConnectedComponents
from distalgo.algorithms.graph.k_hop import KHop
from distalgo.algorithms.graph.louvain import Louvain
from distalgo.algorithms.graph.pagerank import PageRank
from distalgo.algorithms.ml.kmeans import KMeans
from distalgo.algorithms.registry import AlgorithmRegistry
from distalgo.core.partitioned_runtime import PartitionedLocalRuntime


class DistributedAlgorithmStatusTest(unittest.TestCase):
    def test_registry_exposes_distributed_verification_metadata(self):
        registry = AlgorithmRegistry.default()
        metadata = {item.name: item for item in registry.metadata_all()}

        self.assertTrue(metadata["pagerank"].distributed_verified)
        self.assertEqual(metadata["kmeans"].status, "distributed_verified")
        self.assertIn("partitioned", metadata["louvain"].verification_level)

    def test_remaining_graph_algorithms_run_on_partitioned_runtime(self):
        runtime = PartitionedLocalRuntime.in_memory()
        graph = [(1, 2), (2, 3), (3, 1), (10, 11), (11, 12), (12, 10)]

        pagerank = runtime.run(PageRank(max_iterations=10), graph, partitions=3)
        connected = runtime.run(ConnectedComponents(max_iterations=10), graph, partitions=3)
        k_hop = runtime.run(KHop(sources=[1], hops=2), graph, partitions=3)
        louvain = runtime.run(Louvain(max_passes=4), graph, partitions=3)

        self.assertAlmostEqual(sum(pagerank.output["scores"].values()), 1.0, places=6)
        self.assertEqual(connected.output["components"][1], connected.output["components"][3])
        self.assertEqual(k_hop.output["neighbors"][1], [2, 3])
        self.assertGreaterEqual(len(set(louvain.output["communities"].values())), 2)

    def test_kmeans_runs_on_partitioned_runtime(self):
        result = PartitionedLocalRuntime.in_memory().run(
            KMeans(k=2, max_iterations=8),
            [(0.0, 0.0), (0.2, 0.1), (8.0, 8.0), (8.2, 8.1)],
            partitions=2,
        )

        self.assertEqual(len(result.output["centers"]), 2)
        self.assertEqual(result.metrics["partitions"], 2.0)


if __name__ == "__main__":
    unittest.main()
