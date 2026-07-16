"""Unit-Tests für die Streamlit-GUI und ihre Konfigurationshelfer."""

from pathlib import Path
import sys
import tempfile
import types
import unittest


PIPELINE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PIPELINE_ROOT))

import gui


class Step5GuiTest(unittest.TestCase):
    """Prüft GUI-Hilfsfunktionen ohne Streamlit-Server."""

    def test_clear_cached_step5_modules_removes_stale_imports(self):
        """Prüft, dass alte Streamlit-Importe vor einem GUI-Lauf entfernt werden."""
        original_modules = {
            module_name: sys.modules.get(module_name)
            for module_name in gui.STEP5_MODULES
        }
        try:
            sys.modules["experiment"] = types.ModuleType("experiment")

            gui._clear_cached_step5_modules()

            self.assertNotIn("experiment", sys.modules)
        finally:
            for module_name in gui.STEP5_MODULES:
                sys.modules.pop(module_name, None)
            for module_name, module in original_modules.items():
                if module is not None:
                    sys.modules[module_name] = module

    def test_parse_number_list_accepts_commas_spaces_and_semicolons(self):
        """Prüft das Parsen gemischter Zahlenlisten."""
        self.assertEqual(
            gui.parse_number_list("0.8, 1.6; 2.4", float),
            [0.8, 1.6, 2.4],
        )

    def test_build_failure_rate_range_includes_reachable_stop(self):
        """Prüft inklusive Failure-Rate-Bereiche."""
        self.assertEqual(
            gui.build_failure_rate_range(0.8, 3.2, 0.8),
            [0.8, 1.6, 2.4, 3.2],
        )
        self.assertEqual(
            gui.build_failure_rate_range(0.3, 0.9, 0.1),
            [0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9],
        )

    def test_gui_default_failure_series_match_step4(self):
        """Prüft die Schritt-4-Defaultwerte der GUI."""
        self.assertEqual(gui.DEFAULT_SEED, 123)
        self.assertEqual(
            gui.CLUSTERED_FAILURE_STARTS,
            [0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9],
        )
        self.assertEqual(gui.CLUSTERED_FAILURE_DROP, 0.3)
        self.assertEqual(
            gui.REAL_WORLD_FAIL_FACTORS,
            [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0],
        )
        self.assertEqual(
            gui.ERDOS_RENYI_DATASETS["synthetic_n25_p015"]["fail_factors"],
            [0.8, 1.6, 2.4, 3.2, 4.0, 4.8, 5.6, 6.4, 7.2, 8.0, 8.8],
        )
        self.assertEqual(
            gui.ERDOS_RENYI_DATASETS["synthetic_n50_p015"]["fail_factors"][-1],
            16.8,
        )
        self.assertEqual(
            gui.ERDOS_RENYI_DATASETS["synthetic_n100_p002"]["fail_factors"][-1],
            49.6,
        )

    def test_build_gui_config_contains_selected_graph_sets_and_plot_groups(self):
        """Prüft GUI-Konfigurationen mit Random- und Real-World-Graphen."""
        graph_datasets = [
            dict(gui.ERDOS_RENYI_DATASETS["synthetic_n25_p015"]),
            dict(gui.ERDOS_RENYI_DATASETS["synthetic_n50_p015"]),
            dict(gui.ERDOS_RENYI_DATASETS["synthetic_n100_p002"]),
            gui.build_gui_random_dataset(30, 0.2, [1.0, 2.0], [0.5, 0.7], 0.4),
            gui.build_gui_real_world_dataset("real_attmpls", [2.0, 4.0], [0.4, 0.8], 0.2),
        ]

        config = gui.build_gui_config(
            run_name="gui_test",
            output_root="Output/gui_test",
            runs=10,
            algorithms=["edp_paths", "ndp_paths"],
            failures=["random_link", "clustered_node"],
            graph_datasets=graph_datasets,
            metrics=["resilience"],
        )

        self.assertEqual(config["run_name"], "gui_test")
        self.assertEqual(config["runs"], 10)
        self.assertEqual(config["seed"], gui.DEFAULT_SEED)
        self.assertTrue(config["resume"])
        self.assertNotIn("fail_factors", config)
        self.assertNotIn("failure_starts", config)
        self.assertNotIn("failure_drop", config)
        self.assertEqual(config["algorithms"], ["edp_paths", "ndp_paths"])
        self.assertEqual(config["failures"], ["random_link", "clustered_node"])
        self.assertEqual(config["metrics"], ["resilience"])
        self.assertEqual(
            [dataset["name"] for dataset in config["datasets"]],
            [
                "synthetic_n25_p015",
                "synthetic_n50_p015",
                "synthetic_n100_p002",
                "random_er_n30_p0p2",
                "real_attmpls",
            ],
        )
        self.assertEqual(config["datasets"][0]["fail_factors"][-1], 8.8)
        self.assertEqual(config["datasets"][2]["fail_factors"][-1], 49.6)
        self.assertEqual(config["datasets"][3]["fail_factors"], [1.0, 2.0])
        self.assertEqual(config["datasets"][3]["failure_starts"], [0.5, 0.7])
        self.assertEqual(config["datasets"][3]["failure_drop"], 0.4)
        self.assertEqual(config["datasets"][4]["fail_factors"], [2.0, 4.0])
        self.assertEqual(config["datasets"][4]["failure_starts"], [0.4, 0.8])
        self.assertEqual(config["datasets"][4]["failure_drop"], 0.2)
        self.assertEqual(
            config["plot_groups"],
            [
                {
                    "name": "random_graphs",
                    "title": "Random Graphs",
                    "datasets": [
                        "synthetic_n25_p015",
                        "synthetic_n50_p015",
                        "synthetic_n100_p002",
                        "random_er_n30_p0p2",
                    ],
                },
                {
                    "name": "real_world",
                    "title": "Real-World Graphs",
                    "datasets": ["real_attmpls"],
                },
            ],
        )

    def test_default_step4_graphs_contains_three_random_and_three_real_world(self):
        """Prüft die sechs vorbereiteten Paper-Graphsets."""
        graph_datasets = gui.default_step4_graphs()

        self.assertEqual(len(graph_datasets), 6)
        self.assertEqual(
            [dataset["name"] for dataset in graph_datasets],
            [
                "synthetic_n25_p015",
                "synthetic_n50_p015",
                "synthetic_n100_p002",
                "real_attmpls",
                "real_oteglobe",
                "real_cogentco",
            ],
        )

    def test_real_world_graphs_use_step5_local_graphml_paths(self):
        """Prüft lokale GraphML-Pfade für Real-World-Graphen."""
        for dataset in gui.REAL_WORLD_DATASETS.values():
            graphml_path = Path(dataset["graphml"])

            self.assertEqual(graphml_path.parts[:2], ("data", "topology_zoo"))
            self.assertTrue((gui.PIPELINE_ROOT / graphml_path).is_file())

    def test_build_gui_config_requires_dataset_algorithm_and_failure(self):
        """Prüft Pflichtauswahlen für Graphen, Algorithmen und Fehlertypen."""
        base = {
            "run_name": "bad",
            "output_root": "Output/bad",
            "runs": 1,
            "algorithms": ["edp_paths"],
            "failures": ["random_link"],
            "graph_datasets": [],
        }

        with self.assertRaises(ValueError):
            gui.build_gui_config(**base)

        with self.assertRaises(ValueError):
            gui.build_gui_config(
                **{
                    **base,
                    "graph_datasets": [dict(gui.ERDOS_RENYI_DATASETS["synthetic_n25_p015"])],
                    "algorithms": [],
                }
            )

        with self.assertRaises(ValueError):
            gui.build_gui_config(
                **{
                    **base,
                    "graph_datasets": [dict(gui.ERDOS_RENYI_DATASETS["synthetic_n25_p015"])],
                    "failures": [],
                }
            )

    def test_write_gui_config_uses_output_root(self):
        """Prüft, dass GUI-Konfigurationen in den Ausgabeordner geschrieben werden."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_root = Path(temp_dir) / "gui_output"
            config = gui.build_gui_config(
                run_name="write_test",
                output_root=str(output_root),
                runs=1,
                algorithms=["edp_paths"],
                failures=["random_link"],
                graph_datasets=[gui.build_gui_random_dataset(8, 0.4, [1.0])],
            )

            config_path = gui.write_gui_config(config)

            self.assertEqual(config_path, output_root / "gui_config.json")
            self.assertTrue(config_path.exists())

    def test_relative_output_root_resolves_inside_step5_output_folder(self):
        """Prüft relative Ausgabeordner innerhalb des Schritt-5-Ordners."""
        self.assertEqual(
            gui.pipeline.resolve_repo_path("Output/gui_test"),
            gui.PIPELINE_ROOT / "Output" / "gui_test",
        )

    def test_server_command_uses_pipeline_cli_and_mode_flag(self):
        """Prüft den vorbereiteten Serverbefehl aus der GUI."""
        config_path = gui.PIPELINE_ROOT / "Output" / "gui" / "gui_config.json"

        command = gui.build_server_command(config_path, "Nur Experimente")

        self.assertIn("python pipeline.py", command)
        self.assertIn("--config Output/gui/gui_config.json", command)
        self.assertIn("--only-experiments", command)

    def test_dry_run_mode_uses_dry_run_flag(self):
        """Prüft den Dry-Run-Modus der GUI."""
        config_path = gui.PIPELINE_ROOT / "Output" / "gui" / "gui_config.json"

        command = gui.build_server_command(config_path, "Dry Run")

        self.assertEqual(gui.mode_to_pipeline_flags("Dry Run"), {"dry_run": True})
        self.assertIn("--dry-run", command)
        self.assertNotIn("--preflight", command)

    def test_dry_run_plan_rows_use_short_graph_column_names(self):
        """Prüft die Spaltennamen der Dry-Run-Tabelle."""
        result = {
            "config": {"runs": 5},
            "plan": [
                {
                    "dataset": {"name": "real_attmpls"},
                    "failure": "random_link",
                    "graph_type": "graphml",
                    "nodes": 25,
                    "graph_param": "",
                    "output_dir": gui.PIPELINE_ROOT / "Output" / "dry" / "raw",
                }
            ],
        }

        rows = gui.dry_run_plan_rows(result)

        self.assertEqual(rows[0]["n"], 25)
        self.assertEqual(rows[0]["p"], "")
        self.assertNotIn("Knoten", rows[0])
        self.assertNotIn("Graphparameter", rows[0])


if __name__ == "__main__":
    unittest.main()
