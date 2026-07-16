"""Gemeinsame Auswertung für die finalen Schritt-4-Notebooks."""

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


ALGORITHM_LABELS = {
    "edp_paths": "EDP Paths",
    "edp_one_tree": "EDP One Tree",
    "edp_multiple_trees": "EDP Multiple Trees",
    "ndp_paths": "NDP Paths",
    "ndp_one_tree": "NDP One Tree",
    "ndp_multiple_trees": "NDP Multiple Trees",
}

ALGORITHM_COLORS = {
    "edp_paths": "#1f77b4",
    "edp_one_tree": "#ff7f0e",
    "edp_multiple_trees": "#2ca02c",
    "ndp_paths": "#9467bd",
    "ndp_one_tree": "#d62728",
    "ndp_multiple_trees": "#8c564b",
}


def load_result_directories(directories):
    """Liest alle algorithms_*.csv und fügt einen Dataset-Schlüssel hinzu."""
    frames = []
    files_by_dataset = {}
    for dataset, directory in directories.items():
        directory = Path(directory)
        files = sorted(directory.glob("algorithms_*.csv"))
        if not files:
            raise FileNotFoundError(f"No result CSVs found for {dataset}: {directory}")
        files_by_dataset[dataset] = files
        for path in files:
            frame = pd.read_csv(path)
            frame["dataset"] = dataset
            frame["sourceFile"] = path.name
            frames.append(frame)
    return pd.concat(frames, ignore_index=True), files_by_dataset


def aggregate_results(raw):
    """Berechnet Resilience sowie Hops/Stretch erfolgreicher Routings."""
    raw = raw.copy()
    for column in ["success", "hops", "stretch", "failFactor", "failureStart"]:
        raw[column] = pd.to_numeric(raw[column], errors="coerce")
    raw["hopsSuccessful"] = raw["hops"].where(raw["success"] == 1)
    raw["stretchSuccessful"] = raw["stretch"].where(raw["success"] == 1)
    raw["failureParameter"] = raw["failFactor"].fillna(raw["failureStart"])
    summary = (
        raw.groupby(
            [
                "dataset",
                "failureType",
                "failureModel",
                "failureParameter",
                "algorithm",
            ],
            as_index=False,
        )
        .agg(
            resilience=("success", "mean"),
            avgHops=("hopsSuccessful", "mean"),
            avgStretch=("stretchSuccessful", "mean"),
            samples=("success", "size"),
            successes=("success", "sum"),
        )
    )
    return raw, summary


def completeness_table(summary):
    """Fasst je Konfiguration zusammen, ob alle Algorithmen vollständig sind."""
    return (
        summary.groupby(
            ["dataset", "failureType", "failureModel", "failureParameter"]
        )
        .agg(algorithms=("algorithm", "nunique"), samplesPerAlgorithm=("samples", "min"))
    )


def validate_summary(summary, expected_runs, algorithms):
    """Bricht ab, wenn eine Serverkonfiguration unvollständig ist."""
    expected_algorithms = set(algorithms)
    grouped = summary.groupby(
        ["dataset", "failureType", "failureModel", "failureParameter"]
    )
    for key, rows in grouped:
        if set(rows["algorithm"]) != expected_algorithms:
            raise ValueError(f"Incomplete algorithms for {key}")
        if not rows["samples"].eq(expected_runs).all():
            raise ValueError(f"Expected {expected_runs} samples for {key}")
    if not summary["resilience"].between(0, 1).all():
        raise ValueError("Resilience outside [0, 1]")


def plot_all_comparisons(
    summary,
    datasets,
    display_names,
    algorithms,
    output_dir,
    title_prefix,
    runs,
    metrics=None,
    failure_combinations=None,
    show=True,
):
    """Erzeugt paper-ähnliche Vergleiche jeweils als PNG und SVG."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    default_metrics = [
        ("resilience", "Resilience", (0, 1.05)),
        ("avgHops", "Average Hops (successful routes)", None),
        ("avgStretch", "Average Stretch (successful routes)", None),
    ]
    metrics = default_metrics if metrics is None else metrics
    outputs = []
    combinations = failure_combinations or [
        ("random", "link"),
        ("random", "node"),
        ("clustered", "link"),
        ("clustered", "node"),
    ]
    for failure_model, failure_type in combinations:
        for metric, ylabel, ylim in metrics:
            fig, axes = plt.subplots(1, len(datasets), figsize=(16, 4.8))
            if len(datasets) == 1:
                axes = [axes]
            for ax, dataset in zip(axes, datasets):
                subset = summary[
                    (summary["dataset"] == dataset)
                    & (summary["failureModel"] == failure_model)
                    & (summary["failureType"] == failure_type)
                ]
                for algorithm in algorithms:
                    values = subset[subset["algorithm"] == algorithm].sort_values(
                        "failureParameter"
                    )
                    ax.plot(
                        values["failureParameter"],
                        values[metric],
                        marker="o",
                        linewidth=2,
                        color=ALGORITHM_COLORS[algorithm],
                        label=ALGORITHM_LABELS[algorithm],
                        linestyle="--" if algorithm.startswith("ndp_") else "-",
                    )
                ax.set_title(display_names[dataset])
                ax.set_xlabel("Failure Rate")
                ax.grid(True, alpha=0.3)
                if ylim is not None:
                    ax.set_ylim(*ylim)
            axes[0].set_ylabel(ylabel)
            fig.suptitle(
                f"{title_prefix}: {failure_model.title()} "
                f"{failure_type.title()} Failures (runs={runs})",
                fontsize=15,
            )
            handles, labels = axes[0].get_legend_handles_labels()
            fig.legend(handles, labels, loc="lower center", ncol=3, fontsize=9)
            fig.tight_layout(rect=(0, 0.13, 1, 0.93))
            stem = f"{failure_model}_{failure_type}_{metric}"
            png_path = output_dir / f"{stem}.png"
            svg_path = output_dir / f"{stem}.svg"
            fig.savefig(png_path, dpi=180, bbox_inches="tight")
            fig.savefig(svg_path, bbox_inches="tight")
            if show:
                plt.show()
            else:
                plt.close(fig)
            outputs.extend([png_path, svg_path])
    return outputs
