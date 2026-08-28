"""Streamlit-Oberfläche für die Schritt-5-Pipeline.

Die GUI ersetzt die Pipeline nicht. Sie sammelt Parameter, schreibt daraus eine
JSON-Konfiguration und ruft anschließend pipeline.run_pipeline auf.
"""

import json
from pathlib import Path
import sys
from decimal import Decimal


PIPELINE_ROOT = Path(__file__).resolve().parent
REPO_ROOT = PIPELINE_ROOT.parent
if str(PIPELINE_ROOT) not in sys.path:
    sys.path.insert(0, str(PIPELINE_ROOT))

STEP5_MODULES = (
    "pipeline",
    "experiment",
    "failures",
    "routing_algorithms",
    "result_analysis",
)


def _clear_cached_step5_modules():
    """Entfernt geladene Schritt-5-Module, damit Streamlit keinen alten Code nutzt."""
    for module_name in STEP5_MODULES:
        sys.modules.pop(module_name, None)


_clear_cached_step5_modules()

import pipeline

if Path(pipeline.__file__).resolve() != (PIPELINE_ROOT / "pipeline.py").resolve():
    raise ImportError(
        f"pipeline wurde aus {pipeline.__file__} statt aus {PIPELINE_ROOT / 'pipeline.py'} geladen"
    )


# Schritt-7-Erweiterungspunkt: sichtbare Namen für neue Algorithmen ergänzen.
ALGORITHM_LABELS = {
    "edp_paths": "EDP Paths",
    "edp_one_tree": "EDP One Tree",
    "edp_multiple_trees": "EDP Multiple Trees",
    "ndp_paths": "NDP Paths",
    "ndp_one_tree": "NDP One Tree",
    "ndp_multiple_trees": "NDP Multiple Trees",
}

# Schritt-7-Erweiterungspunkt: sichtbare Namen für neue Failure-Auswahlen.
FAILURE_LABELS = {
    "random_link": "Link Random",
    "clustered_link": "Link Clustered",
    "random_node": "Node Random",
    "clustered_node": "Node Clustered",
}

DEFAULT_SEED = 123
REAL_WORLD_FAIL_FACTORS = [float(value) for value in range(1, 11)]
CLUSTERED_FAILURE_STARTS = [round(value / 10, 1) for value in range(3, 10)]
CLUSTERED_FAILURE_DROP = 0.3

ERDOS_RENYI_DATASETS = {
    "synthetic_n25_p015": {
        "name": "synthetic_n25_p015",
        "display_name": "Erdos-Renyi n=25, p=0.15",
        "type": "synthetic",
        "graph_type": "erdos_renyi",
        "nodes": 25,
        "p": 0.15,
        "fail_factors": [0.8, 1.6, 2.4, 3.2, 4.0, 4.8, 5.6, 6.4, 7.2, 8.0, 8.8],
        "failure_starts": CLUSTERED_FAILURE_STARTS,
        "failure_drop": CLUSTERED_FAILURE_DROP,
    },
    "synthetic_n50_p015": {
        "name": "synthetic_n50_p015",
        "display_name": "Erdos-Renyi n=50, p=0.15",
        "type": "synthetic",
        "graph_type": "erdos_renyi",
        "nodes": 50,
        "p": 0.15,
        "fail_factors": [
            0.8, 1.6, 2.4, 3.2, 4.0, 4.8, 5.6, 6.4, 7.2, 8.0, 8.8,
            9.6, 10.4, 11.2, 12.0, 12.8, 13.6, 14.4, 15.2, 16.0, 16.8,
        ],
        "failure_starts": CLUSTERED_FAILURE_STARTS,
        "failure_drop": CLUSTERED_FAILURE_DROP,
    },
    "synthetic_n100_p002": {
        "name": "synthetic_n100_p002",
        "display_name": "Erdos-Renyi n=100, p=0.02",
        "type": "synthetic",
        "graph_type": "erdos_renyi",
        "nodes": 100,
        "p": 0.02,
        "fail_factors": [
            0.8, 1.6, 2.4, 3.2, 4.0, 4.8, 5.6, 6.4, 7.2, 8.0, 8.8,
            9.6, 10.4, 11.2, 12.0, 12.8, 13.6, 14.4, 15.2, 16.0, 16.8,
            17.6, 18.4, 19.2, 20.0, 20.8, 21.6, 22.4, 23.2, 24.0,
            24.8, 25.6, 26.4, 27.2, 28.0, 28.8, 29.6, 30.4, 31.2,
            32.0, 32.8, 33.6, 34.4, 35.2, 36.0, 36.8, 37.6, 38.4,
            39.2, 40.0, 40.8, 41.6, 42.4, 43.2, 44.0, 44.8, 45.6,
            46.4, 47.2, 48.0, 48.8, 49.6,
        ],
        "failure_starts": CLUSTERED_FAILURE_STARTS,
        "failure_drop": CLUSTERED_FAILURE_DROP,
    },
}

