"""Unit-Tests für die Schritt-5-Pipeline."""

import json
from pathlib import Path
import random
import sys
import tempfile
import unittest

import networkx as nx


PIPELINE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PIPELINE_ROOT))

import pipeline


class Step5PipelineTest(unittest.TestCase):
    """Prüft Konfiguration, Ausführung und Ausgabe der Pipeline."""

    def test_pipeline_uses_local_step5_modules(self):
        """Prüft, dass die Pipeline nur lokale Schritt-5-Module lädt."""
        local_modules = [
            pipeline.experiment.__file__,
            pipeline.result_analysis.__file__,
            sys.modules["routing_algorithms"].__file__,
            sys.modules["failures"].__file__,
        ]

        for module_path in local_modules:
            self.assertTrue(
                Path(module_path).resolve().is_relative_to(pipeline.PIPELINE_ROOT)
            )

    def test_default_output_root_is_inside_step5_output_folder(self):
        """Prüft den Standard-Ausgabeordner innerhalb von Schritt 5."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = {
                "run_name": "portable_run",
                "runs": 1,
                "algorithms": ["edp_paths"],
                "failures": ["random_link"],
                "datasets": [
                    {
                        "name": "small",
                        "type": "synthetic",
                        "graph_type": "erdos_renyi",
                        "nodes": 8,
                        "p": 0.4,
                    }
                ],
            }
            config_path = Path(temp_dir) / "config.json"
            config_path.write_text(json.dumps(config), encoding="utf-8")

            result = pipeline.run_pipeline(config_path, dry_run=True)

        self.assertEqual(
            result["config"]["output_root"],
            str(Path("Output") / "portable_run"),
        )
        self.assertEqual(
            Path(result["plan"][0]["output_dir"]).resolve(),
            pipeline.PIPELINE_ROOT / "Output" / "portable_run" / "raw" / "small",
        )
        self.assertEqual(result["config"]["title"], "Step 5 CLI")

    def test_dataset_failure_values_do_not_need_global_failure_defaults(self):
        """Prüft dataset-spezifische Failureparameter ohne globale Defaults."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = {
                "run_name": "dataset_only_failures",
                "runs": 1,
                "algorithms": ["edp_paths"],
                "failures": ["random_link", "clustered_node"],
                "datasets": [
                    {
                        "name": "small",
                        "type": "synthetic",
                        "graph_type": "erdos_renyi",
                        "nodes": 8,
                        "p": 0.4,
                        "fail_factors": [0.8, 1.6],
                        "failure_starts": [0.3, 0.6],
                        "failure_drop": 0.2,
                    }
                ],
            }
            config_path = Path(temp_dir) / "config.json"
            config_path.write_text(json.dumps(config), encoding="utf-8")

            result = pipeline.run_pipeline(config_path, dry_run=True)

        self.assertNotIn("fail_factors", result["config"])
        self.assertNotIn("failure_starts", result["config"])
        self.assertNotIn("failure_drop", result["config"])
        self.assertEqual(result["plan"][0]["fail_factors"], [0.8, 1.6])
        self.assertEqual(result["plan"][0]["failure_starts"], [0.3, 0.6])
        self.assertEqual(result["plan"][0]["failure_drop"], 0.2)

    def write_config(self, directory, extra=None):
        """Schreibt eine kleine Testkonfiguration und liefert ihren Pfad."""
        config = {
            "run_name": "test_run",
            "output_root": str(Path(directory) / "step5_output"),
            "runs": 1,
            "seed": 123,
            "resume": False,
            "algorithms": ["edp_paths", "ndp_paths"],
            "failures": ["random_link"],
            "fail_factors": [1.0],
            "failure_starts": [0.9],
            "failure_drop": 0.3,
            "metrics": ["resilience"],
            "datasets": [
                {
                    "name": "small",
                    "display_name": "Small",
                    "type": "synthetic",
                    "graph_type": "erdos_renyi",
                    "nodes": 8,
                    "p": 0.4,
                }
            ],
        }
        if extra:
            config.update(extra)
        path = Path(directory) / "config.json"
        path.write_text(json.dumps(config), encoding="utf-8")
        return path

    def test_dry_run_builds_one_job_per_dataset_and_failure(self):
        """Prüft die Jobplanung pro Dataset und Fehlertyp im Dry-Run."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = self.write_config(
                temp_dir,
                {
                    "failures": ["random_link", "clustered_node"],
                    "datasets": [
                        {
                            "name": "small",
                            "type": "synthetic",
                            "graph_type": "erdos_renyi",
                            "nodes": 8,
                            "p": 0.4,
                        },
                        {
                            "name": "regular",
                            "type": "synthetic",
                            "graph_type": "random_regular",
                            "nodes": 8,
                            "degree": 3,
                        },
                    ],
                },
            )

            result = pipeline.run_pipeline(config_path, dry_run=True)

        self.assertEqual(len(result["plan"]), 4)
        self.assertEqual(
            {(item["dataset"]["name"], item["failure"]) for item in result["plan"]},
            {
                ("small", "random_link"),
                ("small", "clustered_node"),
                ("regular", "random_link"),
                ("regular", "clustered_node"),
            },
        )

    def test_cli_overrides_filter_algorithms_failures_and_datasets(self):
        """Prüft CLI-Filter für Algorithmen, Fehlertypen und Datasets."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = self.write_config(
                temp_dir,
                {
                    "failures": ["random_link", "random_node"],
                    "datasets": [
                        {
                            "name": "small",
                            "type": "synthetic",
                            "graph_type": "erdos_renyi",
                            "nodes": 8,
                            "p": 0.4,
                        },
                        {
                            "name": "other",
                            "type": "synthetic",
                            "graph_type": "erdos_renyi",
                            "nodes": 9,
                            "p": 0.4,
                        },
                    ],
                },
            )

            result = pipeline.run_pipeline(
                config_path,
                dry_run=True,
                algorithms_override=["edp_paths"],
                failures_override=["random_node"],
                datasets_override=["other"],
            )

        self.assertEqual(len(result["plan"]), 1)
        self.assertEqual(result["plan"][0]["algorithms"], ["edp_paths"])
        self.assertEqual(result["plan"][0]["failure"], "random_node")
        self.assertEqual(result["plan"][0]["dataset"]["name"], "other")

    def test_cli_overrides_experiment_and_synthetic_graph_parameters(self):
        """Prüft CLI-Overrides für Lauf- und Graphparameter."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_root = Path(temp_dir) / "override_output"
            config_path = self.write_config(temp_dir)

            result = pipeline.run_pipeline(
                config_path,
                dry_run=True,
                run_name_override="quick_n12",
                output_root_override=str(output_root),
                runs_override=7,
                seed_override=456,
                fail_factors_override=[0.5, 1.5],
                failure_starts_override=[0.4, 0.8],
                failure_drop_override=0.2,
                nodes_override=12,
                p_override=0.25,
            )

        self.assertEqual(result["config"]["run_name"], "quick_n12")
        self.assertEqual(result["config"]["output_root"], str(output_root))
        self.assertEqual(result["config"]["runs"], 7)
        self.assertEqual(result["config"]["seed"], 456)
        self.assertEqual(result["config"]["fail_factors"], [0.5, 1.5])
        self.assertEqual(result["config"]["failure_starts"], [0.4, 0.8])
        self.assertEqual(result["config"]["failure_drop"], 0.2)
        self.assertEqual(result["plan"][0]["nodes"], 12)
        self.assertEqual(result["plan"][0]["graph_param"], 0.25)
        self.assertEqual(result["plan"][0]["fail_factors"], [0.5, 1.5])
        self.assertEqual(result["plan"][0]["failure_starts"], [0.4, 0.8])
        self.assertEqual(result["plan"][0]["failure_drop"], 0.2)

    def test_dataset_specific_failure_parameters_override_globals(self):
        """Prüft Vorrang von Dataset-Parametern vor globalen Werten."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = self.write_config(
                temp_dir,
                {
                    "fail_factors": [1.0],
                    "failure_starts": [0.9],
                    "failure_drop": 0.3,
                    "datasets": [
                        {
                            "name": "small",
                            "type": "synthetic",
                            "graph_type": "erdos_renyi",
                            "nodes": 8,
                            "p": 0.4,
                            "fail_factors": [0.8, 1.6],
                            "failure_starts": [0.3, 0.6],
                            "failure_drop": 0.2,
                        },
                        {
                            "name": "defaulted",
                            "type": "synthetic",
                            "graph_type": "erdos_renyi",
                            "nodes": 9,
                            "p": 0.4,
                        },
                    ],
                },
            )

            result = pipeline.run_pipeline(config_path, dry_run=True)

        by_dataset = {item["dataset"]["name"]: item for item in result["plan"]}
        self.assertEqual(by_dataset["small"]["fail_factors"], [0.8, 1.6])
        self.assertEqual(by_dataset["small"]["failure_starts"], [0.3, 0.6])
        self.assertEqual(by_dataset["small"]["failure_drop"], 0.2)
        self.assertEqual(by_dataset["defaulted"]["fail_factors"], [1.0])
        self.assertEqual(by_dataset["defaulted"]["failure_starts"], [0.9])
        self.assertEqual(by_dataset["defaulted"]["failure_drop"], 0.3)

    def test_preflight_checks_missing_graphml(self):
        """Prüft Preflight-Fehler bei fehlender GraphML-Datei."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = self.write_config(
                temp_dir,
                {
                    "datasets": [
                        {
                            "name": "missing",
                            "type": "graphml",
                            "graphml": str(Path(temp_dir) / "missing.graphml"),
                        }
                    ]
                },
            )

            with self.assertRaises(FileNotFoundError):
                pipeline.run_pipeline(config_path, preflight=True)

    def test_dry_run_graphml_plan_uses_real_graph_metadata(self):
        """Prüft Dry-Run-Metadaten für Real-World-Graphen."""
        with tempfile.TemporaryDirectory() as temp_dir:
            graphml_path = Path(temp_dir) / "path.graphml"
            nx.write_graphml(nx.path_graph(7), graphml_path)
            config_path = self.write_config(
                temp_dir,
                {
                    "datasets": [
                        {
                            "name": "real_path",
                            "type": "graphml",
                            "graphml": str(graphml_path),
                            "graph_name": "path",
                        }
                    ]
                },
            )

            result = pipeline.run_pipeline(config_path, dry_run=True)

        self.assertEqual(result["plan"][0]["graph_type"], "graphml")
        self.assertEqual(result["plan"][0]["nodes"], 7)
        self.assertEqual(result["plan"][0]["graph_param"], "")

    def test_preflight_returns_summary_for_valid_config(self):
        """Prüft die Preflight-Zusammenfassung für gültige Konfigurationen."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = self.write_config(temp_dir)

            result = pipeline.run_pipeline(config_path, preflight=True)

        self.assertTrue(any(message.startswith("datasets=1") for message in result["preflight"]))
        self.assertTrue(any(message.startswith("jobs=1") for message in result["preflight"]))

    def test_dry_run_and_preflight_cannot_be_combined(self):
        """Prüft die Trennung von Plananzeige und technischer Prüfung."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = self.write_config(temp_dir)

            with self.assertRaises(ValueError):
                pipeline.run_pipeline(config_path, dry_run=True, preflight=True)

    def test_pipeline_writes_summary_plots_and_manifest(self):
        """Prüft Summary, Plots, Manifest und verwendete Konfiguration."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = self.write_config(temp_dir)

            result = pipeline.run_pipeline(config_path, runs_override=2)

            summary = Path(result["summary"])
            manifest = Path(result["manifest"])
            used_config = manifest.parent / "used_config.json"
            plots = [Path(path) for path in result["plots"]]

            self.assertTrue(summary.exists())
            self.assertTrue(manifest.exists())
            self.assertTrue(used_config.exists())
            self.assertEqual(len(plots), 2)
            self.assertTrue(all(path.exists() for path in plots))
            manifest_data = json.loads(manifest.read_text(encoding="utf-8"))
            used_config_data = json.loads(used_config.read_text(encoding="utf-8"))

        self.assertEqual(manifest_data["run_name"], "test_run")
        self.assertEqual(manifest_data["runs"], 2)
        self.assertEqual(manifest_data["algorithms"], ["edp_paths", "ndp_paths"])
        self.assertEqual(used_config_data["runs"], 2)

    def test_pipeline_writes_plot_groups_to_separate_directories(self):
        """Prüft getrennte Plotordner für Random- und Real-World-Gruppen."""
        with tempfile.TemporaryDirectory() as temp_dir:
            graphml_path = Path(temp_dir) / "cycle.graphml"
            nx.write_graphml(nx.cycle_graph(8), graphml_path)
            config_path = self.write_config(
                temp_dir,
                {
                    "runs": 1,
                    "datasets": [
                        {
                            "name": "random_small",
                            "display_name": "Random Small",
                            "type": "synthetic",
                            "graph_type": "erdos_renyi",
                            "nodes": 8,
                            "p": 0.4,
                        },
                        {
                            "name": "real_cycle",
                            "display_name": "Real Cycle",
                            "type": "graphml",
                            "graphml": str(graphml_path),
                            "graph_name": "cycle",
                        },
                    ],
                    "plot_groups": [
                        {
                            "name": "random_graphs",
                            "title": "Random Graphs",
                            "datasets": ["random_small"],
                        },
                        {
                            "name": "real_world",
                            "title": "Real-World Graphs",
                            "datasets": ["real_cycle"],
                        },
                    ],
                },
            )

            result = pipeline.run_pipeline(config_path)
            plot_paths = [Path(path) for path in result["plots"]]

        self.assertEqual(len(plot_paths), 4)
        self.assertTrue(any("random_graphs" in path.parts for path in plot_paths))
        self.assertTrue(any("real_world" in path.parts for path in plot_paths))

    def test_pipeline_defaults_plot_groups_like_gui(self):
        """Prüft automatische CLI-Plotgruppen ohne explizite JSON-Plotgruppen."""
        with tempfile.TemporaryDirectory() as temp_dir:
            graphml_path = Path(temp_dir) / "cycle.graphml"
            nx.write_graphml(nx.cycle_graph(8), graphml_path)
            config_path = self.write_config(
                temp_dir,
                {
                    "runs": 1,
                    "datasets": [
                        {
                            "name": "random_small",
                            "display_name": "Random Small",
                            "type": "synthetic",
                            "graph_type": "erdos_renyi",
                            "nodes": 8,
                            "p": 0.4,
                        },
                        {
                            "name": "real_cycle",
                            "display_name": "Real Cycle",
                            "type": "graphml",
                            "graphml": str(graphml_path),
                            "graph_name": "cycle",
                        },
                    ],
                },
            )

            result = pipeline.run_pipeline(config_path)
            plot_paths = [Path(path) for path in result["plots"]]

        self.assertEqual(len(plot_paths), 4)
        self.assertTrue(all("all_graphs" not in path.parts for path in plot_paths))
        self.assertTrue(any("random_graphs" in path.parts for path in plot_paths))
        self.assertTrue(any("real_world" in path.parts for path in plot_paths))

    def test_default_plot_groups_use_at_most_three_datasets(self):
        """Prüft, dass Standard-Plotgruppen höchstens drei Teilplots enthalten."""
        datasets = [
            {"name": f"random_{index}", "type": "synthetic"}
            for index in range(4)
        ] + [
            {"name": f"real_{index}", "type": "graphml"}
            for index in range(4)
        ]

        groups = pipeline.default_plot_groups(datasets)

        self.assertEqual(
            [group["name"] for group in groups],
            ["random_graphs", "random_graphs_2", "real_world", "real_world_2"],
        )
        self.assertTrue(all(len(group["datasets"]) <= 3 for group in groups))

    def test_extension_helpers_keep_existing_failure_filenames(self):
        """Prüft stabile CSV-Dateinamen nach Erweiterungshelfern."""
        random_filename = pipeline.experiment.configuration_filename(
            {
                "failure_type": "link",
                "failure_model": "random",
                "fail_factor": 0.8,
            },
            0.3,
        )
        clustered_filename = pipeline.experiment.configuration_filename(
            {
                "failure_type": "node",
                "failure_model": "clustered",
                "failure_start": 0.3,
            },
            0.3,
        )

        self.assertEqual(random_filename, "algorithms_random_link_ff0.8.csv")
        self.assertEqual(
            clustered_filename,
            "algorithms_clustered_node_fs0.3_fd0.3.csv",
        )

    def test_instance_rows_store_failed_edges_and_nodes_separately(self):
        """Prüft getrennte Zähler für betroffene Kanten und Knoten."""
        graph = nx.path_graph(4)

        rows = pipeline.experiment.create_instance_rows(
            1,
            graph,
            0,
            3,
            failed_edges=[(1, 2), (2, 3)],
            failure_type="node",
            failure_model="random",
            failed_nodes=[2],
            algorithms=["edp_paths"],
        )

        self.assertEqual(rows[0]["nrFailedEdges"], 2)
        self.assertEqual(rows[0]["nrFailedNodes"], 1)
        self.assertNotIn("nrFails", rows[0])

    def test_scene_selection_is_stable_for_graph_insertion_order(self):
        """Prüft deterministische Endpunkt- und Failure-Auswahl."""
        edges = [
            ("0", "1"),
            ("1", "2"),
            ("2", "3"),
            ("3", "4"),
            ("0", "4"),
            ("1", "4"),
        ]
        graph_a = nx.Graph()
        graph_a.add_edges_from(edges)
        graph_b = nx.Graph()
        graph_b.add_edges_from(reversed(edges))

        self.assertEqual(
            pipeline.experiment.choose_endpoints(graph_a, random.Random(123)),
            pipeline.experiment.choose_endpoints(graph_b, random.Random(123)),
        )

        random_link_a = pipeline.failures.select_failures(
            graph_a, "0", "3", "link", "random", 2, 0.0, 0.3, random.Random("same")
        )
        random_link_b = pipeline.failures.select_failures(
            graph_b, "0", "3", "link", "random", 2, 0.0, 0.3, random.Random("same")
        )
        random_node_a = pipeline.failures.select_failures(
            graph_a, "0", "3", "node", "random", 2, 0.0, 0.3, random.Random("same")
        )
        random_node_b = pipeline.failures.select_failures(
            graph_b, "0", "3", "node", "random", 2, 0.0, 0.3, random.Random("same")
        )

        self.assertEqual(random_link_a, random_link_b)
        self.assertEqual(random_node_a, random_node_b)

    def test_failure_seed_parameter_tokens_are_numeric_canonical(self):
        """Prüft gleiche Failure-RNG-Schlüssel für 1 und 1.0."""
        self.assertEqual(
            pipeline.experiment.seed_parameter_token(1),
            pipeline.experiment.seed_parameter_token(1.0),
        )
        self.assertEqual(
            pipeline.experiment.seed_parameter_token("0.30"),
            pipeline.experiment.seed_parameter_token(0.3),
        )

    def test_clustered_link_protects_source_in_every_layer(self):
        """Prüft den Schutz von `s` sowie den Rücklaufschutz für `d`."""
        class RecordingRandom:
            """Zeichnet die Kandidaten jeder deterministischen Auswahl auf."""

            def __init__(self):
                self.populations = []

            def sample(self, population, count):
                population = list(population)
                self.populations.append(population)
                return population[:count]

        graph = nx.Graph()
        graph.add_edges_from(
            [
                ("d", "a"),
                ("d", "b"),
                ("a", "c"),
                ("b", "e"),
                ("c", "f"),
                ("s", "a"),
                ("s", "d"),
            ]
        )
        rng = RecordingRandom()

        pipeline.failures.clustered_link_failures(
            graph,
            "s",
            "d",
            failure_start=1.0,
            failure_drop=0.3,
            rng=rng,
        )

        self.assertTrue(rng.populations)
        self.assertTrue(
            all(
                "s" not in edge
                for population in rng.populations
                for edge in population
            )
        )
        self.assertTrue(
            all("d" in edge for edge in rng.populations[0])
        )
        self.assertTrue(
            all(
                "d" not in edge
                for population in rng.populations[1:]
                for edge in population
            )
        )

    def test_one_tree_keeps_other_disjoint_paths_separate(self):
        """Prüft, dass nur der längste Pfad zum One Tree erweitert wird."""
        graph = nx.Graph()
        graph.add_edges_from(
            [
                ("s", "a"),
                ("a", "b"),
                ("b", "c"),
                ("c", "d"),
                ("s", "x"),
                ("x", "d"),
                ("a", "x"),
                ("b", "y"),
                ("y", "d"),
            ]
        )
        paths = [
            ["s", "x", "d"],
            ["s", "a", "b", "c", "d"],
        ]

        structures = pipeline.routing_algorithms.build_structures(
            graph,
            "s",
            "d",
            paths,
            "one_tree",
        )

        remaining_path, one_tree = structures
        self.assertFalse(remaining_path.is_tree)
        self.assertEqual(remaining_path.original_path, ("s", "x", "d"))
        self.assertEqual(
            {frozenset(edge) for edge in remaining_path.graph.edges},
            {frozenset(("s", "x"))},
        )
        self.assertTrue(one_tree.is_tree)
        self.assertIsNone(one_tree.grown_graph)
        self.assertEqual(one_tree.original_path, ("s", "a", "b", "c", "d"))
        self.assertNotIn("x", one_tree.graph)
        self.assertTrue(
            {
                frozenset(("s", "a")),
                frozenset(("a", "b")),
                frozenset(("b", "c")),
                frozenset(("b", "y")),
            }.issubset({frozenset(edge) for edge in one_tree.graph.edges})
        )
        self.assertEqual(set(one_tree.exits), {"c", "y"})

    def test_multiple_trees_keep_every_base_path(self):
        """Prüft, dass jeder disjunkte Pfad Grundgerüst eines Baums bleibt."""
        graph = nx.Graph()
        graph.add_edges_from(
            [
                ("s", "a"),
                ("a", "d"),
                ("s", "b"),
                ("b", "c"),
                ("c", "d"),
                ("a", "u"),
                ("u", "d"),
                ("b", "v"),
                ("v", "d"),
            ]
        )
        paths = [["s", "a", "d"], ["s", "b", "c", "d"]]

        structures = pipeline.routing_algorithms.build_structures(
            graph,
            "s",
            "d",
            paths,
            "multiple_trees",
        )

        self.assertTrue(all(structure.is_tree for structure in structures))
        for structure in structures:
            base_edges = {
                frozenset(edge)
                for edge in zip(
                    structure.original_path[:-2],
                    structure.original_path[1:-1],
                )
            }
            self.assertTrue(
                base_edges.issubset(
                    {frozenset(edge) for edge in structure.graph.edges}
                )
            )

    def test_tree_growth_does_not_start_at_source(self):
        """Prüft die TREE-Regel: Wachstum beginnt nur an inneren Pfadknoten."""
        graph = nx.Graph()
        graph.add_edges_from(
            [
                ("s", "a"),
                ("a", "d"),
                ("s", "z"),
                ("z", "d"),
            ]
        )
        paths = [["s", "a", "d"]]

        for structure_type in ("one_tree", "multiple_trees"):
            with self.subTest(structure_type=structure_type):
                structures = pipeline.routing_algorithms.build_structures(
                    graph,
                    "s",
                    "d",
                    paths,
                    structure_type,
                )

                self.assertEqual(len(structures), 1)
                self.assertNotIn("z", structures[0].graph)
                self.assertEqual(set(structures[0].exits), {"a"})

    def test_one_tree_retains_growth_stage_before_truncation(self):
        """Prüft die sichtbare Wachstumsphase vor dem Entfernen toter Äste."""
        graph = nx.Graph()
        graph.add_edges_from(
            [
                ("s", "a"),
                ("a", "b"),
                ("b", "d"),
                ("s", "x"),
                ("x", "d"),
                ("a", "u"),
                ("u", "v"),
            ]
        )
        paths = [["s", "x", "d"], ["s", "a", "b", "d"]]

        structures = pipeline.routing_algorithms.build_structures(
            graph,
            "s",
            "d",
            paths,
            "one_tree",
            retain_growth_stage=True,
        )
        one_tree = next(structure for structure in structures if structure.is_tree)

        self.assertIsNotNone(one_tree.grown_graph)
        self.assertTrue(one_tree.grown_graph.has_edge("a", "u"))
        self.assertTrue(one_tree.grown_graph.has_edge("u", "v"))
        self.assertNotIn("u", one_tree.graph)
        self.assertNotIn("v", one_tree.graph)

    def test_tree_growth_processes_base_path_from_source_to_destination(self):
        """Prüft die Wachstumsreihenfolge vom ersten bis zum letzten Innenknoten."""
        graph = nx.Graph()
        graph.add_edges_from(
            [
                ("s", "a"),
                ("a", "b"),
                ("b", "d"),
                ("a", "u"),
                ("b", "u"),
                ("u", "v"),
                ("v", "d"),
            ]
        )
        paths = [["s", "a", "b", "d"]]

        for structure_type in ("one_tree", "multiple_trees"):
            with self.subTest(structure_type=structure_type):
                structures = pipeline.routing_algorithms.build_structures(
                    graph,
                    "s",
                    "d",
                    paths,
                    structure_type,
                    retain_growth_stage=True,
                )
                grown_graph = structures[0].grown_graph

                self.assertTrue(grown_graph.has_edge("a", "u"))
                self.assertFalse(grown_graph.has_edge("b", "u"))



if __name__ == "__main__":
    unittest.main()
