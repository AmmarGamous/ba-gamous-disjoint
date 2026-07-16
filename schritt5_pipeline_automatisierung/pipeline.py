"""Konfigurationsgetriebene Pipeline für Schritt 5.

Die Pipeline verbindet den Schritt-4-Experimentgenerator mit der vorhandenen
Auswertung: Eine JSON-Konfiguration beschreibt Algorithmen, Failure-Modelle,
Datasets und Laufparameter; die Pipeline erzeugt daraus Rohdaten, Summary-CSV
und paper-nahe PNG/SVG-Plots.
"""

import argparse
import importlib
import json
from pathlib import Path
import platform
import sys
from datetime import datetime, timezone

import networkx as nx


PIPELINE_ROOT = Path(__file__).resolve().parent
REPO_ROOT = PIPELINE_ROOT.parent
STEP5_SRC = PIPELINE_ROOT / "src"
STEP5_EVALUATION = PIPELINE_ROOT / "evaluation"
for import_path in (STEP5_SRC, STEP5_EVALUATION):
    if str(import_path) not in sys.path:
        sys.path.insert(0, str(import_path))


def _import_local_module(module_name, expected_path):
    """Importiert ein Modul frisch aus dem lokalen Schritt-5-Ordner."""
    expected_path = expected_path.resolve()
    if module_name in sys.modules:
        del sys.modules[module_name]

    module = importlib.import_module(module_name)
    module_path = Path(module.__file__).resolve()
    if module_path != expected_path:
        raise ImportError(
            f"{module_name} wurde aus {module_path} statt aus {expected_path} geladen"
        )
    return module


failures = _import_local_module("failures", STEP5_SRC / "failures.py")
routing_algorithms = _import_local_module(
    "routing_algorithms", STEP5_SRC / "routing_algorithms.py"
)
experiment = _import_local_module("experiment", STEP5_SRC / "experiment.py")
result_analysis = _import_local_module(
    "result_analysis", STEP5_EVALUATION / "result_analysis.py"
)
ALGORITHMS = routing_algorithms.ALGORITHMS


# Schritt-7-Erweiterungspunkt: neue auswählbare Failure-Kombinationen hier
# aufnehmen. Das Modell selbst muss in src/failures.py registriert sein.
FAILURE_COMBINATIONS = {
    "random_link": ("random", "link"),
    "random_node": ("random", "node"),
    "clustered_link": ("clustered", "link"),
    "clustered_node": ("clustered", "node"),
}
DEFAULT_FAILURES = tuple(FAILURE_COMBINATIONS)


def resolve_repo_path(value):
    """Löst relative Ausgabepfade stabil vom Schritt-5-Ordner aus auf."""
    path = Path(value)
    return path if path.is_absolute() else PIPELINE_ROOT / path


def resolve_pipeline_path(value):
    """Löst relative Code-/Datenpfade stabil vom Schritt-5-Ordner aus auf."""
    path = Path(value)
    return path if path.is_absolute() else PIPELINE_ROOT / path


def resolve_config_path(value):
    """Findet Configs relativ zum Arbeitsordner oder zur Step-5-Kopie."""
    path = Path(value)
    if path.is_absolute():
        return path
    cwd_path = Path.cwd() / path
    return cwd_path if cwd_path.is_file() else PIPELINE_ROOT / path


def load_config(config_path):
    """Lädt eine JSON-Konfiguration und ergänzt stabile Defaults."""
    config_path = resolve_config_path(config_path)
    with config_path.open(encoding="utf-8") as config_file:
        config = json.load(config_file)

    run_name = config.get("run_name") or config_path.stem
    config["run_name"] = run_name
    config.setdefault(
        "output_root",
        str(Path("Output") / run_name),
    )
    config.setdefault("runs", 5)
    config.setdefault("seed", 123)
    config.setdefault("resume", True)
    config.setdefault("algorithms", list(ALGORITHMS))
    config.setdefault("failures", list(DEFAULT_FAILURES))
    config.setdefault("metrics", ["resilience", "avgHops", "avgStretch"])
    if not config.get("datasets"):
        raise ValueError("Config must contain at least one dataset")
    return config


