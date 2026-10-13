import csv
from pathlib import Path
import random
import sys
import tempfile
import unittest

import networkx as nx


SRC_ROOT = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC_ROOT))

import kResilienceTrees as trees


class NodeFailureHelpersTest(unittest.TestCase):
    def test_source_and_destination_are_not_failure_candidates(self):
        graph = nx.path_graph(5)

        candidates = trees.getNodeFailureCandidates(graph, s=0, d=4)

        self.assertEqual(candidates, [1, 2, 3])

    def test_random_node_failures_exclude_source_and_destination(self):
        graph = nx.complete_graph(8)
        random.seed(123)

        failed_nodes = trees.getRandomNodeFailures(graph, s=0, d=7, nodesToFail=4)

        self.assertEqual(len(failed_nodes), 4)
        self.assertNotIn(0, failed_nodes)
        self.assertNotIn(7, failed_nodes)

    def test_node_failure_blocks_all_incident_edges_without_duplicates(self):
        graph = nx.Graph([(0, 1), (1, 2), (2, 3), (2, 4)])

        failed_edges = trees.nodeFailuresToEdgeFailures(graph, failed_nodes=[1, 2])
        failed_edge_sets = {frozenset(edge) for edge in failed_edges}

        self.assertEqual(
            failed_edge_sets,
            {
                frozenset((0, 1)),
                frozenset((1, 2)),
                frozenset((2, 3)),
                frozenset((2, 4)),
            },
        )
        self.assertEqual(len(failed_edges), len(failed_edge_sets))

    def test_edge_conversion_matches_removed_node_shortest_path(self):
        graph = nx.cycle_graph(6)
        failed_nodes = [2]
        failed_edges = trees.nodeFailuresToEdgeFailures(graph, failed_nodes)

        edge_based_length = trees.getTrueShortestPathLength(graph.copy(), 0, 4, failed_edges)
        node_removed_graph = graph.copy()
        node_removed_graph.remove_nodes_from(failed_nodes)
        node_based_length = nx.shortest_path_length(node_removed_graph, 0, 4)

        self.assertEqual(edge_based_length, node_based_length)

    def test_clustered_failures_start_next_to_destination_and_exclude_endpoints(self):
        graph = nx.Graph([(0, 1), (0, 2), (0, 3), (1, 4), (2, 5), (3, 6), (4, 7)])
        random.seed(123)

        failed_nodes = trees.getClusteredNodeFailures(
            graph,
            s=7,
            d=0,
            failureStart=1.0,
            failureDrop=0.5,
        )

        self.assertTrue({1, 2, 3}.issubset(failed_nodes))
        self.assertNotIn(0, failed_nodes)
        self.assertNotIn(7, failed_nodes)


class NodeFailureCsvTest(unittest.TestCase):
    def read_single_row(self, csv_path):
        with open(csv_path, newline="") as csv_file:
            rows = list(csv.DictReader(csv_file))
        self.assertEqual(len(rows), 1)
        return rows[0]

    def test_random_csv_records_failed_node_count_explicitly(self):
        with tempfile.TemporaryDirectory() as output_dir:
            csv_path = trees.main(
                rep=1,
                p=2,
                no_nodes=25,
                failureModel="random",
                edgeFailFactorPar=1.0,
                output_dir=output_dir,
                seed=123,
            )

            row = self.read_single_row(csv_path)

        self.assertEqual(row["nrFailedNodes"], "1")
        self.assertEqual(row["nrFails"], "1")

    def test_clustered_csv_records_failed_node_count_explicitly(self):
        with tempfile.TemporaryDirectory() as output_dir:
            csv_path = trees.main(
                rep=1,
                p=2,
                no_nodes=25,
                failureModel="clustered",
                failurePercentPar=0.9,
                failureDropPar=0.3,
                output_dir=output_dir,
                seed=123,
            )

            row = self.read_single_row(csv_path)

        self.assertGreater(int(row["nrFailedNodes"]), 0)
        self.assertEqual(row["nrFails"], "")


if __name__ == "__main__":
    unittest.main()