REAL_WORLD_DATASETS = {
    "real_attmpls": {
        "name": "real_attmpls",
        "display_name": "Small: ATT-MPLS",
        "type": "graphml",
        "graphml": "data/topology_zoo/AttMpls.graphml",
        "graph_name": "attmpls",
        "fail_factors": list(REAL_WORLD_FAIL_FACTORS),
        "failure_starts": list(CLUSTERED_FAILURE_STARTS),
        "failure_drop": CLUSTERED_FAILURE_DROP,
    },
    "real_oteglobe": {
        "name": "real_oteglobe",
        "display_name": "Medium: Oteglobe",
        "type": "graphml",
        "graphml": "data/topology_zoo/Oteglobe.graphml",
        "graph_name": "oteglobe",
        "fail_factors": REAL_WORLD_FAIL_FACTORS,
        "failure_starts": CLUSTERED_FAILURE_STARTS,
        "failure_drop": CLUSTERED_FAILURE_DROP,
    },
    "real_cogentco": {
        "name": "real_cogentco",
        "display_name": "Large: Cogentco",
        "type": "graphml",
        "graphml": "data/topology_zoo/Cogentco.graphml",
        "graph_name": "cogentco",
        "fail_factors": REAL_WORLD_FAIL_FACTORS,
        "failure_starts": CLUSTERED_FAILURE_STARTS,
        "failure_drop": CLUSTERED_FAILURE_DROP,
    },
}

# Schritt-7-Erweiterungspunkt: neue Graph-Typen in der GUI benennen.
GRAPH_TYPE_LABELS = {
    "random_erdos": "Random (Erdos-Renyi)",
    "real_world": "Real-World",
}


def parse_number_list(text, cast=float):
    """Parst kommagetrennte oder leerzeichengetrennte Zahlenlisten."""
    values = []
    for part in text.replace(",", " ").replace(";", " ").split():
        values.append(cast(part))
    if not values:
        raise ValueError("At least one value is required")
    return values


def format_number_list(values):
    """Formatiert Zahlenlisten für GUI-Textfelder."""
    return " ".join(str(value) for value in values)


def build_failure_rate_range(start, stop, step):
    """Erzeugt inklusive Werte für Failure-Rate-Bereiche."""
    start_value = Decimal(str(start))
    stop_value = Decimal(str(stop))
    step_value = Decimal(str(step))
    if step_value <= 0:
        raise ValueError("step must be greater than 0")
    if stop_value < start_value:
        raise ValueError("stop must be greater than or equal to start")

    values = []
    current = start_value
    epsilon = step_value / Decimal("1000000")
    while current <= stop_value + epsilon:
        values.append(float(current))
        current += step_value
    return values


def _safe_decimal_token(value):
    """Formatiert Dezimalzahlen stabil für Dataset-Namen."""
    return str(value).replace(".", "p").replace("-", "m")