def apply_config_overrides(
    config,
    run_name_override=None,
    output_root_override=None,
    runs_override=None,
    seed_override=None,
    fail_factors_override=None,
    failure_starts_override=None,
    failure_drop_override=None,
):
    """Überschreibt globale Config-Werte mit optionalen CLI-Parametern."""
    if run_name_override is not None:
        config["run_name"] = run_name_override
        if output_root_override is None:
            config["output_root"] = str(Path("Output") / run_name_override)
    if output_root_override is not None:
        config["output_root"] = output_root_override
    if runs_override is not None:
        config["runs"] = runs_override
    if seed_override is not None:
        config["seed"] = seed_override
    if fail_factors_override is not None:
        config["fail_factors"] = fail_factors_override
    if failure_starts_override is not None:
        config["failure_starts"] = failure_starts_override
    if failure_drop_override is not None:
        config["failure_drop"] = failure_drop_override
    return config


def selected_algorithms(config, override=None):
    """Validiert und liefert die Algorithmusauswahl."""
    algorithms = list(override or config.get("algorithms", ALGORITHMS))
    unknown = sorted(set(algorithms) - set(ALGORITHMS))
    if unknown:
        raise ValueError(f"Unknown algorithms: {unknown}")
    return algorithms


def selected_failures(config, override=None):
    """Validiert und liefert Failure-Kombinationen als (model, type)."""
    names = list(override or config.get("failures", DEFAULT_FAILURES))
    unknown = sorted(set(names) - set(FAILURE_COMBINATIONS))
    if unknown:
        raise ValueError(f"Unknown failures: {unknown}")
    selected = [(name, FAILURE_COMBINATIONS[name]) for name in names]
    for _, (failure_model, _) in selected:
        failures.failure_model_spec(failure_model)
    return selected


def selected_datasets(config, override=None):
    """Filtert Datasets optional per Name."""
    datasets = [dict(dataset) for dataset in config["datasets"]]
    if override:
        wanted = set(override)
        datasets = [dataset for dataset in datasets if dataset["name"] in wanted]
        missing = sorted(wanted - {dataset["name"] for dataset in datasets})
        if missing:
            raise ValueError(f"Unknown datasets: {missing}")
    return datasets


def apply_dataset_overrides(
    datasets,
    graph_type_override=None,
    nodes_override=None,
    p_override=None,
    degree_override=None,
    fail_factors_override=None,
    failure_starts_override=None,
    failure_drop_override=None,
):
    """Überschreibt Graph- und Failureparameter für ausgewählte Datasets."""
    updated = []
    for dataset in datasets:
        dataset = dict(dataset)
        if dataset.get("type", "synthetic") == "synthetic":
            if graph_type_override is not None:
                dataset["graph_type"] = graph_type_override
            if nodes_override is not None:
                dataset["nodes"] = nodes_override
            if p_override is not None:
                dataset["p"] = p_override
            if degree_override is not None:
                dataset["degree"] = degree_override
        if fail_factors_override is not None:
            dataset["fail_factors"] = fail_factors_override
        if failure_starts_override is not None:
            dataset["failure_starts"] = failure_starts_override
        if failure_drop_override is not None:
            dataset["failure_drop"] = failure_drop_override
        updated.append(dataset)
    return updated


def dataset_parameters(config, dataset):
    """Liefert die effektiven Failureparameter für ein Dataset."""
    return {
        "fail_factors": dataset.get(
            "fail_factors", config.get("fail_factors", [1.0])
        ),
        "failure_starts": dataset.get(
            "failure_starts", config.get("failure_starts", [0.9])
        ),
        "failure_drop": dataset.get(
            "failure_drop", config.get("failure_drop", 0.3)
        ),
    }


