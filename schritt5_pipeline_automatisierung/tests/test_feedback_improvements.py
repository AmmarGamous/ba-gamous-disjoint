"""Regressionstests für die aus dem Artefaktfeedback abgeleiteten Änderungen."""

from contextlib import redirect_stdout
import csv
import inspect
import io
import json
from pathlib import Path
import random
import sys
import tempfile
import unittest
from unittest.mock import patch


PIPELINE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PIPELINE_ROOT))
import pipeline


class FeedbackImprovementsTest(unittest.TestCase):
    """Prüft stabile Defaults, frühe Fehler und nachvollziehbare Metadaten."""

    def setUp(self):
        """Legt einen eigenen kleinen Testlauf außerhalb vorhandener Ergebnisse an."""
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.config = {
            "run_name": "feedback_test", "output_root": str(self.root / "Output"),
            "runs": 1, "seed": 123, "resume": True,
            "algorithms": list(pipeline.DEFAULT_ALGORITHMS),
            "failures": list(pipeline.DEFAULT_FAILURES),
            "metrics": ["resilience", "avgHops", "avgStretch"],
            "fail_factors": [0.8], "failure_starts": [0.3], "failure_drop": 0.3,
            "datasets": [{"name": "small", "type": "synthetic", "graph_type": "erdos_renyi", "nodes": 8, "p": 0.4}],
        }
        self.config_path = self.root / "config.json"

    def write_config(self):
        """Schreibt die jeweils angepasste Konfiguration für den öffentlichen Einstieg."""
        self.config_path.write_text(json.dumps(self.config), encoding="utf-8")
        return self.config_path

    def test_registered_extensions_do_not_change_defaults(self):
        """Neue Einträge bleiben explizit auswählbar, gehören aber nicht zu Defaults."""
        self.config.pop("algorithms", None)
        self.config.pop("failures", None)
        algorithms = pipeline.ALGORITHMS + ("extra",)
        with patch.object(pipeline, "ALGORITHMS", algorithms), patch.object(
            pipeline.experiment, "ALGORITHMS", algorithms
        ), patch.dict(pipeline.FAILURE_COMBINATIONS, {"extra_link": ("random", "link")}), patch.dict(
            pipeline.routing_algorithms.EXTRA_ALGORITHM_RUNNERS, {"extra": lambda *args: None}
        ):
            config = pipeline.load_config(self.write_config())
            self.assertEqual(config["algorithms"], list(pipeline.DEFAULT_ALGORITHMS))
            self.assertEqual(config["failures"], list(pipeline.DEFAULT_FAILURES))
            self.assertEqual(pipeline.experiment.parse_args([]).algorithms, list(pipeline.DEFAULT_ALGORITHMS))
            self.assertEqual(pipeline.experiment.parse_args(["--algorithms", "extra"]).algorithms, ["extra"])
            result = pipeline.run_pipeline(self.config_path, dry_run=True, algorithms_override=["extra"], failures_override=["extra_link"])
            self.assertEqual(result["plan"][0]["algorithms"], ["extra"])
            self.assertEqual(result["plan"][0]["failure"], "extra_link")

    def test_python_entry_defaults_are_base_algorithms(self):
        """Auch direkte Python-Aufrufe nehmen Zusatzverfahren nicht automatisch auf."""
        for function in (
            pipeline.experiment.create_instance_rows,
            pipeline.experiment.run_experiment_series,
            pipeline.routing_algorithms.run_algorithms,
        ):
            with self.subTest(function=function.__name__):
                self.assertEqual(inspect.signature(function).parameters["algorithms"].default, pipeline.DEFAULT_ALGORITHMS)

    def test_empty_selections_are_rejected(self):
        """Eine leere explizite Auswahl darf nicht auf die Defaults zurückfallen."""
        for argument in ("algorithms_override", "failures_override"):
            with self.subTest(argument=argument), self.assertRaises(ValueError):
                pipeline.run_pipeline(self.write_config(), dry_run=True, **{argument: []})

    def test_selection_and_resume_overrides_are_saved_effectively(self):
        """Verwendete Auswahl- und Resume-Overrides stehen in Config und Manifest."""
        result = pipeline.run_pipeline(
            self.write_config(),
            only_experiments=True,
            algorithms_override=["edp_paths"],
            failures_override=["random_node"],
            resume_override=False,
        )
        used_config = json.loads(
            (Path(result["manifest"]).parent / "used_config.json").read_text(
                encoding="utf-8"
            )
        )
        manifest = json.loads(Path(result["manifest"]).read_text(encoding="utf-8"))

        for stored in (result["config"], used_config, manifest):
            self.assertEqual(stored["algorithms"], ["edp_paths"])
            self.assertEqual(stored["failures"], ["random_node"])
            self.assertFalse(stored["resume"])

    def test_missing_parameter_group_is_rejected_before_summary(self):
        """Eine vollständig fehlende Failure-Parameterdatei darf nicht durchgehen."""
        self.config.update(
            algorithms=["edp_paths"],
            failures=["random_link"],
            fail_factors=[0.8, 1.6],
            metrics=["resilience"],
            resume=False,
        )
        result = pipeline.run_pipeline(self.write_config(), only_experiments=True)
        missing_file = next(
            Path(path) for path in result["generated_csvs"] if "ff1.6" in Path(path).name
        )
        missing_file.unlink()

        with self.assertRaisesRegex(ValueError, "Fehlende Parametergruppen"):
            pipeline.run_pipeline(self.config_path, only_plots=True)
        self.assertFalse(
            (self.root / "Output/summaries/feedback_test_summary.csv").exists()
        )

    def test_invalid_extension_runner_is_rejected_before_planning(self):
        """Nicht aufrufbare Zusatzalgorithmen werden früh erkannt."""
        self.config["algorithms"] = ["extra"]
        with patch.object(pipeline, "ALGORITHMS", pipeline.ALGORITHMS + ("extra",)), patch.dict(
            pipeline.routing_algorithms.EXTRA_ALGORITHM_RUNNERS, {"extra": None}
        ), self.assertRaisesRegex(ValueError, "RUNNER"):
            pipeline.run_pipeline(self.write_config(), dry_run=True)

    def test_invalid_graph_registration_is_rejected_before_cast(self):
        """Ein Graph ohne Parametervertrag liefert eine verständliche Meldung."""
        with patch.dict(pipeline.experiment.GRAPH_PARAMETER_SPECS, {}, clear=True), self.assertRaisesRegex(ValueError, "GRAPH_PARAMETER_SPECS"):
            pipeline.run_pipeline(self.write_config(), dry_run=True)

    def test_invalid_failure_registration_is_rejected(self):
        """Widersprüchliche Parametermetadaten werden nicht still akzeptiert."""
        with patch.dict(pipeline.failures.FAILURE_MODEL_SPECS, {"random": {}}), self.assertRaisesRegex(ValueError, "Parameterarten"):
            pipeline.run_pipeline(self.write_config(), dry_run=True)

    def test_new_cluster_models_use_cluster_parameter_validation(self):
        """Die Vorabprüfung nutzt die Modellmetadaten statt nur des Namens clustered."""
        self.config["failures"] = ["extra_node"]
        spec = dict(pipeline.failures.FAILURE_MODEL_SPECS["clustered"])
        with patch.dict(pipeline.FAILURE_COMBINATIONS, {"extra_node": ("extra_cluster", "node")}), patch.dict(
            pipeline.failures.FAILURE_MODEL_SPECS, {"extra_cluster": spec}
        ), patch.object(pipeline, "run_experiments") as run:
            for start, drop in ((0, 0.3), (1.3, 0.3), (0.8, 0), (0.8, 1.3), (float("nan"), 0.3)):
                self.config.update(failure_starts=[start], failure_drop=drop)
                with self.subTest(start=start, drop=drop), self.assertRaises(ValueError):
                    pipeline.run_pipeline(self.write_config())
            run.assert_not_called()

    def test_nonfinite_factors_are_rejected_before_experiments(self):
        """NaN und unendliche Faktoren dürfen keine langen Läufe starten."""
        with patch.object(pipeline, "run_experiments") as run:
            for factor in (float("nan"), float("inf"), -1):
                self.config["fail_factors"] = [factor]
                with self.subTest(factor=factor), self.assertRaises(ValueError):
                    pipeline.run_pipeline(self.write_config())
            run.assert_not_called()

    def test_plot_metadata_errors_stop_normal_runs(self):
        """Fehlende oder falsche Farben und Labels werden vor der Berechnung erkannt."""
        self.config["algorithms"] = ["edp_paths"]
        for field, value in (("ALGORITHM_COLORS", None), ("ALGORITHM_COLORS", "invalid-color"), ("ALGORITHM_LABELS", "")):
            with self.subTest(field=field, value=value), patch.dict(
                getattr(pipeline.result_analysis, field), {"edp_paths": value}
            ), patch.object(pipeline, "run_experiments") as run, self.assertRaisesRegex(ValueError, field):
                pipeline.run_pipeline(self.write_config())
            run.assert_not_called()
        self.assertFalse((self.root / "Output").exists())

    def test_experiment_only_does_not_require_plot_metadata(self):
        """Reine Rohdatenläufe benötigen keine Farben, ein vollständiger Preflight schon."""
        with patch.dict(pipeline.result_analysis.ALGORITHM_COLORS, {}, clear=True):
            result = pipeline.run_pipeline(self.write_config(), only_experiments=True)
            self.assertTrue(result["generated_csvs"])
            with self.assertRaisesRegex(ValueError, "ALGORITHM_COLORS"):
                pipeline.run_pipeline(self.config_path, preflight=True)

    def test_dry_run_does_not_write_results(self):
        """Die reine Plananzeige bleibt ohne Output-Nebenwirkungen."""
        pipeline.run_pipeline(self.write_config(), dry_run=True)
        self.assertFalse((self.root / "Output").exists())

    def test_conflicting_python_modes_fail_before_reading_config(self):
        """Widersprüchliche Modi scheitern auch ohne CLI vor Dateizugriffen."""
        with self.assertRaisesRegex(ValueError, "only_experiments and only_plots"):
            pipeline.run_pipeline(self.root / "missing.json", only_experiments=True, only_plots=True)
        self.assertFalse((self.root / "Output").exists())

    def test_direct_plot_calls_validate_metadata_before_creating_output(self):
        """Auch direkte Plotaufrufe liefern frühe verständliche Metadatenfehler."""
        analysis = pipeline.result_analysis
        figures_before = analysis.plt.get_fignums()
        for field in ("ALGORITHM_COLORS", "ALGORITHM_LABELS"):
            with self.subTest(field=field), patch.dict(getattr(analysis, field), {}, clear=True), self.assertRaisesRegex(ValueError, field):
                analysis.plot_all_comparisons(
                    None, ["small"], {"small": "Test"}, ["edp_paths"],
                    self.root / "plots", "Test", 1, show=False,
                )
        self.assertFalse((self.root / "plots").exists())
        self.assertEqual(figures_before, analysis.plt.get_fignums())
        self.assertEqual(analysis.failure_model_label("clustered_random_center"), "Clustered Random Center")

    def test_direct_cli_accepts_registered_models_and_preserves_both(self):
        """Neue Modelle sind ausdrücklich wählbar; both aktiviert sie nicht."""
        experiment = pipeline.experiment
        spec = dict(pipeline.failures.FAILURE_MODEL_SPECS["random"], csv_prefix="extra_random")
        original_selector = experiment.select_failures

        def select_extra(graph, source, destination, failure_type, failure_model, *args):
            """Simuliert einen separat implementierten Auswahlzweig für den Test."""
            return original_selector(graph, source, destination, failure_type, "random", *args)

        with patch.dict(experiment.FAILURE_MODEL_SPECS, {"extra_random": spec}):
            with patch.object(experiment, "run_experiment_series") as series:
                experiment.run_from_args(experiment.parse_args(["--p", "0.4"]))
                self.assertEqual(series.call_args.kwargs["failure_models"], ["random", "clustered"])
            args = experiment.parse_args([
                "--failure-model", "extra_random", "--nodes", "8", "--p", "0.4",
                "--runs", "1", "--seed", "123", "--output-dir", str(self.root / "extra"),
            ])
            with patch.object(experiment, "select_failures", side_effect=select_extra):
                outputs = experiment.run_from_args(args)
        self.assertEqual(len(outputs), 2)
        for output in outputs:
            with Path(output).open(encoding="utf-8", newline="") as file:
                rows = list(csv.DictReader(file))
            self.assertEqual(len(rows), 6)
            self.assertEqual({row["failureModel"] for row in rows}, {"extra_random"})

    def test_complete_graph_endpoint_rule_is_opt_in_and_limited(self):
        """Benachbarte Endpunkte werden nicht als allgemeiner Fallback verwendet."""
        experiment = pipeline.experiment
        graph = pipeline.nx.complete_graph(6)
        with self.assertRaises(pipeline.nx.NetworkXNoPath):
            experiment.choose_graph_endpoints(graph, random.Random(123), "complete_graph")
        with patch.dict(experiment.GRAPH_ENDPOINT_SELECTORS, {"complete_graph": experiment.choose_complete_graph_endpoints}):
            pair = experiment.choose_graph_endpoints(graph, random.Random(123), "complete_graph")
            self.assertEqual(pair, experiment.choose_graph_endpoints(graph, random.Random(123), "complete_graph"))
            self.assertTrue(graph.has_edge(*pair))
            for graph_type in ("erdos_renyi", "random_regular", "graphml"):
                with self.subTest(graph_type=graph_type), self.assertRaises(pipeline.nx.NetworkXNoPath):
                    experiment.choose_graph_endpoints(graph, random.Random(123), graph_type)
            with self.assertRaises(ValueError):
                experiment.choose_graph_endpoints(pipeline.nx.path_graph(6), random.Random(123), "complete_graph")

    def test_registered_complete_graph_runs_without_changing_base_defaults(self):
        """Ein vollständiger Zusatzgraph funktioniert mit seiner eigenen Endpunktregel."""
        experiment = pipeline.experiment
        self.config.update(failures=["random_link"], fail_factors=[0.0])
        self.config["datasets"] = [{"name": "complete", "type": "synthetic", "graph_type": "complete_graph", "nodes": 6}]
        with patch.dict(experiment.GRAPH_BUILDERS, {"complete_graph": lambda n, p, seed: pipeline.nx.complete_graph(n)}), patch.dict(
            experiment.GRAPH_PARAMETER_SPECS, {"complete_graph": {"config_key": None, "cast": str}}
        ), patch.dict(experiment.GRAPH_VALIDATORS, {"complete_graph": lambda *args: None}), patch.dict(
            experiment.GRAPH_ENDPOINT_SELECTORS, {"complete_graph": experiment.choose_complete_graph_endpoints}
        ):
            result = pipeline.run_pipeline(self.write_config(), only_experiments=True)
        with Path(result["generated_csvs"][0]).open(encoding="utf-8", newline="") as file:
            rows = list(csv.DictReader(file))
        self.assertEqual(len(rows), 6)
        self.assertEqual({row["success"] for row in rows}, {"1"})

    def test_invalid_endpoint_registration_fails_early(self):
        """Ein nicht aufrufbarer Endpunkt-Hook wird schon beim Planen abgewiesen."""
        with patch.dict(pipeline.experiment.GRAPH_ENDPOINT_SELECTORS, {"erdos_renyi": None}), self.assertRaisesRegex(ValueError, "GRAPH_ENDPOINT_SELECTORS"):
            pipeline.run_pipeline(self.write_config(), dry_run=True)

    def test_new_default_output_paths_are_inside_step5_Output(self):
        """Direkte Serien, CLI und Illustrationen verwenden den portablen Output-Ordner."""
        from illustrations import create_thesis_figures

        self.assertEqual(Path(pipeline.experiment.parse_args([]).output_dir), PIPELINE_ROOT / "Output")
        self.assertEqual(inspect.signature(pipeline.experiment.run_experiment_series).parameters["output_dir"].default, PIPELINE_ROOT / "Output")
        self.assertEqual(create_thesis_figures.DEFAULT_OUTPUT_DIR, PIPELINE_ROOT / "Output/illustrations")

    def test_progress_reports_jobs_and_completion(self):
        """Callback und CLI melden die abgeschlossenen Wiederholungen pro Job."""
        events = []
        self.config["runs"] = 2
        result = pipeline.run_pipeline(self.write_config(), only_experiments=True, progress_callback=events.append)
        self.assertEqual(events[0]["phase"], "preparation")
        self.assertEqual(events[-1]["phase"], "complete")
        self.assertTrue(Path(result["manifest"]).exists())
        progress = [event for event in events if event["phase"] == "experiment"]
        self.assertEqual({event["job_index"] for event in progress}, {1, 2, 3, 4})
        for job in range(1, 5):
            self.assertEqual([event["completed"] for event in progress if event["job_index"] == job], [0, 1, 2])
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            pipeline.run_pipeline(self.config_path, only_experiments=True)
        self.assertIn("Job 4/4", stdout.getvalue())
        self.assertIn("2/2 abgeschlossen (2 aus Resume)", stdout.getvalue())

    def test_progress_preserves_interruption_and_resume_results(self):
        """Eine Unterbrechung nach einer Fortschrittsmeldung verändert keine CSV-Werte."""
        events = []

        def interrupt(event):
            """Unterbricht nach zwei vollständig gespeicherten Wiederholungen."""
            if event.get("completed") == 2:
                raise RuntimeError("Testunterbrechung")

        kwargs = dict(
            runs=3, failure_types=["link", "node"], failure_models=["random", "clustered"],
            nodes=8, graph_param=0.4, seed=123, fail_factors=[0.8], failure_starts=[0.3],
        )
        with self.assertRaisesRegex(RuntimeError, "Testunterbrechung"):
            pipeline.experiment.run_experiment_series(**kwargs, output_dir=self.root / "resume", progress_callback=interrupt)
        resumed = pipeline.experiment.run_experiment_series(**kwargs, output_dir=self.root / "resume", resume=True, progress_callback=events.append)
        fresh = pipeline.experiment.run_experiment_series(**kwargs, output_dir=self.root / "fresh", progress_callback=lambda event: None)
        self.assertEqual([event["completed"] for event in events], [2, 3])
        for left, right in zip(resumed, fresh):
            self.assertEqual(Path(left).read_bytes(), Path(right).read_bytes())

    def test_progress_does_not_run_for_dry_run_or_preflight(self):
        """Planung und Vorabprüfung erzeugen keine irreführenden Laufmeldungen."""
        for mode in ("dry_run", "preflight"):
            events = []
            pipeline.run_pipeline(self.write_config(), **{mode: True}, progress_callback=events.append)
            self.assertEqual(events, [])

    def test_only_plots_can_use_raw_data_without_original_graphml(self):
        """Nur Plots bleibt ohne die ursprüngliche GraphML-Datei nutzbar."""
        graph_path = self.root / "graph.graphml"
        pipeline.nx.write_graphml(pipeline.nx.cycle_graph(8), graph_path)
        self.config["datasets"] = [{"name": "cycle", "type": "graphml", "graphml": str(graph_path)}]
        self.config["metrics"] = ["resilience"]
        self.config["failures"] = ["random_link"]
        pipeline.run_pipeline(self.write_config(), only_experiments=True)
        graph_path.unlink()
        result = pipeline.run_pipeline(self.config_path, only_plots=True)
        self.assertEqual(len(result["plots"]), 2)
        manifest = json.loads(Path(result["manifest"]).read_text(encoding="utf-8"))
        self.assertIsNone(manifest["provenance"]["input_graphs"][str(graph_path)])

    def test_manifest_records_packages_and_input_hashes(self):
        """Ein Lauf enthält Paketversionen und Prüfsummen für Code und GraphML."""
        graph_path = self.root / "graph.graphml"
        pipeline.nx.write_graphml(pipeline.nx.cycle_graph(8), graph_path)
        self.config["datasets"] = [{"name": "cycle", "type": "graphml", "graphml": str(graph_path)}]
        result = pipeline.run_pipeline(self.write_config(), only_experiments=True)
        manifest = json.loads(Path(result["manifest"]).read_text(encoding="utf-8"))
        provenance = manifest["provenance"]
        self.assertIn("networkx", {name.lower() for name in provenance["package_versions"]})
        self.assertIn("src/routing_algorithms.py", provenance["code_fingerprint"]["files"])
        self.assertEqual(len(provenance["code_fingerprint"]["digest"]), 64)
        self.assertEqual(len(provenance["input_graphs"][str(graph_path)]), 64)

    def test_code_hash_is_portable_and_changes_with_source(self):
        """Output und Dokumentation beeinflussen den definierten Code-Hash nicht."""
        with patch.object(pipeline, "PIPELINE_ROOT", self.root):
            (self.root / "src").mkdir()
            code = self.root / "src/example.py"
            code.write_text("value = 1\n", encoding="utf-8")
            first = pipeline.collect_run_provenance([])["code_fingerprint"]
            (self.root / "Output").mkdir()
            (self.root / "Output/result.csv").write_text("x\n1\n", encoding="utf-8")
            second = pipeline.collect_run_provenance([])["code_fingerprint"]
            self.assertEqual(first, second)
            self.assertEqual(list(first["files"]), ["src/example.py"])
            copied_root = self.root / "moved"
            (copied_root / "src").mkdir(parents=True)
            (copied_root / "src/example.py").write_bytes(code.read_bytes())
            with patch.object(pipeline, "PIPELINE_ROOT", copied_root):
                self.assertEqual(first, pipeline.collect_run_provenance([])["code_fingerprint"])
            code.write_text("value = 2\n", encoding="utf-8")
            self.assertNotEqual(first["digest"], pipeline.collect_run_provenance([])["code_fingerprint"]["digest"])

    def test_dependency_error_contains_install_command(self):
        """CLI und GUI verweisen bei fehlenden Paketen auf dieselbe existierende Datei."""
        requirements = PIPELINE_ROOT / "Dokumentation/requirements.txt"
        self.assertTrue(requirements.is_file())
        for gui in (False, True):
            with self.subTest(gui=gui), patch.object(
                pipeline.environment_check.importlib, "import_module", side_effect=ModuleNotFoundError("missing")
            ), self.assertRaises(RuntimeError) as error:
                pipeline.environment_check.check_dependencies(gui=gui)
            self.assertIn(str(requirements), str(error.exception))

    def test_old_python_is_rejected_before_importing_libraries(self):
        """Ein ungeeigneter Interpreter wird vor Typannotationen und Bibliotheken erkannt."""
        with patch.object(pipeline.environment_check.sys, "version_info", (3, 9)), patch.object(
            pipeline.environment_check.importlib, "import_module"
        ) as importer, self.assertRaisesRegex(RuntimeError, "Python 3.10"):
            pipeline.environment_check.check_dependencies()
        importer.assert_not_called()


if __name__ == "__main__":
    unittest.main()