def build_custom_erdos_renyi_dataset(
    name,
    nodes,
    p,
    fail_factors=None,
    failure_starts=None,
    failure_drop=None,
):
    """Baut ein frei konfiguriertes Erdős-Rényi-Dataset für die Pipeline."""
    dataset = {
        "name": name,
        "display_name": f"Erdos-Renyi n={int(nodes)}, p={float(p):g}",
        "type": "synthetic",
        "graph_type": "erdos_renyi",
        "nodes": int(nodes),
        "p": float(p),
    }
    if fail_factors is not None:
        dataset["fail_factors"] = list(fail_factors)
    if failure_starts is not None:
        dataset["failure_starts"] = list(failure_starts)
    if failure_drop is not None:
        dataset["failure_drop"] = float(failure_drop)
    return dataset


def build_random_regular_dataset(name, nodes, degree):
    """Baut ein Random-Regular-Dataset für die Pipeline-Konfiguration."""
    return {
        "name": name,
        "display_name": f"Random Regular n={int(nodes)}, degree={int(degree)}",
        "type": "synthetic",
        "graph_type": "random_regular",
        "nodes": int(nodes),
        "degree": int(degree),
    }


def default_step4_graphs():
    """Liefert alle sechs Graphsets aus den Schritt-4-Serverläufen."""
    return [
        *(dict(dataset) for dataset in ERDOS_RENYI_DATASETS.values()),
        *(dict(dataset) for dataset in REAL_WORLD_DATASETS.values()),
    ]


def normalize_graph_datasets(datasets):
    """Ergänzt stabile Failure-Defaults für GUI-Datasets."""
    updated = []
    for dataset in datasets:
        dataset = dict(dataset)
        dataset["fail_factors"] = list(dataset.get("fail_factors", REAL_WORLD_FAIL_FACTORS))
        dataset["failure_starts"] = list(dataset.get("failure_starts", CLUSTERED_FAILURE_STARTS))
        dataset["failure_drop"] = float(dataset.get("failure_drop", CLUSTERED_FAILURE_DROP))
        updated.append(dataset)
    return updated


def build_gui_random_dataset(
    nodes,
    p,
    fail_factors,
    failure_starts=None,
    failure_drop=None,
):
    """Baut ein Random-Graph-Dataset aus den GUI-Eingaben."""
    name = f"random_er_n{int(nodes)}_p{_safe_decimal_token(float(p))}"
    return build_custom_erdos_renyi_dataset(
        name,
        nodes,
        p,
        fail_factors=fail_factors,
        failure_starts=failure_starts or CLUSTERED_FAILURE_STARTS,
        failure_drop=CLUSTERED_FAILURE_DROP if failure_drop is None else failure_drop,
    )


def build_gui_real_world_dataset(
    dataset_key,
    fail_factors=None,
    failure_starts=None,
    failure_drop=None,
):
    """Baut ein Real-World-Dataset aus den GUI-Eingaben."""
    dataset = dict(REAL_WORLD_DATASETS[dataset_key])
    dataset["fail_factors"] = list(fail_factors or REAL_WORLD_FAIL_FACTORS)
    dataset["failure_starts"] = list(failure_starts or CLUSTERED_FAILURE_STARTS)
    dataset["failure_drop"] = float(
        CLUSTERED_FAILURE_DROP if failure_drop is None else failure_drop
    )
    return dataset


def build_plot_groups(datasets):
    """Trennt Plotgruppen wie die CLI mit maximal drei Graphen pro Bild."""
    return pipeline.default_plot_groups(datasets)


def build_gui_config(
    run_name,
    output_root,
    runs,
    algorithms,
    failures,
    graph_datasets,
    metrics=None,
    seed=DEFAULT_SEED,
):
    """Baut die Pipeline-Konfiguration aus GUI-Eingaben."""
    datasets = normalize_graph_datasets(graph_datasets)
    if not datasets:
        raise ValueError("At least one dataset must be selected")
    if not algorithms:
        raise ValueError("At least one algorithm must be selected")
    if not failures:
        raise ValueError("At least one failure type must be selected")

    return {
        "run_name": run_name,
        "title": f"Step 5 GUI: {run_name}",
        "output_root": output_root,
        "runs": int(runs),
        "seed": int(seed),
        "resume": True,
        "algorithms": list(algorithms),
        "failures": list(failures),
        "metrics": list(metrics or ["resilience", "avgHops", "avgStretch"]),
        "datasets": datasets,
        "plot_groups": build_plot_groups(datasets),
    }