def metric_specs(metric_names):
    """Übersetzt kurze Metriknamen in result_analysis-Spezifikationen."""
    available = {
        "resilience": ("resilience", "Resilience", (0, 1.05)),
        "avgHops": ("avgHops", "Average Hops (successful routes)", None),
        "avgStretch": ("avgStretch", "Average Stretch (successful routes)", None),
    }
    unknown = sorted(set(metric_names) - set(available))
    if unknown:
        raise ValueError(f"Unknown metrics: {unknown}")
    return [available[name] for name in metric_names]


def dataset_output_dir(output_root, dataset):
    """Liefert den Rohdatenordner für ein Dataset innerhalb des Outputs."""
    return Path(output_root) / "raw" / dataset["name"]


def graphml_node_count(graphml_path, fallback=0):
    """Liest die Knotenzahl eines GraphML-Datasets für Plan- und Dry-Run-Ausgaben."""
    graphml_path = Path(graphml_path)
    if not graphml_path.is_file():
        return int(fallback or 0)
    return nx.read_graphml(graphml_path).number_of_nodes()


def build_experiment_plan(config, algorithms=None, failures=None, datasets=None):
    """Erzeugt die konkreten Experimentaufrufe aus der Pipeline-Konfiguration."""
    output_root = resolve_repo_path(config["output_root"])
    algorithms = algorithms or selected_algorithms(config)
    failures = failures or selected_failures(config)
    datasets = datasets or selected_datasets(config)
    plan = []
    for dataset in datasets:
        dataset_type = dataset.get("type", "synthetic")
        parameters = dataset_parameters(config, dataset)
        for failure_name, (failure_model, failure_type) in failures:
            item = {
                "dataset": dataset,
                "failure": failure_name,
                "failure_model": failure_model,
                "failure_type": failure_type,
                "algorithms": algorithms,
                "output_dir": dataset_output_dir(output_root, dataset),
                "fail_factors": parameters["fail_factors"],
                "failure_starts": parameters["failure_starts"],
                "failure_drop": parameters["failure_drop"],
            }
            if dataset_type == "synthetic":
                graph_type = dataset.get("graph_type", "erdos_renyi")
                item.update(
                    {
                        "graph_type": graph_type,
                        "nodes": int(dataset["nodes"]),
                        "graph_param": experiment.graph_parameter_from_dataset(
                            dataset
                        ),
                        "graphml_path": None,
                        "graph_name": dataset.get("graph_name", dataset["name"]),
                    }
                )
            elif dataset_type == "graphml":
                graphml_path = resolve_pipeline_path(dataset["graphml"])
                item.update(
                    {
                        "graph_type": "graphml",
                        "nodes": graphml_node_count(
                            graphml_path, dataset.get("nodes", 0)
                        ),
                        "graph_param": dataset.get("p", dataset.get("graph_param", "")),
                        "graphml_path": graphml_path,
                        "graph_name": dataset.get("graph_name", dataset["name"]),
                    }
                )
            else:
                raise ValueError(f"Unknown dataset type: {dataset_type}")
            plan.append(item)
    return plan


def run_experiments(config, plan, resume_override=None):
    """Führt alle geplanten Experimentserien aus."""
    generated = []
    for item in plan:
        failure_model = item["failure_model"]
        outputs = experiment.run_experiment_series(
            runs=int(config["runs"]),
            failure_types=[item["failure_type"]],
            failure_models=[failure_model],
            algorithms=item["algorithms"],
            graph_type=item["graph_type"],
            nodes=item["nodes"],
            graph_param=item["graph_param"],
            graphml_path=item["graphml_path"],
            graph_name=item["graph_name"],
            fail_factors=item["fail_factors"],
            failure_starts=item["failure_starts"],
            failure_drop=float(item["failure_drop"]),
            output_dir=item["output_dir"],
            seed=config.get("seed"),
            resume=config["resume"] if resume_override is None else resume_override,
        )
        generated.extend(outputs)
    return generated


