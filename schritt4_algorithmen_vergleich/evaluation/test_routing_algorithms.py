from pathlib import Path
import csv
import sys
import tempfile
import unittest

import networkx as nx


SRC_ROOT = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC_ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import routing_algorithms as routing
import experiment
import failures
import result_analysis


class RoutingAlgorithmsTest(unittest.TestCase):
    """Regressionstests für die Schritt-4-Implementierung.

    Diese Tests sind weniger als klassische Unit-Tests für einzelne Zeilen
    gedacht, sondern als Schutznetz für die fachlichen Anforderungen: Alle sechs
    Algorithmusvarianten müssen stabil vorhanden sein, One Tree und Multiple
    Trees müssen sich paper-nah verhalten, Node- und Link-Failures müssen korrekt
    vorbereitet werden, und die CSV-Ausgabe muss für spätere Notebooks sauber
    aggregierbar bleiben.
    """

    def setUp(self):
        """Bereitet eine kleine Topologie mit Pfaden, Ast und Exit vor."""
        # Zwei disjunkte s-d-Pfade und zusätzliche Äste. Knoten 7 ist ein
        # redundantes Blatt, Knoten 5 bietet dagegen einen neuen Ausgang zu d.
        # Genau diese kleine Topologie macht sichtbar, ob die Trunkierung
        # überflüssige Blätter entfernt und nützliche Ausgänge zum Ziel behält.
        self.graph = nx.Graph(
            [
                (0, 1), (1, 6),
                (0, 2), (2, 3), (3, 6),
                (3, 4), (4, 5), (5, 6),
                (4, 7),
            ]
        )
        self.paths = [[0, 1, 6], [0, 2, 3, 6]]

    def test_six_algorithm_names_are_stable(self):
        """Sichert die sechs erwarteten Algorithmusnamen ab."""
        self.assertEqual(
            set(routing.ALGORITHMS),
            {
                "edp_paths", "edp_one_tree", "edp_multiple_trees",
                "ndp_paths", "ndp_one_tree", "ndp_multiple_trees",
            },
        )

    def test_one_tree_extends_only_longest_path(self):
        """Prüft, dass One Tree nur den längsten Pfad erweitert."""
        structures = routing.build_structures(self.graph, 0, 6, self.paths, "one_tree")

        self.assertFalse(structures[0].is_tree)
        self.assertEqual(set(structures[0].graph.edges), {(0, 1)})
        self.assertTrue(structures[1].is_tree)
        self.assertIn(5, structures[1].exits)

    def test_truncation_removes_branch_without_exit_to_destination(self):
        """Prüft, dass die Trunkierung nutzlose Blätter entfernt."""
        structures = routing.build_structures(self.graph, 0, 6, self.paths, "one_tree")
        tree = structures[1].graph

        self.assertNotIn(7, tree)
        leaves = {node for node in tree if node != 0 and tree.degree(node) == 1}
        self.assertTrue(all(self.graph.has_edge(node, 6) for node in leaves))

    def test_one_tree_keeps_path_hops_without_failures(self):
        """Vergleicht One Tree ohne Ausfälle mit reinem Pfadrouting."""
        paths = routing.route_algorithm(self.graph, 0, 6, [], "edp_paths", self.paths)
        one_tree = routing.route_algorithm(self.graph, 0, 6, [], "edp_one_tree", self.paths)

        self.assertEqual(paths.hops, 2)
        self.assertEqual(one_tree.hops, paths.hops)

    def test_one_tree_uses_added_branch_after_original_exit_fails(self):
        """Prüft, dass ein gewachsener Ast als Ersatzroute genutzt wird."""
        result = routing.route_algorithm(
            self.graph, 0, 6, [(1, 6), (3, 6)], "edp_one_tree", self.paths
        )

        self.assertTrue(result.success)
        self.assertEqual(result.route[-1], (5, 6))

    def test_path_routing_counts_return_to_source_before_fallback(self):
        """Sichert die Hop-Zählung beim Rückweg zur nächsten Struktur."""
        result = routing.route_algorithm(
            self.graph, 0, 6, [(1, 6)], "edp_paths", self.paths
        )

        self.assertTrue(result.success)
        self.assertEqual(result.hops, 5)  # 0-1-0, danach 0-2-3-6

    def test_all_algorithms_share_one_failure_instance(self):
        """Prüft, dass alle Algorithmen dieselbe Ausfallinstanz erhalten."""
        results = routing.run_algorithms(self.graph, 0, 6, [(1, 6)])

        self.assertEqual(len(results), 6)
        self.assertEqual({result.algorithm for result in results}, set(routing.ALGORITHMS))

    def test_multiple_trees_are_edge_disjoint(self):
        """Prüft die Kantendisjunktheit der Multiple-Trees-Strukturen."""
        structures = routing.build_structures(
            self.graph, 0, 6, self.paths, "multiple_trees"
        )
        edge_sets = [
            {frozenset(edge) for edge in structure.graph.edges}
            for structure in structures
        ]

        for index, edges in enumerate(edge_sets):
            for other in edge_sets[index + 1:]:
                self.assertTrue(edges.isdisjoint(other))

    def test_long_csv_has_one_row_per_algorithm_and_shared_instance(self):
        """Sichert das Long-CSV-Format mit einer Zeile pro Algorithmus."""
        rows = experiment.create_instance_rows(
            rep=1,
            graph=self.graph,
            source=0,
            destination=6,
            failed_edges=[(1, 6)],
            failure_type="link",
            failure_model="random",
            graph_type="test",
        )

        self.assertEqual(len(rows), 6)
        self.assertEqual({row["algorithm"] for row in rows}, set(routing.ALGORITHMS))
        self.assertEqual({row["source"] for row in rows}, {0})
        self.assertEqual({row["destination"] for row in rows}, {6})
        self.assertEqual({row["nrFails"] for row in rows}, {1})

        with tempfile.TemporaryDirectory() as temp_dir:
            csv_path = Path(temp_dir) / "results.csv"
            experiment.write_rows(csv_path, rows)
            with csv_path.open(newline="", encoding="utf-8") as csv_file:
                written = list(csv.DictReader(csv_file))
        self.assertEqual(len(written), 6)
        self.assertEqual(set(written[0]), set(experiment.CSV_FIELDNAMES))

    def test_node_disjoint_paths_share_no_internal_nodes(self):
        """Prüft, dass NDPs keine internen Knoten teilen."""
        paths = routing.get_disjoint_paths(self.graph, 0, 6, "ndp")
        internal = [set(path[1:-1]) for path in paths]

        for index, nodes in enumerate(internal):
            for other in internal[index + 1:]:
                self.assertTrue(nodes.isdisjoint(other))

    def test_node_failures_are_converted_to_all_incident_edges(self):
        """Prüft die Umwandlung eines Knotenausfalls in Kanten."""
        failed_edges = failures.node_failures_to_edges(self.graph, [3])
        edge_sets = {frozenset(edge) for edge in failed_edges}

        self.assertEqual(
            edge_sets,
            {
                frozenset((2, 3)),
                frozenset((3, 6)),
                frozenset((3, 4)),
            },
        )

    def test_full_series_writes_all_four_failure_combinations_paired(self):
        """Sichert alle vier Failure-Kombinationen auf gepaarten Instanzen."""
        with tempfile.TemporaryDirectory() as temp_dir:
            graphml_path = Path(temp_dir) / "cycle.graphml"
            nx.write_graphml(nx.cycle_graph(8), graphml_path)
            output_dir = Path(temp_dir) / "output"
            paths = experiment.run_experiment_series(
                runs=2,
                failure_types=["link", "node"],
                failure_models=["random", "clustered"],
                graphml_path=graphml_path,
                graph_name="cycle",
                fail_factors=[1.0],
                failure_starts=[0.9],
                output_dir=output_dir,
                seed=123,
            )

            rows_by_file = {}
            for path in paths:
                with open(path, newline="", encoding="utf-8") as csv_file:
                    rows_by_file[Path(path).name] = list(csv.DictReader(csv_file))

        self.assertEqual(len(rows_by_file), 4)
        self.assertTrue(all(len(rows) == 12 for rows in rows_by_file.values()))
        combinations_found = {
            (rows[0]["failureType"], rows[0]["failureModel"])
            for rows in rows_by_file.values()
        }
        self.assertEqual(
            combinations_found,
            {
                ("link", "random"),
                ("node", "random"),
                ("link", "clustered"),
                ("node", "clustered"),
            },
        )
        paired_instances = []
        for rows in rows_by_file.values():
            paired_instances.append(
                [(row["rep"], row["source"], row["destination"]) for row in rows[::6]]
            )
        self.assertTrue(all(instances == paired_instances[0] for instances in paired_instances))

    def test_cli_can_select_algorithms(self):
        """Prüft, dass die CLI eine Algorithmus-Teilmenge ausführen kann."""
        with tempfile.TemporaryDirectory() as temp_dir:
            graphml_path = Path(temp_dir) / "cycle.graphml"
            nx.write_graphml(nx.cycle_graph(8), graphml_path)
            args = experiment.parse_args(
                [
                    "--runs", "1",
                    "--failure-type", "link",
                    "--failure-model", "random",
                    "--graphml", str(graphml_path),
                    "--algorithms", "edp_paths", "ndp_one_tree",
                    "--output-dir", str(Path(temp_dir) / "output"),
                    "--seed", "123",
                ]
            )
            paths = experiment.run_from_args(args)
            with open(paths[0], newline="", encoding="utf-8") as csv_file:
                rows = list(csv.DictReader(csv_file))

        self.assertEqual(
            {row["algorithm"] for row in rows},
            {"edp_paths", "ndp_one_tree"},
        )

    def test_resume_keeps_complete_reps_and_replaces_partial_rep(self):
        """Prüft, dass Resume vollständige Reps behält und Teil-Reps ersetzt."""
        selected = ["edp_paths", "ndp_one_tree"]
        with tempfile.TemporaryDirectory() as temp_dir:
            graphml_path = Path(temp_dir) / "cycle.graphml"
            nx.write_graphml(nx.cycle_graph(8), graphml_path)
            output_dir = Path(temp_dir) / "output"
            paths = experiment.run_experiment_series(
                runs=2,
                failure_types=["link"],
                failure_models=["random"],
                algorithms=selected,
                graphml_path=graphml_path,
                graph_name="cycle",
                fail_factors=[1.0],
                output_dir=output_dir,
                seed=123,
            )
            csv_path = Path(paths[0])
            with csv_path.open(newline="", encoding="utf-8") as csv_file:
                original_rows = list(csv.DictReader(csv_file))

            partial = dict(original_rows[0])
            partial["rep"] = "3"
            with csv_path.open("a", newline="", encoding="utf-8") as csv_file:
                writer = csv.DictWriter(csv_file, fieldnames=experiment.CSV_FIELDNAMES)
                writer.writerow(partial)

            experiment.run_experiment_series(
                runs=4,
                failure_types=["link"],
                failure_models=["random"],
                algorithms=selected,
                graphml_path=graphml_path,
                graph_name="cycle",
                fail_factors=[1.0],
                output_dir=output_dir,
                seed=123,
                resume=True,
            )
            with csv_path.open(newline="", encoding="utf-8") as csv_file:
                resumed_rows = list(csv.DictReader(csv_file))

        self.assertEqual(resumed_rows[:4], original_rows)
        self.assertEqual(len(resumed_rows), 8)
        self.assertEqual(
            [row["rep"] for row in resumed_rows],
            ["1", "1", "2", "2", "3", "3", "4", "4"],
        )

    def test_final_analysis_validates_complete_server_style_data(self):
        """Sichert die Validierung vollständiger serverartiger Ergebnisdaten."""
        with tempfile.TemporaryDirectory() as temp_dir:
            graphml_path = Path(temp_dir) / "cycle.graphml"
            nx.write_graphml(nx.cycle_graph(8), graphml_path)
            output_dir = Path(temp_dir) / "output"
            experiment.run_experiment_series(
                runs=2,
                failure_types=["link", "node"],
                failure_models=["random", "clustered"],
                graphml_path=graphml_path,
                graph_name="cycle",
                fail_factors=[1.0],
                failure_starts=[0.9],
                output_dir=output_dir,
                seed=123,
            )
            raw_input, files = result_analysis.load_result_directories(
                {"cycle": output_dir}
            )
            _, summary = result_analysis.aggregate_results(raw_input)
            result_analysis.validate_summary(summary, 2, routing.ALGORITHMS)
            complete = result_analysis.completeness_table(summary)

        self.assertEqual(len(files["cycle"]), 4)
        self.assertTrue(complete["algorithms"].eq(6).all())
        self.assertTrue(complete["samplesPerAlgorithm"].eq(2).all())


if __name__ == "__main__":
    unittest.main()