def write_gui_config(config):
    """Schreibt die von der GUI erzeugte JSON in den Ausgabeordner."""
    output_root = pipeline.resolve_repo_path(config["output_root"])
    output_root.mkdir(parents=True, exist_ok=True)
    config_path = output_root / "gui_config.json"
    with config_path.open("w", encoding="utf-8") as config_file:
        json.dump(config, config_file, indent=2)
        config_file.write("\n")
    return config_path


def mode_to_pipeline_flags(mode):
    """Übersetzt den GUI-Ausführungsmodus in Pipeline-Flags."""
    return {
        "Experiment + Plots": {},
        "Nur Experimente": {"only_experiments": True},
        "Nur Plots": {"only_plots": True},
        "Dry Run": {"dry_run": True},
        "Preflight": {"preflight": True},
    }[mode]


def build_server_command(config_path, mode):
    """Erzeugt den CLI-Befehl für einen Serverlauf derselben Config."""
    config_path = Path(config_path)
    try:
        config_arg = (
            config_path.relative_to(PIPELINE_ROOT).as_posix()
            if config_path.is_absolute()
            else config_path.as_posix()
        )
    except ValueError:
        config_arg = str(config_path)
    flags = mode_to_pipeline_flags(mode)
    extra = []
    if flags.get("only_experiments"):
        extra.append("--only-experiments")
    if flags.get("only_plots"):
        extra.append("--only-plots")
    if flags.get("dry_run"):
        extra.append("--dry-run")
    if flags.get("preflight"):
        extra.append("--preflight")
    suffix = " " + " ".join(extra) if extra else ""
    return f"python pipeline.py --config {config_arg}{suffix}"


def write_server_command(config_path, mode):
    """Speichert einen Server-Hilfsbefehl neben der GUI-Config."""
    command = build_server_command(config_path, mode)
    script_path = Path(config_path).parent / "run_on_server.sh"
    with script_path.open("w", encoding="utf-8") as script:
        script.write("#!/usr/bin/env bash\n")
        script.write("set -euo pipefail\n")
        script.write('STEP5_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"\n')
        script.write('cd "$STEP5_ROOT"\n')
        script.write(command + "\n")
    return script_path, command


def dry_run_plan_rows(result):
    """Formatiert geplante Jobs für die Dry-Run-Tabelle der GUI."""
    return [
        {
            "Dataset": item["dataset"]["name"],
            "Failure": item["failure"],
            "Runs": result["config"]["runs"],
            "Graph": item["graph_type"],
            "n": item["nodes"],
            "p": item["graph_param"],
            "Ausgabeordner": str(item["output_dir"]),
        }
        for item in result["plan"]
    ]


def _render_result(st, result):
    """Zeigt Pipeline-Ergebnisse und erzeugte PNG-Plots in Streamlit an."""
    if result.get("dry_run"):
        st.success("Dry Run erfolgreich")
        st.write(f"Geplante Jobs: {len(result['plan'])}")
        st.dataframe(dry_run_plan_rows(result), use_container_width=True)
        return
    if result.get("preflight"):
        st.success("Preflight erfolgreich")
        st.write(result["preflight"])
        return
    st.success("Pipeline abgeschlossen")
    if result.get("manifest"):
        st.write(f"Manifest: {result['manifest']}")
    if result.get("summary"):
        st.write(f"Summary: {result['summary']}")
    if result.get("generated_csvs"):
        st.write(f"CSV-Dateien: {len(result['generated_csvs'])}")
    if result.get("plots"):
        png_plots = [Path(path) for path in result["plots"] if str(path).endswith(".png")]
        st.write(f"Plots: {len(result['plots'])}")
        show_plots = st.checkbox("PNG-Plots anzeigen", value=True, key="show_png_plots")
        if show_plots:
            for path in png_plots:
                st.image(str(path), caption=str(path.relative_to(path.parents[2])))