def write_summary_and_plots(config, datasets, algorithms, failures):
    """Aggregiert CSVs und erzeugt Summary sowie PNG/SVG-Plots."""
    output_root = resolve_repo_path(config["output_root"])
    directories = {
        dataset["name"]: dataset_output_dir(output_root, dataset)
        for dataset in datasets
    }
    display_names = {
        dataset["name"]: dataset.get("display_name", dataset["name"])
        for dataset in datasets
    }
    raw, _ = result_analysis.load_result_directories(directories)
    _, summary = result_analysis.aggregate_results(raw)
    result_analysis.validate_summary(summary, int(config["runs"]), algorithms)

    summary_dir = output_root / "summaries"
    summary_dir.mkdir(parents=True, exist_ok=True)
    summary_path = summary_dir / f"{config['run_name']}_summary.csv"
    summary.to_csv(summary_path, index=False)

    plot_groups = config.get("plot_groups") or [
        {
            "name": "all_graphs",
            "title": config.get("title", config["run_name"]),
            "datasets": list(directories),
        }
    ]
    plot_paths = []
    for group in plot_groups:
        group_datasets = [
            dataset for dataset in group.get("datasets", [])
            if dataset in directories
        ]
        if not group_datasets:
            continue
        title = group.get("title", group["name"])
        plot_paths.extend(
            result_analysis.plot_all_comparisons(
                summary,
                datasets=group_datasets,
                display_names=display_names,
                algorithms=algorithms,
                output_dir=output_root / "plots" / group["name"],
                title_prefix=f"{config.get('title', config['run_name'])}: {title}",
                runs=int(config["runs"]),
                metrics=metric_specs(config.get("metrics", [])),
                failure_combinations=[combination for _, combination in failures],
                show=False,
            )
        )
    return summary_path, plot_paths


def write_used_config(config, output_root):
    """Speichert die effektive Konfiguration neben den Ergebnissen."""
    destination = Path(output_root) / "used_config.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="utf-8") as config_file:
        json.dump(config, config_file, indent=2)
        config_file.write("\n")
    return destination


def validate_preflight(config, plan):
    """Prüft Konfiguration, Eingabedateien und Output-Ziel vor dem Lauf."""
    if int(config["runs"]) <= 0:
        raise ValueError("runs must be greater than 0")

    metric_specs(config.get("metrics", []))
    output_root = resolve_repo_path(config["output_root"])
    output_root.mkdir(parents=True, exist_ok=True)
    probe = output_root / ".preflight_write_check"
    probe.write_text("ok", encoding="utf-8")
    probe.unlink()

    for item in plan:
        dataset = item["dataset"]
        dataset_type = dataset.get("type", "synthetic")
        if not item["algorithms"]:
            raise ValueError("At least one algorithm must be selected")
        if not item["fail_factors"]:
            raise ValueError(f"{dataset['name']}: fail_factors must not be empty")
        if not item["failure_starts"]:
            raise ValueError(f"{dataset['name']}: failure_starts must not be empty")
        if any(float(value) < 0 for value in item["fail_factors"]):
            raise ValueError(f"{dataset['name']}: fail_factors must be >= 0")
        if any(not 0 <= float(value) <= 1 for value in item["failure_starts"]):
            raise ValueError(f"{dataset['name']}: failure_starts must be in [0, 1]")
        if float(item["failure_drop"]) <= 0:
            raise ValueError(f"{dataset['name']}: failure_drop must be > 0")

        if dataset_type == "synthetic":
            experiment.validate_graph_parameters(
                item["graph_type"],
                item["nodes"],
                item["graph_param"],
                dataset["name"],
            )
        elif dataset_type == "graphml":
            graphml_path = Path(item["graphml_path"])
            if not graphml_path.is_file():
                raise FileNotFoundError(
                    f"{dataset['name']}: GraphML file not found: {graphml_path}"
                )
        else:
            raise ValueError(f"{dataset['name']}: unknown dataset type {dataset_type}")

    return [
        f"datasets={len({item['dataset']['name'] for item in plan})}",
        f"jobs={len(plan)}",
        f"output_root={output_root}",
    ]


