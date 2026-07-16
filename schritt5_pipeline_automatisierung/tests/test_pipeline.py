"""Unit-Tests für die Schritt-5-Pipeline."""

import json
from pathlib import Path
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


if __name__ == "__main__":
    unittest.main()