def _init_session_state(st):
    """Initialisiert alle Session-State-Werte der GUI."""
    st.session_state.setdefault("graph_datasets", [])
    st.session_state.setdefault("add_graph_open", False)
    st.session_state.setdefault("last_result", None)
    st.session_state.setdefault("last_config_path", None)
    st.session_state.setdefault("last_server_command", None)
    st.session_state.setdefault("last_server_script", None)


def _append_graph(st, dataset):
    """Fügt eine Graph-Konfiguration hinzu und vermeidet doppelte Namen."""
    existing = [item["name"] for item in st.session_state.graph_datasets]
    dataset = dict(dataset)
    base_name = dataset["name"]
    if base_name in existing:
        index = 2
        while f"{base_name}_{index}" in existing:
            index += 1
        dataset["name"] = f"{base_name}_{index}"
        dataset["display_name"] = f"{dataset.get('display_name', base_name)} ({index})"
    st.session_state.graph_datasets.append(dataset)


def _render_rate_preview(st, values):
    """Zeigt eine kompakte Vorschau der erzeugten Failure-Rate-Werte."""
    st.caption(f"{len(values)} Werte: {format_number_list(values)}")


def _render_failure_range_editor(
    st,
    key_prefix,
    heading,
    caption,
    start_default,
    stop_default,
    step_default,
    max_value=None,
):
    """Rendert Eingabefelder für einen Failure-Rate-Bereich."""
    st.markdown(f"**{heading}**")
    st.caption(caption)
    range_cols = st.columns(3)
    start_kwargs = {
        "label": "Failure Rate von",
        "min_value": 0.0,
        "value": float(start_default),
        "step": 0.1,
        "key": f"{key_prefix}_rate_start",
    }
    stop_kwargs = {
        "label": "Failure Rate bis",
        "min_value": 0.0,
        "value": float(stop_default),
        "step": 0.1,
        "key": f"{key_prefix}_rate_stop",
    }
    step_kwargs = {
        "label": "Schrittgröße",
        "min_value": 0.01,
        "value": float(step_default),
        "step": 0.1,
        "key": f"{key_prefix}_rate_step",
    }
    if max_value is not None:
        start_kwargs["max_value"] = float(max_value)
        stop_kwargs["max_value"] = float(max_value)
        step_kwargs["max_value"] = float(max_value)

    rate_start = range_cols[0].number_input(**start_kwargs)
    rate_stop = range_cols[1].number_input(**stop_kwargs)
    rate_step = range_cols[2].number_input(**step_kwargs)
    try:
        rates = build_failure_rate_range(rate_start, rate_stop, rate_step)
        _render_rate_preview(st, rates)
        return rates
    except ValueError as exc:
        st.warning(str(exc))
        return []


def _render_failure_drop_editor(st, key_prefix):
    """Rendert das Eingabefeld für `failureDrop`."""
    return st.number_input(
        "Failure drop",
        min_value=0.01,
        max_value=1.0,
        value=CLUSTERED_FAILURE_DROP,
        step=0.05,
        key=f"{key_prefix}_failure_drop",
        help="failureDrop senkt die Cluster-Wahrscheinlichkeit pro Abstandsschritt.",
    )