def write_manifest(config, config_path, plan, generated_csvs, summary_path, plot_paths):
    """Schreibt Metadaten für Repeatability und spätere Kontrolle."""
    output_root = resolve_repo_path(config["output_root"])
    manifest = {
        "run_name": config["run_name"],
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "python": sys.version,
        "platform": platform.platform(),
        "config_path": str(Path(config_path).resolve()),
        "runs": int(config["runs"]),
        "seed": config.get("seed"),
        "resume": bool(config.get("resume", False)),
        "algorithms": list(plan[0]["algorithms"]) if plan else [],
        "failures": sorted({item["failure"] for item in plan}),
        "fail_factors": config.get("fail_factors", []),
        "failure_starts": config.get("failure_starts", []),
        "failure_drop": config.get("failure_drop"),
        "job_failure_parameters": [
            {
                "dataset": item["dataset"]["name"],
                "failure": item["failure"],
                "fail_factors": item["fail_factors"],
                "failure_starts": item["failure_starts"],
                "failure_drop": item["failure_drop"],
            }
            for item in plan
        ],
        "datasets": sorted({item["dataset"]["name"] for item in plan}),
        "plot_groups": config.get("plot_groups", []),
        "dataset_configs": list(
            {
                item["dataset"]["name"]: item["dataset"]
                for item in plan
            }.values()
        ),
        "generated_csvs": [str(Path(path)) for path in generated_csvs],
        "summary": str(summary_path) if summary_path else "",
        "plots": [str(Path(path)) for path in plot_paths],
    }
    manifest_path = output_root / "manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with manifest_path.open("w", encoding="utf-8") as manifest_file:
        json.dump(manifest, manifest_file, indent=2)
        manifest_file.write("\n")
    return manifest_path


def run_pipeline(
    config_path,
    dry_run=False,
    only_experiments=False,
    only_plots=False,
    algorithms_override=None,
    failures_override=None,
    datasets_override=None,
    resume_override=None,
    run_name_override=None,
    output_root_override=None,
    runs_override=None,
    seed_override=None,
    fail_factors_override=None,
    failure_starts_override=None,
    failure_drop_override=None,
    graph_type_override=None,
    nodes_override=None,
    p_override=None,
    degree_override=None,
    preflight=False,
):
    """Haupteinstieg für Tests und CLI."""
    if dry_run and preflight:
        raise ValueError("dry_run and preflight cannot be combined")

    config = load_config(config_path)
    apply_config_overrides(
        config,
        run_name_override=run_name_override,
        output_root_override=output_root_override,
        runs_override=runs_override,
        seed_override=seed_override,
        fail_factors_override=fail_factors_override,
        failure_starts_override=failure_starts_override,
        failure_drop_override=failure_drop_override,
    )
    algorithms = selected_algorithms(config, algorithms_override)
    failures = selected_failures(config, failures_override)
    datasets = selected_datasets(config, datasets_override)
    datasets = apply_dataset_overrides(
        datasets,
        graph_type_override=graph_type_override,
        nodes_override=nodes_override,
        p_override=p_override,
        degree_override=degree_override,
        fail_factors_override=fail_factors_override,
        failure_starts_override=failure_starts_override,
        failure_drop_override=failure_drop_override,
    )
    config["datasets"] = datasets
    plan = build_experiment_plan(config, algorithms, failures, datasets)

    preflight_messages = validate_preflight(config, plan) if preflight else []

    if dry_run or preflight:
        return {
            "config": config,
            "plan": plan,
            "dry_run": bool(dry_run),
            "preflight": preflight_messages,
            "generated_csvs": [],
            "summary": None,
            "plots": [],
            "manifest": None,
        }

    output_root = resolve_repo_path(config["output_root"])
    write_used_config(config, output_root)

    generated_csvs = []
    if not only_plots:
        generated_csvs = run_experiments(config, plan, resume_override)

    summary_path = None
    plot_paths = []
    if not only_experiments:
        summary_path, plot_paths = write_summary_and_plots(
            config, datasets, algorithms, failures
        )

    manifest_path = write_manifest(
        config, config_path, plan, generated_csvs, summary_path, plot_paths
    )
    return {
        "config": config,
        "plan": plan,
        "dry_run": False,
        "preflight": preflight_messages,
        "generated_csvs": generated_csvs,
        "summary": summary_path,
        "plots": plot_paths,
        "manifest": manifest_path,
    }


