import csv
from pathlib import Path
import random
import sys
import tempfile
import unittest

import networkx as nx


SRC_ROOT = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC_ROOT))

import kResiliencePaths as ndp


class NodeDisjointPathTest(unittest.TestCase):
    def setUp(self):
        self.graph = nx.Graph(
            [
                (0, 1),
                (1, 4),
                (0, 2),
                (2, 3),
                (3, 4),
                (1, 2),
            ]
        )

    def test_paths_only_share_source_and_destination(self):
        paths = ndp.getNodeDisjointPaths(self.graph, s=0, d=4)
        internal_nodes = [set(path[1:-1]) for path in paths]

        self.assertEqual(len(paths), 2)
        self.assertTrue(internal_nodes[0].isdisjoint(internal_nodes[1]))

    def test_edge_disjoint_baseline_uses_at_least_as_many_paths(self):
        edge_disjoint_paths = ndp.getEdgeDisjointPaths(self.graph, s=0, d=4)
        node_disjoint_paths = ndp.getNodeDisjointPaths(self.graph, s=0, d=4)

        self.assertGreaterEqual(len(edge_disjoint_paths), len(node_disjoint_paths))

    def test_shortest_node_disjoint_path_is_tried_first(self):
        hops, _, route, attributes = ndp.kResiliencePaths(0, 4, [], self.graph)

        self.assertEqual(hops, 2)
        self.assertEqual(route, [(0, 1), (1, 4)])
        self.assertEqual(attributes, ["1", "2"])

    def test_link_failure_falls_back_to_second_node_disjoint_path(self):
        hops, _, route, _ = ndp.kResiliencePaths(0, 4, [(1, 4)], self.graph)

        self.assertGreater(hops, 0)
        self.assertEqual(route[-1][1], 4)

    def test_node_failure_falls_back_to_unaffected_node_disjoint_path(self):
        failed_edges = ndp.nodeFailuresToEdgeFailures(self.graph, failed_nodes=[1])

        hops, _, route, _ = ndp.kResiliencePaths(0, 4, failed_edges, self.graph)

        self.assertGreater(hops, 0)
        self.assertEqual(route[-1][1], 4)
        self.assertNotIn(1, {node for edge in route for node in edge})

    def test_clustered_link_failures_start_at_destination_without_duplicates(self):
        graph = nx.Graph(
            [(0, 1), (0, 2), (0, 3), (1, 4), (2, 5), (3, 6)]
        )

        failed_edges = ndp.getClusteredLinkFailures(
            graph,
            destination=0,
            failure_start=1.0,
            failure_drop=1.0,
            rng=random.Random(123),
        )
        failed_edge_sets = {frozenset(edge) for edge in failed_edges}

        self.assertEqual(
            failed_edge_sets,
            {frozenset((0, 1)), frozenset((0, 2)), frozenset((0, 3))},
        )
        self.assertEqual(len(failed_edges), len(failed_edge_sets))

    def test_clustered_node_failures_start_next_to_destination_and_protect_endpoints(self):
        graph = nx.Graph(
            [(0, 1), (0, 2), (0, 3), (1, 4), (2, 5), (3, 6), (4, 7)]
        )

        failed_nodes = ndp.getClusteredNodeFailures(
            graph,
            source=7,
            destination=0,
            failure_start=1.0,
            failure_drop=1.0,
            rng=random.Random(123),
        )

        self.assertEqual(set(failed_nodes), {1, 2, 3})
        self.assertNotIn(0, failed_nodes)
        self.assertNotIn(7, failed_nodes)

    def test_cluster_parameters_reject_non_positive_drop(self):
        with self.assertRaises(ValueError):
            ndp.getClusteredLinkFailures(
                self.graph,
                destination=4,
                failure_start=0.9,
                failure_drop=0.0,
                rng=random.Random(123),
            )

    def test_failure_of_each_internal_path_returns_no_route(self):
        failed_edges = ndp.nodeFailuresToEdgeFailures(self.graph, failed_nodes=[1, 3])

        hops, _, route, _ = ndp.kResiliencePaths(0, 4, failed_edges, self.graph)

        self.assertEqual(hops, -1)
        self.assertNotIn(4, {node for edge in route for node in edge})

    def test_experiment_csvs_are_generated_by_k_resilience_paths(self):
        with tempfile.TemporaryDirectory() as output_dir:
            paths = [
                ndp.runExperiments(
                    runs=3,
                    failure_type=failure_type,
                    fail_factor=1.0,
                    output_dir=output_dir,
                    seed=123,
                )
                for failure_type in ("link", "node")
            ]

            rows_by_type = {}
            for path in paths:
                with open(path, newline="") as csv_file:
                    rows = list(csv.DictReader(csv_file))
                rows_by_type[rows[0]["failureType"]] = rows

        self.assertEqual(len(rows_by_type["link"]), 3)
        self.assertEqual(len(rows_by_type["node"]), 3)
        self.assertEqual(rows_by_type["link"][0]["nrFailedNodes"], "0")
        self.assertGreater(int(rows_by_type["node"][0]["nrFailedNodes"]), 0)
        self.assertEqual(rows_by_type["link"][0]["failFactor"], "1.0")

    def test_failure_factor_series_writes_one_csv_per_factor(self):
        with tempfile.TemporaryDirectory() as output_dir:
            args = ndp.parseArgs(
                [
                    "--runs", "2",
                    "--failure-type", "link",
                    "--fail-factor", "0", "0.5", "1",
                    "--output-dir", output_dir,
                    "--seed", "123",
                ]
            )
            paths = ndp.runFromArgs(args)

            rows_by_factor = {}
            for path in paths:
                with open(path, newline="") as csv_file:
                    rows = list(csv.DictReader(csv_file))
                rows_by_factor[rows[0]["failFactor"]] = rows

        self.assertEqual(set(rows_by_factor), {"0.0", "0.5", "1.0"})
        self.assertTrue(all(len(rows) == 2 for rows in rows_by_factor.values()))
        self.assertTrue(all(row["nrFails"] == "0" for row in rows_by_factor["0.0"]))
        baseline_instances = [
            (row["nrEdges"], row["source"], row["destination"], row["nrNDPs"])
            for row in rows_by_factor["0.0"]
        ]
        for rows in rows_by_factor.values():
            instances = [
                (row["nrEdges"], row["source"], row["destination"], row["nrNDPs"])
                for row in rows
            ]
            self.assertEqual(instances, baseline_instances)

    def test_erdos_renyi_csv_records_graph_parameters(self):
        with tempfile.TemporaryDirectory() as output_dir:
            path = ndp.runExperiments(
                runs=2,
                failure_type="node",
                graph_type="erdos_renyi",
                graph_param=0.15,
                no_nodes=25,
                fail_factor=0.8,
                output_dir=output_dir,
                seed=123,
            )

            with open(path, newline="") as csv_file:
                rows = list(csv.DictReader(csv_file))

        self.assertEqual(len(rows), 2)
        self.assertTrue(all(row["graphType"] == "erdos_renyi" for row in rows))
        self.assertTrue(all(row["graphParam"] == "0.15" for row in rows))
        self.assertTrue(all(row["edgeProb"] == "0.15" for row in rows))
        self.assertTrue(all(row["degree"] == "" for row in rows))
        self.assertTrue(all(row["nrNodes"] == "25" for row in rows))

    def test_erdos_renyi_cli_requires_probability(self):
        args = ndp.parseArgs(["--graph-type", "erdos_renyi"])

        with self.assertRaises(ValueError):
            ndp.runFromArgs(args)

    def test_erdos_renyi_series_uses_paired_instances(self):
        with tempfile.TemporaryDirectory() as output_dir:
            args = ndp.parseArgs(
                [
                    "--runs", "2",
                    "--failure-type", "node",
                    "--graph-type", "erdos_renyi",
                    "--p", "0.15",
                    "--nodes", "25",
                    "--fail-factor", "0.8", "1.6",
                    "--output-dir", output_dir,
                    "--seed", "123",
                ]
            )
            paths = ndp.runFromArgs(args)

            instances_by_factor = {}
            for path in paths:
                with open(path, newline="") as csv_file:
                    rows = list(csv.DictReader(csv_file))
                instances_by_factor[rows[0]["failFactor"]] = [
                    (row["nrEdges"], row["source"], row["destination"], row["nrNDPs"])
                    for row in rows
                ]

        self.assertEqual(instances_by_factor["0.8"], instances_by_factor["1.6"])

    def test_graphml_csv_records_topology_metadata(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            graphml_path = Path(temp_dir) / "TestTopology.graphml"
            nx.write_graphml(nx.cycle_graph(6), graphml_path)
            output_dir = Path(temp_dir) / "output"

            path = ndp.runExperiments(
                runs=2,
                failure_type="link",
                graphml_path=graphml_path,
                graph_name="test_topology",
                fail_factor=1.0,
                output_dir=output_dir,
                seed=123,
            )

            with open(path, newline="") as csv_file:
                rows = list(csv.DictReader(csv_file))

        self.assertEqual(len(rows), 2)
        self.assertTrue(all(row["graphType"] == "graphml" for row in rows))
        self.assertTrue(all(row["graphName"] == "test_topology" for row in rows))
        self.assertTrue(all(row["graphMLPath"].endswith("TestTopology.graphml") for row in rows))
        self.assertTrue(all(row["nrNodes"] == "6" for row in rows))
        self.assertTrue(all(row["nrEdges"] == "6" for row in rows))
        self.assertTrue(all(row["degree"] == "" for row in rows))
        self.assertTrue(all(row["edgeProb"] == "" for row in rows))

    def test_graphml_cli_uses_paired_instances_across_factors(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            graphml_path = Path(temp_dir) / "TestTopology.graphml"
            nx.write_graphml(nx.cycle_graph(8), graphml_path)
            output_dir = Path(temp_dir) / "output"
            args = ndp.parseArgs(
                [
                    "--runs", "2",
                    "--failure-type", "node",
                    "--graphml", str(graphml_path),
                    "--graph-name", "test_topology",
                    "--fail-factor", "1", "2",
                    "--output-dir", str(output_dir),
                    "--seed", "123",
                ]
            )
            paths = ndp.runFromArgs(args)

            instances_by_factor = {}
            for path in paths:
                with open(path, newline="") as csv_file:
                    rows = list(csv.DictReader(csv_file))
                instances_by_factor[rows[0]["failFactor"]] = [
                    (row["nrEdges"], row["source"], row["destination"], row["nrNDPs"])
                    for row in rows
                ]

        self.assertEqual(instances_by_factor["1.0"], instances_by_factor["2.0"])

    def test_clustered_link_and_node_csvs_record_parameters(self):
        with tempfile.TemporaryDirectory() as output_dir:
            paths = [
                ndp.runExperiments(
                    runs=2,
                    failure_type=failure_type,
                    failure_model="clustered",
                    failure_start=0.9,
                    failure_drop=0.3,
                    output_dir=output_dir,
                    seed=123,
                )
                for failure_type in ("link", "node")
            ]

            rows_by_type = {}
            for path in paths:
                with open(path, newline="") as csv_file:
                    rows = list(csv.DictReader(csv_file))
                rows_by_type[rows[0]["failureType"]] = rows

        for rows in rows_by_type.values():
            self.assertTrue(all(row["failureModel"] == "clustered" for row in rows))
            self.assertTrue(all(row["failureStart"] == "0.9" for row in rows))
            self.assertTrue(all(row["failureDrop"] == "0.3" for row in rows))
            self.assertTrue(all(row["failFactor"] == "" for row in rows))
        self.assertTrue(all(row["nrFailedNodes"] == "0" for row in rows_by_type["link"]))
        self.assertTrue(all(int(row["nrFailedNodes"]) > 0 for row in rows_by_type["node"]))

    def test_clustered_cli_writes_one_csv_per_start_and_failure_type(self):
        with tempfile.TemporaryDirectory() as output_dir:
            args = ndp.parseArgs(
                [
                    "--runs", "1",
                    "--failure-type", "both",
                    "--failure-model", "clustered",
                    "--failure-start", "0.6", "0.9",
                    "--failure-drop", "0.3",
                    "--output-dir", output_dir,
                    "--seed", "123",
                ]
            )
            paths = ndp.runFromArgs(args)

        self.assertEqual(len(paths), 4)
        self.assertTrue(any("clustered_link_fs0.6_fd0.3" in path for path in paths))
        self.assertTrue(any("clustered_node_fs0.9_fd0.3" in path for path in paths))

    def test_clustered_series_uses_paired_instances_across_starts(self):
        with tempfile.TemporaryDirectory() as output_dir:
            args = ndp.parseArgs(
                [
                    "--runs", "2",
                    "--failure-type", "link",
                    "--failure-model", "clustered",
                    "--failure-start", "0.3", "0.6", "0.9",
                    "--failure-drop", "0.3",
                    "--output-dir", output_dir,
                    "--seed", "123",
                ]
            )
            paths = ndp.runFromArgs(args)

            instances_by_start = {}
            for path in paths:
                with open(path, newline="") as csv_file:
                    rows = list(csv.DictReader(csv_file))
                instances_by_start[rows[0]["failureStart"]] = [
                    (row["nrEdges"], row["source"], row["destination"], row["nrNDPs"])
                    for row in rows
                ]

        baseline = instances_by_start["0.3"]
        for instances in instances_by_start.values():
            self.assertEqual(instances, baseline)


if __name__ == "__main__":
    unittest.main()