def _render_graph_builder(st):
    """Rendert die Graph-Auswahl und die Liste gewählter Graph-Konfigurationen."""
    st.subheader("Graphen")

    action_cols = st.columns([1, 1, 1, 3])
    if action_cols[0].button("+ Hinzufügen", type="secondary"):
        st.session_state.add_graph_open = True
    if action_cols[1].button("Paper-Graphsets"):
        st.session_state.graph_datasets = default_step4_graphs()
    if action_cols[2].button("Graphauswahl leeren"):
        st.session_state.graph_datasets = []
        st.session_state.add_graph_open = False

    builder_col, selected_col = st.columns([1, 1])
    with builder_col:
        if not st.session_state.add_graph_open:
            st.info("Mit + Hinzufügen eine neue Graph-Konfiguration erstellen.")
        else:
            graph_kind = st.radio(
                "Graph-Typ",
                options=list(GRAPH_TYPE_LABELS),
                format_func=lambda key: GRAPH_TYPE_LABELS[key],
                horizontal=True,
            )

            if graph_kind == "random_erdos":
                nodes = st.number_input("n", min_value=2, value=50, step=1)
                p = st.number_input("p", min_value=0.0, max_value=1.0, value=0.15, step=0.01)
                random_rates = _render_failure_range_editor(
                    st,
                    "random_graph_random_failure",
                    "Random-Failure",
                    "Failure Rate repräsentiert bei Random-Ausfällen den failFactor.",
                    0.8,
                    16.8,
                    0.8,
                )
                clustered_rates = _render_failure_range_editor(
                    st,
                    "random_graph_clustered_failure",
                    "Clustered-Failure",
                    "Failure Rate repräsentiert bei Clustered-Ausfällen failureStart.",
                    0.3,
                    0.9,
                    0.1,
                    max_value=1.0,
                )
                failure_drop = _render_failure_drop_editor(st, "random_graph_clustered_failure")

                save_cols = st.columns([1, 1, 3])
                if save_cols[0].button("Graph speichern", key="save_random_erdos"):
                    try:
                        if not random_rates or not clustered_rates:
                            raise ValueError("Failure Rate range is empty")
                        dataset = build_gui_random_dataset(
                            nodes,
                            p,
                            random_rates,
                            clustered_rates,
                            failure_drop,
                        )
                        _append_graph(st, dataset)
                        st.session_state.add_graph_open = False
                        st.rerun()
                    except ValueError as exc:
                        st.error(str(exc))
                if save_cols[1].button("Abbrechen", key="cancel_random_erdos"):
                    st.session_state.add_graph_open = False
                    st.rerun()
            else:
                key = st.selectbox(
                    "Real-World Graph",
                    options=list(REAL_WORLD_DATASETS),
                    format_func=lambda item: REAL_WORLD_DATASETS[item]["display_name"],
                )
                random_rates = _render_failure_range_editor(
                    st,
                    "real_graph_random_failure",
                    "Random-Failure",
                    "Failure Rate repräsentiert bei Random-Ausfällen den failFactor.",
                    1.0,
                    10.0,
                    1.0,
                )
                clustered_rates = _render_failure_range_editor(
                    st,
                    "real_graph_clustered_failure",
                    "Clustered-Failure",
                    "Failure Rate repräsentiert bei Clustered-Ausfällen failureStart.",
                    0.3,
                    0.9,
                    0.1,
                    max_value=1.0,
                )
                failure_drop = _render_failure_drop_editor(st, "real_graph_clustered_failure")

                save_cols = st.columns([1, 1, 3])
                if save_cols[0].button("Graph speichern", key="save_real_world"):
                    try:
                        if not random_rates or not clustered_rates:
                            raise ValueError("Failure Rate range is empty")
                        dataset = build_gui_real_world_dataset(
                            key,
                            random_rates,
                            clustered_rates,
                            failure_drop,
                        )
                        _append_graph(st, dataset)
                        st.session_state.add_graph_open = False
                        st.rerun()
                    except ValueError as exc:
                        st.error(str(exc))
                if save_cols[1].button("Abbrechen", key="cancel_real_world"):
                    st.session_state.add_graph_open = False
                    st.rerun()

    with selected_col:
        st.write("Ausgewählte Graph-Konfigurationen")
        if not st.session_state.graph_datasets:
            st.info("Noch keine Graph-Konfiguration ausgewählt.")
        for index, dataset in enumerate(list(st.session_state.graph_datasets)):
            cols = st.columns([4, 1])
            detail = (
                f"{index + 1}. {dataset.get('display_name', dataset['name'])} | "
                f"failFactor: {format_number_list(dataset.get('fail_factors', []))} | "
                f"failureStart: {format_number_list(dataset.get('failure_starts', []))} | "
                f"failureDrop: {dataset.get('failure_drop', CLUSTERED_FAILURE_DROP)}"
            )
            cols[0].write(detail)
            if cols[1].button("Entfernen", key=f"remove_graph_{index}"):
                del st.session_state.graph_datasets[index]
                st.rerun()