def parse_args(argv=None):
    """Parst die CLI-Argumente für Pipeline-Läufe."""
    parser = argparse.ArgumentParser(description="Run the Step-5 experiment pipeline")
    parser.add_argument("--config", required=True, help="JSON pipeline configuration")
    parser.add_argument("--dry-run", action="store_true", help="Print planned jobs only")
    parser.add_argument("--preflight", action="store_true", help="Validate config and paths only")
    parser.add_argument("--only-experiments", action="store_true")
    parser.add_argument("--only-plots", action="store_true")
    parser.add_argument("--resume", action="store_true", help="Force resume on")
    parser.add_argument("--no-resume", action="store_true", help="Force resume off")
    parser.add_argument("--algorithms", nargs="+", choices=ALGORITHMS)
    parser.add_argument("--failures", nargs="+", choices=sorted(FAILURE_COMBINATIONS))
    parser.add_argument("--datasets", nargs="+", help="Dataset names from config")
    parser.add_argument("--run-name", help="Override run_name and default output folder")
    parser.add_argument("--output-root", help="Override output root directory")
    parser.add_argument("--runs", type=int, help="Override number of repetitions")
    parser.add_argument("--seed", type=int, help="Override random seed")
    parser.add_argument(
        "--fail-factor",
        dest="fail_factors",
        type=float,
        nargs="+",
        help="Override random failure factors",
    )
    parser.add_argument(
        "--failure-start",
        dest="failure_starts",
        type=float,
        nargs="+",
        help="Override clustered failure starts",
    )
    parser.add_argument("--failure-drop", type=float, help="Override clustered drop")
    parser.add_argument(
        "--graph-type",
        choices=experiment.GRAPH_TYPES,
        help="Override graph type for selected synthetic datasets",
    )
    parser.add_argument("--nodes", type=int, help="Override n for synthetic datasets")
    parser.add_argument("--p", type=float, help="Override p for Erdos-Renyi datasets")
    parser.add_argument(
        "--degree",
        type=int,
        help="Override degree for random-regular datasets",
    )
    return parser.parse_args(argv)


def main(argv=None):
    """Startet die Pipeline über die Kommandozeile."""
    args = parse_args(argv)
    if args.dry_run and args.preflight:
        raise ValueError("--dry-run and --preflight cannot be combined")
    if args.only_experiments and args.only_plots:
        raise ValueError("--only-experiments and --only-plots cannot be combined")
    resume_override = None
    if args.resume:
        resume_override = True
    if args.no_resume:
        resume_override = False

    result = run_pipeline(
        args.config,
        dry_run=args.dry_run,
        only_experiments=args.only_experiments,
        only_plots=args.only_plots,
        algorithms_override=args.algorithms,
        failures_override=args.failures,
        datasets_override=args.datasets,
        resume_override=resume_override,
        run_name_override=args.run_name,
        output_root_override=args.output_root,
        runs_override=args.runs,
        seed_override=args.seed,
        fail_factors_override=args.fail_factors,
        failure_starts_override=args.failure_starts,
        failure_drop_override=args.failure_drop,
        graph_type_override=args.graph_type,
        nodes_override=args.nodes,
        p_override=args.p,
        degree_override=args.degree,
        preflight=args.preflight,
    )
    if args.preflight:
        print("preflight ok", ", ".join(result["preflight"]))
        return
    if args.dry_run:
        for item in result["plan"]:
            print(
                "plan",
                item["dataset"]["name"],
                item["failure"],
                "runs",
                result["config"]["runs"],
                "graph",
                item["graph_type"],
                item["nodes"],
                item["graph_param"],
                "fail_factors",
                item["fail_factors"],
                "failure_starts",
                item["failure_starts"],
                "->",
                item["output_dir"],
            )
        return
    print("manifest", result["manifest"])
    if result["summary"]:
        print("summary", result["summary"])
    print("plots", len(result["plots"]))


if __name__ == "__main__":
    main()