def main():
    """Startet die Streamlit-GUI für die Schritt-5-Pipeline."""
    try:
        import streamlit as st
    except ModuleNotFoundError as exc:
        raise SystemExit(
            "Streamlit is not installed. Install it with "
            "`pip install streamlit` or run the CLI pipeline instead."
        ) from exc

    st.set_page_config(page_title="Schritt 5 Pipeline", layout="wide")
    _init_session_state(st)
    st.title("Schritt 5 Pipeline")

    left, right = st.columns([1, 1])
    with left:
        run_name = st.text_input("Laufname", value="gui_pilot")
        default_output = f"Output/{run_name}"
        output_root = st.text_input("Ausgabeordner", value=default_output)
        runs = st.number_input("Läufe", min_value=1, value=5, step=1)
        st.caption(f"Seed ist fest auf {DEFAULT_SEED} gesetzt.")
        mode = st.selectbox(
            "Ausführung",
            [
                "Experiment + Plots",
                "Nur Experimente",
                "Nur Plots",
                "Dry Run",
                "Preflight",
            ],
        )
        target = st.selectbox(
            "Ausführungsort",
            ["Lokal ausführen", "Server vorbereiten"],
        )

    with right:
        algorithms = st.multiselect(
            "Algorithmen",
            options=list(pipeline.ALGORITHMS),
            default=list(pipeline.ALGORITHMS),
            format_func=lambda key: ALGORITHM_LABELS[key],
        )
        failures = st.multiselect(
            "Fehlertypen",
            options=list(pipeline.FAILURE_COMBINATIONS),
            default=list(pipeline.FAILURE_COMBINATIONS),
            format_func=lambda key: FAILURE_LABELS[key],
        )
        metrics = st.multiselect(
            "Metriken",
            options=["resilience", "avgHops", "avgStretch"],
            default=["resilience", "avgHops", "avgStretch"],
        )

    _render_graph_builder(st)

    def current_config():
        """Baut die aktuelle GUI-Konfiguration ohne sie auszuführen."""
        return build_gui_config(
            run_name,
            output_root,
            runs,
            algorithms,
            failures,
            st.session_state.graph_datasets,
            metrics,
        )

    with st.expander("Konfiguration anzeigen"):
        try:
            st.json(current_config())
        except ValueError as exc:
            st.warning(str(exc))

    if st.button("Experiment starten", type="primary"):
        try:
            config = current_config()
            config_path = write_gui_config(config)
            st.session_state.last_config_path = str(config_path)
            st.session_state.last_server_command = None
            st.session_state.last_server_script = None
            st.info(f"Konfiguration: {config_path}")
            if target == "Server vorbereiten":
                script_path, command = write_server_command(config_path, mode)
                st.session_state.last_server_script = str(script_path)
                st.session_state.last_server_command = command
                st.session_state.last_result = None
            else:
                with st.spinner("Pipeline läuft..."):
                    st.session_state.last_result = pipeline.run_pipeline(
                        config_path,
                        **mode_to_pipeline_flags(mode),
                    )
        except Exception as exc:
            st.error(str(exc))

    if st.session_state.last_server_command:
        st.success("Serverlauf vorbereitet")
        st.write(f"Skript: {st.session_state.last_server_script}")
        st.code(st.session_state.last_server_command, language="bash")
        st.caption(
            "Die GUI startet keinen entfernten Serverprozess. Führe den Befehl "
            "auf dem Server aus oder starte Streamlit direkt auf dem Server."
        )

    if st.session_state.last_result:
        _render_result(st, st.session_state.last_result)


if __name__ == "__main__":
    main()
