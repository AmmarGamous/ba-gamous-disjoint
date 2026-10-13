"""Erzeugt kleine Bildbeispiele für die Ausarbeitung.

Das Modul ist absichtlich von der Experiment-Pipeline getrennt. Es nutzt die
gleichen Kernfunktionen für EDPs, NDPs und Failure-Auswahl, erzeugt aber kleine,
kontrollierte Beispielgraphen für erklärende Abbildungen im Text.
"""

import argparse
from pathlib import Path
import random
import sys

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import FancyArrowPatch, Rectangle
import networkx as nx


ILLUSTRATION_ROOT = Path(__file__).resolve().parent
STEP5_ROOT = ILLUSTRATION_ROOT.parent
STEP5_SRC = STEP5_ROOT / "src"
STEP5_EVALUATION = STEP5_ROOT / "evaluation"
for import_path in (STEP5_SRC, STEP5_EVALUATION):
    if str(import_path) not in sys.path:
        sys.path.insert(0, str(import_path))

import experiment  # noqa: E402
import result_analysis  # noqa: E402
from failures import node_failures_to_edges, select_failures  # noqa: E402
from routing_algorithms import (  # noqa: E402
    build_structures,
    get_disjoint_paths,
    route_algorithm,
)


DEFAULT_OUTPUT_DIR = STEP5_ROOT / "Output" / "illustrations"
SOURCE = "s"
DESTINATION = "d"
PATH_COLORS = list(dict.fromkeys(result_analysis.ALGORITHM_COLORS.values()))
BRANCH_COLOR = "#d62728"
THESIS_PATH_COLORS = [
    color for color in PATH_COLORS if color.lower() != BRANCH_COLOR
]
THESIS_LAYOUT_SEED = 195
THESIS_COMPARISON_CONFIG = {
    "graph_type": "erdos_renyi",
    "nodes": 10,
    "p": 0.35,
    "degree": 4,
    "seed": 430,
}
ALGORITHM_CHOICES = [
    "none",
    "edp_paths",
    "edp_one_tree",
    "edp_multiple_trees",
    "ndp_paths",
    "ndp_one_tree",
    "ndp_multiple_trees",
]


def set_graph_title(graph, title):
    """Speichert den Titel einer erzeugten Illustrationsszene."""
    graph.graph["title"] = title
    return graph


def create_disjointness_strength_graph():
    """Erzeugt den Vergleichsgraphen reproduzierbar über `experiment.py`."""
    graph_type = "erdos_renyi"
    nodes = 8
    p = 0.3
    seed = 21
    graph = experiment.create_graph(graph_type, nodes, p, seed)
    source, destination = experiment.choose_endpoints(graph, random.Random(seed))
    edps = get_disjoint_paths(graph, source, destination, "edp")
    shared_inner_nodes = set(edps[0][1:-1])
    for path in edps[1:]:
        shared_inner_nodes.intersection_update(path[1:-1])
    if not shared_inner_nodes:
        raise RuntimeError("Der Vergleichsgraph besitzt keinen gemeinsamen EDP-Knoten.")
    shared_node = sorted(shared_inner_nodes, key=str)[0]
    graph = nx.relabel_nodes(
        graph,
        {
            source: SOURCE,
            destination: DESTINATION,
            shared_node: "x",
        },
        copy=True,
    )
    graph = set_graph_title(
        graph,
        "Stärke der Disjunktheit: EDP im Vergleich zu NDP",
    )
    graph.graph.update(
        {
            "graph_type": graph_type,
            "nodes": nodes,
            "p": p,
            "seed": seed,
            "shared_node": "x",
        }
    )
    return graph


def analyze_disjointness_routing(graph):
    """Prüft EDP/NDP-Routing vor und nach Ausfall des gemeinsamen Knotens."""
    edps = get_disjoint_paths(graph, SOURCE, DESTINATION, "edp")
    ndps = get_disjoint_paths(graph, SOURCE, DESTINATION, "ndp")
    failed_node = graph.graph["shared_node"]
    failed_edges = node_failures_to_edges(graph, [failed_node])
    return {
        "edps": edps,
        "ndps": ndps,
        "failed_node": failed_node,
        "failed_edges": failed_edges,
        "edp_before": route_algorithm(
            graph, SOURCE, DESTINATION, [], "edp_paths", paths=edps
        ),
        "edp_after": route_algorithm(
            graph, SOURCE, DESTINATION, failed_edges, "edp_paths", paths=edps
        ),
        "ndp_before": route_algorithm(
            graph, SOURCE, DESTINATION, [], "ndp_paths", paths=ndps
        ),
        "ndp_after": route_algorithm(
            graph, SOURCE, DESTINATION, failed_edges, "ndp_paths", paths=ndps
        ),
    }


def failure_comparison_scene():
    """Vergleicht einen gezielten Kanten- und Knotenausfall im Kerngraphen."""
    graph = create_disjointness_strength_graph()
    failed_node = graph.graph["shared_node"]
    node_failed_edges = node_failures_to_edges(graph, [failed_node])
    link_failed_edge = next(
        edge for edge in node_failed_edges if SOURCE in edge
    )
    return graph, {
        "failed_node": failed_node,
        "link_failed_edges": [link_failed_edge],
        "node_failed_edges": node_failed_edges,
    }


def first_paths(paths, count):
    """Wählt optional höchstens `count` Pfade in stabiler Reihenfolge aus."""
    return list(paths if count is None or count <= 0 else paths[:count])


def create_configured_graph(graph_type, nodes, p, degree, seed):
    """Erzeugt einen parametrisierbaren Graphen wie vor einem Routinglauf."""
    if graph_type == "erdos_renyi":
        graph = experiment.create_graph(graph_type, nodes, p, seed)
        title = f"Erdos-Renyi n={nodes}, p={p}, seed={seed}"
    elif graph_type == "random_regular":
        graph = experiment.create_graph(graph_type, nodes, degree, seed)
        title = f"Random-Regular n={nodes}, degree={degree}, seed={seed}"
    else:
        raise ValueError(f"Unbekannter Graph-Typ: {graph_type}")
    return set_graph_title(graph, title)


def choose_source_destination(graph, seed):
    """Wählt ein verbundenes, möglichst nicht direkt benachbartes s-d-Paar."""
    try:
        return experiment.choose_endpoints(graph, random.Random(seed))
    except nx.NetworkXNoPath:
        ordered = sorted(graph.nodes, key=str)
        if len(ordered) < 2:
            raise ValueError("Der Graph braucht mindestens zwei Knoten.")
        return ordered[0], ordered[-1]


def relabel_endpoints(graph, source, destination):
    """Benennt das gewählte s-d-Paar für die Abbildung nach s und d um."""
    mapping = {}
    if source != SOURCE:
        mapping[source] = SOURCE
    if destination != DESTINATION:
        mapping[destination] = DESTINATION
    for node in list(graph.nodes):
        if node not in mapping and node in (SOURCE, DESTINATION):
            mapping[node] = f"v{node}"
    relabeled = nx.relabel_nodes(graph, mapping, copy=True)
    return set_graph_title(
        relabeled,
        graph.graph.get("title", "Konfigurierter Graph"),
    )


def safe_disjoint_paths(graph, path_type, max_paths):
    """Berechnet Pfade robust; bei fehlender Verbindung wird leer zurückgegeben."""
    try:
        return first_paths(
            get_disjoint_paths(graph, SOURCE, DESTINATION, path_type),
            max_paths,
        )
    except nx.NetworkXException:
        return []


def disjoint_path_count(graph, path_type):
    """Zählt EDPs oder NDPs robust für die Pipeline-nahe Failure-Berechnung."""
    try:
        return len(get_disjoint_paths(graph, SOURCE, DESTINATION, path_type))
    except nx.NetworkXException:
        return 0


def random_failure_count(graph, failure_type, fail_factor):
    """Berechnet die Random-Ausfallanzahl wie in der Experiment-Pipeline."""
    path_type = "edp" if failure_type == "link" else "ndp"
    connectivity = disjoint_path_count(graph, path_type)
    return round(max(connectivity - 1, 0) * fail_factor)


def filename_token(value):
    """Formatiert Parameter kurz und dateinamensfreundlich."""
    return str(value).replace(".", "p")


def configured_scene(
    graph_type="erdos_renyi",
    nodes=12,
    p=0.28,
    degree=3,
    path_type="both",
    algorithm="none",
    max_paths=0,
    failure_type="node",
    failure_model="random",
    fail_factor=0.8,
    failure_start=0.8,
    failure_drop=0.3,
    seed=123,
):
    """Erzeugt eine frei konfigurierbare Szene mit Pfaden und Ausfällen."""
    graph = create_configured_graph(graph_type, nodes, p, degree, seed)
    source, destination = choose_source_destination(graph, seed)
    graph = relabel_endpoints(graph, source, destination)

    paths_by_type = {}
    structures = []
    if algorithm != "none":
        algorithm_path_type, structure_type = algorithm.split("_", 1)
        paths = safe_disjoint_paths(graph, algorithm_path_type, max_paths)
        paths_by_type[algorithm_path_type] = paths
        structures = build_structures(
            graph,
            SOURCE,
            DESTINATION,
            paths,
            structure_type,
            retain_growth_stage=True,
        )

    path_types = (
        []
        if algorithm != "none" or path_type == "none"
        else ["edp", "ndp"] if path_type == "both" else [path_type]
    )
    for current_path_type in path_types:
        paths = safe_disjoint_paths(graph, current_path_type, max_paths)
        paths_by_type[current_path_type] = paths

    nr_failures = (
        random_failure_count(graph, failure_type, fail_factor)
        if failure_model == "random"
        else 0
    )
    if failure_model == "none":
        failed_edges, failed_nodes = [], []
    else:
        failed_edges, failed_nodes = select_failures(
            graph,
            SOURCE,
            DESTINATION,
            failure_type,
            failure_model,
            nr_failures,
            failure_start,
            failure_drop,
            random.Random(seed),
        )
    routing_result = None
    if algorithm != "none":
        routing_result = route_algorithm(
            graph,
            SOURCE,
            DESTINATION,
            failed_edges,
            algorithm,
            paths=paths_by_type[algorithm_path_type],
        )

    title_parts = [graph.graph["title"]]
    if algorithm != "none":
        title_parts.append(result_analysis.ALGORITHM_LABELS.get(algorithm, algorithm))
    elif path_type != "none":
        title_parts.append("EDP/NDP" if path_type == "both" else path_type.upper())
    if failure_model == "none":
        title_parts.append("ohne Ausfälle")
    elif failure_model == "random":
        title_parts.append(
            f"Random {failure_type.title()} Failure "
            f"(failFactor={fail_factor}, nr={nr_failures})"
        )
    else:
        title_parts.append(
            f"Clustered {failure_type.title()} Failure "
            f"(start={failure_start}, drop={failure_drop})"
        )
    title = " | ".join(title_parts)
    return "configured_scene", graph, {
        "paths": paths_by_type,
        "structures": structures,
        "routing_result": routing_result,
        "algorithm": algorithm,
        "algorithm_path_type": (
            algorithm_path_type if algorithm != "none" else None
        ),
        "structure_type": structure_type if algorithm != "none" else None,
        "failed_edges": failed_edges,
        "failed_nodes": failed_nodes,
        "nr_failures": nr_failures,
        "fail_factor": fail_factor,
        "title": title,
    }


def thesis_comparison_scene():
    """Berechnet den gemeinsamen Graphen für die drei Vergleichsabbildungen."""
    config = THESIS_COMPARISON_CONFIG
    graph = create_configured_graph(
        config["graph_type"],
        config["nodes"],
        config["p"],
        config["degree"],
        config["seed"],
    )
    source, destination = choose_source_destination(graph, config["seed"])
    graph = relabel_endpoints(graph, source, destination)
    paths = {
        path_type: safe_disjoint_paths(graph, path_type, max_paths=0)
        for path_type in ("edp", "ndp")
    }
    structures = {
        f"{path_type}_{structure_type}": build_structures(
            graph,
            SOURCE,
            DESTINATION,
            paths[path_type],
            structure_type,
            retain_growth_stage=True,
        )
        for path_type in ("edp", "ndp")
        for structure_type in ("one_tree", "multiple_trees")
    }
    return graph, {
        "config": dict(config),
        "paths": paths,
        "structures": structures,
    }


def shared_inner_nodes(paths):
    """Liefert innere Knoten, die in mehr als einem Pfad vorkommen."""
    occurrences = {}
    for path in paths:
        for node in set(path[1:-1]):
            occurrences[node] = occurrences.get(node, 0) + 1
    return {
        node for node, count in occurrences.items()
        if count > 1
    }


def _path_edges(path):
    """Liefert die gerichtungsunabhängigen Kanten eines vollständigen Pfads."""
    return [tuple(edge) for edge in zip(path, path[1:])]


def _structure_edges(structure):
    """Liefert Baumkanten einschließlich der möglichen Ausgänge zu d."""
    edges = list(structure.graph.edges)
    edges.extend((exit_node, DESTINATION) for exit_node in structure.exits)
    return edges


def draw_pipeline_overview(output_path):
    """Zeigt den Pipeline-Ablauf mit kurzen Beschriftungen für eine Folie."""
    stages = (
        ("Konfiguration", "CLI oder GUI", "Graphen und Parameter", "#2b6c99"),
        ("Experimente", "Routingversuche", "Rohdaten als CSV", "#287a65"),
        ("Auswertung", "Kennzahlen", "Zusammenfassung", "#906525"),
        ("Plots", "Vergleichsdiagramme", "PNG und SVG", "#6a5c86"),
    )
    fig, ax = plt.subplots(figsize=(14.4, 3.2))
    try:
        fig.subplots_adjust(left=0, right=1, bottom=0, top=1)
        ax.set_xlim(0, 14.4)
        ax.set_ylim(0, 3.2)
        ax.axis("off")
        width = 3.1
        spacing = 3.6
        for index, (title, first_line, second_line, color) in enumerate(stages):
            left = 0.25 + index * spacing
            center = left + width / 2
            ax.add_patch(Rectangle(
                (left, 1.65), width, 0.95,
                facecolor="#f8fafb", edgecolor=color, linewidth=1.8,
            ))
            ax.text(
                center, 2.125, title, ha="center", va="center",
                fontsize=22, fontweight="bold", color="#25343c",
            )
            for y, label in ((1.12, first_line), (0.76, second_line)):
                ax.text(
                    center, y, label, ha="center", va="center",
                    fontsize=16, color="#45545d",
                )
            if index < len(stages) - 1:
                ax.add_patch(FancyArrowPatch(
                    (left + width + 0.07, 2.125),
                    (left + spacing - 0.07, 2.125),
                    arrowstyle="-|>", mutation_scale=18,
                    linewidth=1.8, color="#45545d",
                ))
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(output_path, dpi=220, bbox_inches="tight", facecolor="white")
    finally:
        plt.close(fig)


def draw_failure_comparison(graph, metadata, output_path):
    """Zeigt beide Ausfalltypen ohne Pfadmarkierung in identischem Layout."""
    positions = nx.spring_layout(graph, seed=21, iterations=200)
    positions = {node: (y, -x) for node, (x, y) in positions.items()}
    available_color = "#7a858c"
    failed_color = "#c52b32"
    panels = (
        (
            "Kantenausfall",
            "Eine Verbindung betroffen",
            metadata["link_failed_edges"],
            [],
        ),
        (
            "Knotenausfall",
            "Alle angrenzenden Verbindungen betroffen",
            metadata["node_failed_edges"],
            [metadata["failed_node"]],
        ),
    )
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.8))
    try:
        for ax, (title, subtitle, failed_edges, failed_nodes) in zip(axes, panels):
            failed_edge_set = {frozenset(edge) for edge in failed_edges}
            available_edges = [
                edge for edge in graph.edges
                if frozenset(edge) not in failed_edge_set
            ]
            nx.draw_networkx_edges(
                graph, positions, ax=ax, edgelist=available_edges,
                edge_color=available_color, width=2,
            )
            nx.draw_networkx_edges(
                graph, positions, ax=ax, edgelist=failed_edges,
                edge_color=failed_color, width=3, style="dashed",
            )
            nx.draw_networkx_nodes(
                graph, positions, ax=ax,
                node_color=[
                    "#f8d7da" if node in failed_nodes
                    else "#d9edf7" if node in (SOURCE, DESTINATION)
                    else "#ffffff"
                    for node in graph.nodes
                ],
                edgecolors=[
                    failed_color if node in failed_nodes else "#33434c"
                    for node in graph.nodes
                ],
                node_size=850, linewidths=2,
            )
            nx.draw_networkx_labels(
                graph, positions, ax=ax, font_size=14, font_weight="bold",
                font_color="#25343c",
            )
            ax.set_title(title, fontsize=20, fontweight="bold", pad=38)
            ax.text(
                0.5, 1.035, subtitle, transform=ax.transAxes,
                ha="center", va="bottom", fontsize=13, color="#33434c",
            )
            ax.margins(0.16)
            ax.set_aspect("equal")
            ax.axis("off")
        fig.legend(
            handles=[
                Line2D([], [], color=available_color, linewidth=2, label="Verfügbar"),
                Line2D(
                    [], [], color=failed_color, linewidth=3,
                    linestyle="--", label="Ausgefallen",
                ),
            ],
            loc="lower center", ncol=2, frameon=False, fontsize=13,
            bbox_to_anchor=(0.5, 0.015),
        )
        fig.subplots_adjust(left=0.02, right=0.98, bottom=0.13, top=0.81, wspace=0.16)
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(output_path, dpi=220, bbox_inches="tight", facecolor="white")
    finally:
        plt.close(fig)


def _draw_nodes_and_background(
    ax,
    graph,
    positions,
    highlighted_edges,
    failed_nodes,
):
    """Zeichnet neutrale Graphkanten und alle Knoten auf eine Achse."""
    highlighted = {frozenset(edge) for edge in highlighted_edges}
    normal_edges = [
        edge for edge in graph.edges if frozenset(edge) not in highlighted
    ]
    normal_nodes = [node for node in graph.nodes if node not in failed_nodes]
    source_target_nodes = [node for node in (SOURCE, DESTINATION) if node in graph]

    nx.draw_networkx_edges(
        graph,
        positions,
        ax=ax,
        edgelist=normal_edges,
        width=1.1,
        edge_color="#c2c2c2",
    )
    nx.draw_networkx_nodes(
        graph,
        positions,
        ax=ax,
        nodelist=normal_nodes,
        node_color="#f7f7f7",
        edgecolors="#333333",
        linewidths=1.3,
        node_size=700,
    )
    nx.draw_networkx_nodes(
        graph,
        positions,
        ax=ax,
        nodelist=source_target_nodes,
        node_color="#d9edf7",
        edgecolors="#1f77b4",
        linewidths=2.0,
        node_size=760,
    )
    if failed_nodes:
        nx.draw_networkx_nodes(
            graph,
            positions,
            ax=ax,
            nodelist=failed_nodes,
            node_color="#f8d7da",
            edgecolors="#c82333",
            linewidths=2.4,
            node_size=760,
        )
    nx.draw_networkx_labels(
        graph,
        positions,
        ax=ax,
        font_size=10,
        font_weight="bold",
    )
    ax.axis("off")


def one_tree_path_label(path, paths, index, path_type):
    """Bezeichnet den gewählten One-Tree-Grundpfad einschließlich Tie-Break."""
    label = f"{path_type.upper()} {index}"
    maximum_length = max((len(candidate) for candidate in paths), default=0)
    maximum_paths = [
        candidate for candidate in paths if len(candidate) == maximum_length
    ]
    chosen_path = max(
        paths,
        key=lambda candidate: (len(candidate), tuple(map(str, candidate))),
        default=None,
    )
    if path != chosen_path:
        return label
    if len(maximum_paths) == 1:
        return f"{label} (längster/Grundpfad)"
    return f"{label} (gewählter Grundpfad; Längengleichstand)"


def draw_ordered_route(ax, positions, route_edges):
    """Zeichnet die gelaufene Route gerichtet und nummeriert ihre Schritte."""
    totals = {}
    for edge in route_edges:
        key = frozenset(edge)
        totals[key] = totals.get(key, 0) + 1

    occurrences = {}
    for step, (first, second) in enumerate(route_edges, start=1):
        key = frozenset((first, second))
        occurrence = occurrences.get(key, 0)
        occurrences[key] = occurrence + 1
        center = (totals[key] - 1) / 2
        curvature = (occurrence - center) * 0.18
        first_position = positions[first]
        second_position = positions[second]

        arrow = FancyArrowPatch(
            first_position,
            second_position,
            arrowstyle="-|>",
            mutation_scale=15,
            linewidth=3.6,
            color="#222222",
            connectionstyle=f"arc3,rad={curvature}",
            shrinkA=17,
            shrinkB=17,
            zorder=5,
        )
        ax.add_patch(arrow)

        midpoint_x = (first_position[0] + second_position[0]) / 2
        midpoint_y = (first_position[1] + second_position[1]) / 2
        delta_x = second_position[0] - first_position[0]
        delta_y = second_position[1] - first_position[1]
        midpoint_x -= delta_y * curvature * 0.28
        midpoint_y += delta_x * curvature * 0.28
        ax.text(
            midpoint_x,
            midpoint_y,
            str(step),
            ha="center",
            va="center",
            fontsize=8,
            fontweight="bold",
            color="#ffffff",
            bbox={
                "boxstyle": "circle,pad=0.18",
                "facecolor": "#222222",
                "edgecolor": "#ffffff",
                "linewidth": 0.8,
            },
            zorder=6,
        )


def draw_algorithm_graph(graph, title, output_path, metadata):
    """Zeichnet Ausgangspfade, Routingstrukturen und ausgeführte Route."""
    path_type = metadata["algorithm_path_type"]
    structure_type = metadata["structure_type"]
    paths = metadata["paths"].get(path_type, [])
    structures = metadata["structures"]
    routing_result = metadata["routing_result"]
    positions = nx.spring_layout(graph, seed=123, k=1.2)
    failed_edges = list(metadata.get("failed_edges", []))
    failed_nodes = set(metadata.get("failed_nodes", []))
    grown_structures = [
        structure
        for structure in structures
        if structure.is_tree and structure.grown_graph is not None
    ]
    show_growth = bool(grown_structures)

    panel_count = 4 if show_growth else 3
    figure, axes = plt.subplots(
        1,
        panel_count,
        figsize=(24.0, 5.2) if show_growth else (18.4, 5.2),
    )
    path_ax = axes[0]
    growth_ax = axes[1] if show_growth else None
    structure_ax = axes[2] if show_growth else axes[1]
    route_ax = axes[3] if show_growth else axes[2]
    figure.suptitle(title, fontsize=14)
    path_ax.set_title(
        f"1. Alle {path_type.upper()}s ohne Ausfälle",
        fontsize=12,
    )
    result_title = {
        "paths": "Pfade",
        "one_tree": "One Tree",
        "multiple_trees": "Multiple Trees",
    }[structure_type]
    if growth_ax is not None:
        growth_subject = (
            f"längster {path_type.upper()}"
            if structure_type == "one_tree"
            else f"alle {path_type.upper()}s, längste zuerst"
        )
        growth_ax.set_title(
            f"2. Baumwachstum: {growth_subject}",
            fontsize=12,
        )
    structure_ax.set_title(
        f"{3 if show_growth else 2}. Nach dem Trunkieren: {result_title}",
        fontsize=12,
    )
    route_status = "Erfolg" if routing_result.success else "Fehlschlag"
    route_ax.set_title(
        f"{4 if show_growth else 3}. Ausfälle und Routing: "
        f"{route_status}, Hops={routing_result.hops}",
        fontsize=12,
    )

    all_path_edges = [edge for path in paths for edge in _path_edges(path)]
    _draw_nodes_and_background(
        path_ax, graph, positions, all_path_edges, set()
    )
    _draw_structure_collection(structure_ax, graph, positions, structures)
    if growth_ax is not None:
        all_growth_edges = [
            edge
            for structure in grown_structures
            for edge in structure.grown_graph.edges
        ]
        _draw_nodes_and_background(
            growth_ax,
            graph,
            positions,
            all_growth_edges,
            set(),
        )
    route_edges = list(routing_result.route)
    _draw_nodes_and_background(
        route_ax, graph, positions, route_edges + failed_edges, failed_nodes
    )

    legend_items = []
    from matplotlib.lines import Line2D

    for index, path in enumerate(paths, start=1):
        color = PATH_COLORS[(index - 1) % len(PATH_COLORS)]
        label = f"{path_type.upper()} {index}"
        if structure_type == "one_tree":
            label = one_tree_path_label(path, paths, index, path_type)
        nx.draw_networkx_edges(
            graph,
            positions,
            ax=path_ax,
            edgelist=_path_edges(path),
            width=3.2,
            edge_color=color,
            style="solid",
        )
        legend_items.append(Line2D([0], [0], color=color, lw=3, label=label))

    if growth_ax is not None:
        for structure_index, structure in enumerate(structures):
            if structure not in grown_structures:
                continue
            color = PATH_COLORS[structure_index % len(PATH_COLORS)]
            base_edges = _path_edges(structure.original_path)
            base_keys = {frozenset(edge) for edge in base_edges}
            grown_edges = list(structure.grown_graph.edges)
            added_growth_edges = [
                edge
                for edge in grown_edges
                if frozenset(edge) not in base_keys
            ]
            growth_exits = [
                (node, DESTINATION)
                for node in structure.grown_graph.nodes
                if graph.has_edge(node, DESTINATION)
                and frozenset((node, DESTINATION)) not in base_keys
            ]
            nx.draw_networkx_edges(
                graph,
                positions,
                ax=growth_ax,
                edgelist=base_edges,
                width=3.2,
                edge_color=color,
                style="solid",
            )
            if added_growth_edges:
                nx.draw_networkx_edges(
                    graph,
                    positions,
                    ax=growth_ax,
                    edgelist=added_growth_edges,
                    width=3.2,
                    edge_color=color,
                    style="dashdot",
                )
            if growth_exits:
                nx.draw_networkx_edges(
                    graph,
                    positions,
                    ax=growth_ax,
                    edgelist=growth_exits,
                    width=3.2,
                    edge_color=color,
                    style="dotted",
                )

    if route_edges:
        draw_ordered_route(route_ax, positions, route_edges)

    if failed_edges:
        nx.draw_networkx_edges(
            graph,
            positions,
            ax=route_ax,
            edgelist=failed_edges,
            width=3.0,
            edge_color="#d62728",
            style="dashed",
        )
    has_added_tree_edge = any(
        frozenset(edge)
        not in {
            frozenset(base)
            for base in _path_edges(structure.original_path)
        }
        for structure in structures
        for edge in (
            structure.grown_graph.edges
            if structure.grown_graph is not None
            else structure.graph.edges
        )
    )
    if has_added_tree_edge:
        legend_items.append(
            Line2D(
                [0],
                [0],
                color="#555555",
                lw=3,
                linestyle="dashdot",
                label="hinzugefügte Baumkante",
            )
        )
    if any(
        frozenset((exit_node, DESTINATION))
        not in {
            frozenset(base)
            for base in _path_edges(structure.original_path)
        }
        for structure in structures
        for exit_node in structure.exits
    ):
        legend_items.append(
            Line2D(
                [0],
                [0],
                color="#555555",
                lw=3,
                linestyle=":",
                label="zusätzlicher Ausgang zu d",
            )
        )
    if failed_edges or failed_nodes:
        legend_items.append(
            Line2D(
                [0], [0], color="#d62728", lw=3, linestyle="--", label="Ausfall"
            )
        )
    if route_edges:
        legend_items.append(
            Line2D(
                [0],
                [0],
                color="#222222",
                lw=4,
                linestyle="-",
                label="tatsächlich gelaufene Route (nummeriert)",
            )
        )
    if legend_items:
        figure.legend(
            handles=legend_items,
            loc="lower center",
            bbox_to_anchor=(0.5, 0.01),
            ncol=min(len(legend_items), 4),
            frameon=False,
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    figure.subplots_adjust(bottom=0.20, top=0.84, wspace=0.04)
    figure.savefig(output_path, bbox_inches="tight")
    plt.close(figure)


def draw_disjointness_comparison(graph, output_path):
    """Vergleicht EDP-/NDP-Berechnung und Routing auf demselben Graphen."""
    analysis = analyze_disjointness_routing(graph)
    edps = analysis["edps"]
    ndps = analysis["ndps"]
    seed = graph.graph["seed"]
    positions = nx.spring_layout(graph, seed=seed, k=1.35)
    figure, axes = plt.subplots(1, 2, figsize=(12.8, 4.8))
    figure.suptitle(
        "Automatisch erzeugter Erdős-Rényi-Graph "
        f"(n={graph.graph['nodes']}, p={graph.graph['p']}, seed={seed})",
        fontsize=14,
    )
    axes[0].set_title(
        f"{len(edps)} EDPs: x darf geteilt werden\n"
        f"Routing vor Ausfall: {'Erfolg' if analysis['edp_before'].success else 'Fehlschlag'}; "
        f"nach x-Ausfall: {'Erfolg' if analysis['edp_after'].success else 'Fehlschlag'}",
        fontsize=12,
    )
    axes[1].set_title(
        f"{len(ndps)} NDP: innere Knoten dürfen nicht geteilt werden\n"
        f"Routing vor Ausfall: {'Erfolg' if analysis['ndp_before'].success else 'Fehlschlag'}; "
        f"nach x-Ausfall: {'Erfolg' if analysis['ndp_after'].success else 'Fehlschlag'}",
        fontsize=12,
    )

    edp_edges = [edge for path in edps for edge in _path_edges(path)]
    ndp_edges = [edge for path in ndps for edge in _path_edges(path)]
    _draw_nodes_and_background(axes[0], graph, positions, edp_edges, set())
    _draw_nodes_and_background(axes[1], graph, positions, ndp_edges, set())

    from matplotlib.lines import Line2D

    handles = []
    for index, path in enumerate(edps, start=1):
        color = PATH_COLORS[(index - 1) % len(PATH_COLORS)]
        nx.draw_networkx_edges(
            graph,
            positions,
            ax=axes[0],
            edgelist=_path_edges(path),
            width=3.5,
            edge_color=color,
        )
        handles.append(
            Line2D([0], [0], color=color, lw=3, label=f"EDP {index}")
        )

    for index, path in enumerate(ndps, start=1):
        color = PATH_COLORS[(index - 1) % len(PATH_COLORS)]
        nx.draw_networkx_edges(
            graph,
            positions,
            ax=axes[1],
            edgelist=_path_edges(path),
            width=3.5,
            edge_color=color,
            style="dashdot",
        )
        handles.append(
            Line2D(
                [0],
                [0],
                color=color,
                lw=3,
                linestyle="dashdot",
                label=f"NDP {index}",
            )
        )

    for ax in axes:
        nx.draw_networkx_nodes(
            graph,
            positions,
            ax=ax,
            nodelist=["x"],
            node_color="#fff2a8",
            edgecolors="#a66b00",
            linewidths=2.4,
            node_size=780,
        )
        nx.draw_networkx_labels(
            graph,
            positions,
            ax=ax,
            labels={"x": "x"},
            font_size=10,
            font_weight="bold",
        )
        ax.annotate(
            "gemeinsamer innerer Knoten",
            xy=positions["x"],
            xytext=(0, 34),
            textcoords="offset points",
            ha="center",
            fontsize=10,
            arrowprops={"arrowstyle": "->", "color": "#666666"},
        )

    figure.legend(
        handles=handles,
        loc="lower center",
        bbox_to_anchor=(0.5, 0.01),
        ncol=len(handles),
        frameon=False,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    figure.subplots_adjust(bottom=0.18, top=0.82, wspace=0.08)
    figure.savefig(output_path, bbox_inches="tight")
    plt.close(figure)


def _draw_path_collection(ax, graph, positions, paths, path_type):
    """Zeichnet eine berechnete EDP- oder NDP-Menge in ein Teilbild."""
    path_edges = [edge for path in paths for edge in _path_edges(path)]
    _draw_nodes_and_background(ax, graph, positions, path_edges, set())
    for index, path in enumerate(paths, start=1):
        nx.draw_networkx_edges(
            graph,
            positions,
            ax=ax,
            edgelist=_path_edges(path),
            width=3.4,
            edge_color=(
                THESIS_PATH_COLORS[
                    (index - 1) % len(THESIS_PATH_COLORS)
                ]
            ),
            style="solid",
        )


def draw_thesis_path_comparison(graph, metadata, output_path):
    """Zeichnet EDPs und NDPs mit identischer Knotenanordnung."""
    from matplotlib.lines import Line2D

    paths = metadata["paths"]
    positions = nx.spring_layout(
        graph,
        seed=THESIS_LAYOUT_SEED,
        k=1.05,
        iterations=400,
    )
    figure, axes = plt.subplots(1, 2, figsize=(12.0, 5.0))

    _draw_path_collection(axes[0], graph, positions, paths["edp"], "edp")

    _draw_path_collection(axes[1], graph, positions, paths["ndp"], "ndp")

    shared_edp_nodes = shared_inner_nodes(paths["edp"])
    if shared_edp_nodes:
        nx.draw_networkx_nodes(
            graph,
            positions,
            ax=axes[0],
            nodelist=sorted(shared_edp_nodes, key=str),
            node_color="#fff2a8",
            edgecolors="#a66b00",
            linewidths=2.4,
            node_size=760,
        )
        nx.draw_networkx_labels(
            graph,
            positions,
            ax=axes[0],
            labels={node: str(node) for node in shared_edp_nodes},
            font_size=10,
            font_weight="bold",
        )

    maximum_paths = max(len(paths["edp"]), len(paths["ndp"]))
    handles = [
        Line2D(
            [0],
            [0],
            color=(
                THESIS_PATH_COLORS[
                    (index - 1) % len(THESIS_PATH_COLORS)
                ]
            ),
            lw=3,
            label=f"Pfad {index}",
        )
        for index in range(1, maximum_paths + 1)
    ]
    if shared_edp_nodes:
        handles.append(
            Line2D(
                [0],
                [0],
                marker="o",
                linestyle="none",
                markerfacecolor="#fff2a8",
                markeredgecolor="#a66b00",
                markeredgewidth=1.8,
                markersize=10,
                label="gemeinsamer innerer EDP-Knoten",
            )
        )
    figure.legend(
        handles=handles,
        loc="lower center",
        bbox_to_anchor=(0.5, 0.01),
        ncol=4,
        frameon=False,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    figure.subplots_adjust(bottom=0.22, top=0.98, wspace=0.05)
    figure.savefig(output_path, bbox_inches="tight")
    plt.close(figure)


def _draw_structure_collection(ax, graph, positions, structures):
    """Zeichnet finale Pfad- und Baumstrukturen nach dem Trunkieren."""
    structure_edges = [
        edge for structure in structures for edge in _structure_edges(structure)
    ]
    all_base_edge_keys = {
        frozenset(edge)
        for structure in structures
        for edge in _path_edges(structure.original_path)
    }
    _draw_nodes_and_background(ax, graph, positions, structure_edges, set())
    for index, structure in enumerate(structures, start=1):
        color = THESIS_PATH_COLORS[
            (index - 1) % len(THESIS_PATH_COLORS)
        ]
        base_edges = _path_edges(structure.original_path)
        base_keys = {frozenset(edge) for edge in base_edges}
        base_nodes = set(structure.original_path[:-1])
        added_edges = [
            edge
            for edge in structure.graph.edges
            if frozenset(edge) not in base_keys
        ]
        additional_exits = _visible_additional_exits(
            structure,
            all_base_edge_keys,
        )
        nx.draw_networkx_edges(
            graph,
            positions,
            ax=ax,
            edgelist=base_edges,
            width=3.1,
            edge_color=color,
        )
        if added_edges:
            nx.draw_networkx_edges(
                graph,
                positions,
                ax=ax,
                edgelist=added_edges,
                width=3.1,
                edge_color=BRANCH_COLOR,
            )
        if additional_exits:
            path_exits = [
                edge for edge in additional_exits if edge[0] in base_nodes
            ]
            branch_exits = [
                edge for edge in additional_exits if edge[0] not in base_nodes
            ]
            if path_exits:
                nx.draw_networkx_edges(
                    graph,
                    positions,
                    ax=ax,
                    edgelist=path_exits,
                    width=3.1,
                    edge_color=color,
                    style="dotted",
                )
            if branch_exits:
                nx.draw_networkx_edges(
                    graph,
                    positions,
                    ax=ax,
                    edgelist=branch_exits,
                    width=3.1,
                    edge_color=BRANCH_COLOR,
                    style="dotted",
                )


def _visible_additional_exits(structure, all_base_edge_keys):
    """Lässt farbige Basispfad-Ausgänge in der Zeichnung unverändert."""
    return [
        (exit_node, DESTINATION)
        for exit_node in structure.exits
        if frozenset((exit_node, DESTINATION)) not in all_base_edge_keys
    ]


def _draw_thesis_structure_comparison(
    graph,
    metadata,
    output_path,
    structure_type,
):
    """Vergleicht EDP- und NDP-Strukturen eines Baumverfahrens."""
    from matplotlib.lines import Line2D

    positions = nx.spring_layout(
        graph,
        seed=THESIS_LAYOUT_SEED,
        k=1.05,
        iterations=400,
    )
    figure, axes = plt.subplots(1, 2, figsize=(12.0, 5.4))
    for ax, path_type in zip(axes, ("edp", "ndp")):
        structures = metadata["structures"][f"{path_type}_{structure_type}"]
        _draw_structure_collection(ax, graph, positions, structures)

    maximum_structures = max(
        len(metadata["structures"][f"{path_type}_{structure_type}"])
        for path_type in ("edp", "ndp")
    )
    handles = [
        Line2D(
            [0],
            [0],
            color=(
                THESIS_PATH_COLORS[
                    (index - 1) % len(THESIS_PATH_COLORS)
                ]
            ),
            lw=3,
            label=f"Pfad {index}",
        )
        for index in range(1, maximum_structures + 1)
    ]
    handles.extend(
        [
            Line2D(
                [0],
                [0],
                color=BRANCH_COLOR,
                lw=3,
                label="hinzugefügter Baumast",
            ),
            Line2D(
                [0],
                [0],
                color=BRANCH_COLOR,
                lw=3,
                linestyle="dotted",
                label="zusätzlicher Ausgang über Baumast",
            ),
        ]
    )
    figure.legend(
        handles=handles,
        loc="lower center",
        bbox_to_anchor=(0.5, 0.02),
        ncol=5,
        frameon=False,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    figure.subplots_adjust(
        bottom=0.18,
        top=0.98,
        left=0.02,
        right=0.98,
        wspace=0.04,
    )
    figure.savefig(output_path, bbox_inches="tight")
    plt.close(figure)


def draw_thesis_one_tree_comparison(graph, metadata, output_path):
    """Vergleicht die EDP- und NDP-basierte One-Tree-Struktur."""
    _draw_thesis_structure_comparison(
        graph,
        metadata,
        output_path,
        "one_tree",
    )


def draw_thesis_multiple_trees_comparison(graph, metadata, output_path):
    """Vergleicht die EDP- und NDP-basierten Multiple-Trees-Strukturen."""
    _draw_thesis_structure_comparison(
        graph,
        metadata,
        output_path,
        "multiple_trees",
    )


def draw_graph(graph, title, output_path, metadata=None):
    """Speichert eine erklärende Abbildung als SVG oder PNG."""
    if metadata and metadata.get("algorithm") not in (None, "none"):
        draw_algorithm_graph(graph, title, output_path, metadata)
        return
    metadata = metadata or {}
    positions = nx.spring_layout(graph, seed=123, k=1.2)
    plt.figure(figsize=(7.4, 4.6))
    ax = plt.gca()
    ax.set_title(title, fontsize=14)
    ax.axis("off")

    source_target_nodes = [node for node in (SOURCE, DESTINATION) if node in graph]
    failed_nodes = set(metadata.get("failed_nodes", []))
    normal_nodes = [
        node
        for node in graph.nodes
        if node not in source_target_nodes and node not in failed_nodes
    ]

    nx.draw_networkx_nodes(
        graph,
        positions,
        nodelist=normal_nodes,
        node_color="#f7f7f7",
        edgecolors="#333333",
        linewidths=1.4,
        node_size=850,
    )
    nx.draw_networkx_nodes(
        graph,
        positions,
        nodelist=source_target_nodes,
        node_color="#d9edf7",
        edgecolors="#1f77b4",
        linewidths=2.0,
        node_size=900,
    )
    if failed_nodes:
        nx.draw_networkx_nodes(
            graph,
            positions,
            nodelist=failed_nodes,
            node_color="#f8d7da",
            edgecolors="#c82333",
            linewidths=2.4,
            node_size=900,
        )

    failed_edges = list(metadata.get("failed_edges", []))
    path_edge_groups = []
    for path_type in ("edp", "ndp"):
        for index, path in enumerate(
            metadata.get("paths", {}).get(path_type, []),
            start=1,
        ):
            path_edge_groups.append(
                (path_type.upper(), index, _path_edges(path))
            )

    highlighted_edges = failed_edges[:]
    for _, _, edges in path_edge_groups:
        highlighted_edges.extend(edges)
    highlighted = {frozenset(edge) for edge in highlighted_edges}
    normal_edges = [
        edge for edge in graph.edges if frozenset(edge) not in highlighted
    ]

    nx.draw_networkx_edges(
        graph,
        positions,
        edgelist=normal_edges,
        width=1.2,
        edge_color="#b8b8b8",
    )
    for color_index, (path_type_label, index, edges) in enumerate(path_edge_groups):
        color = PATH_COLORS[color_index % len(PATH_COLORS)]
        style = "solid" if path_type_label == "EDP" else "dashdot"
        nx.draw_networkx_edges(
            graph,
            positions,
            edgelist=edges,
            width=3.2,
            edge_color=color,
            style=style,
        )
    nx.draw_networkx_edges(
        graph,
        positions,
        edgelist=failed_edges,
        width=3.0,
        edge_color="#d62728",
        style="dashed",
    )
    nx.draw_networkx_labels(graph, positions, font_size=11, font_weight="bold")

    legend_items = []
    for color_index, (path_type_label, index, _) in enumerate(path_edge_groups):
        color = PATH_COLORS[color_index % len(PATH_COLORS)]
        style = "-" if path_type_label == "EDP" else "-."
        legend_items.append((f"{path_type_label} {index}", color, style))
    if failed_edges or failed_nodes:
        legend_items.append(("Ausfall", "#d62728", "--"))
    if legend_items:
        from matplotlib.lines import Line2D

        handles = [
            Line2D([0], [0], color=color, lw=3, linestyle=style, label=label)
            for label, color, style in legend_items
        ]
        ax.legend(
            handles=handles,
            loc="lower center",
            bbox_to_anchor=(0.5, -0.16),
            ncol=min(len(handles), 4),
            frameon=False,
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.subplots_adjust(bottom=0.18)
    plt.tight_layout()
    plt.savefig(output_path, bbox_inches="tight")
    plt.close()


def create_disjointness_comparison_files(
    output_dir=DEFAULT_OUTPUT_DIR,
    formats=("svg", "png"),
):
    """Erzeugt den direkten EDP-/NDP-Vergleich auf demselben Graphen."""
    figure_dir = Path(output_dir) / "figures"
    graph = create_disjointness_strength_graph()
    written = []
    for file_format in formats:
        figure_path = figure_dir / f"disjointness_edp_vs_ndp.{file_format}"
        draw_disjointness_comparison(graph, figure_path)
        written.append(figure_path)
    return written


def create_pipeline_overview_files(
    output_dir=DEFAULT_OUTPUT_DIR,
    formats=("svg", "png"),
):
    """Schreibt die Ablaufgrafik ohne Experimente oder Routing auszuführen."""
    figure_dir = Path(output_dir) / "figures"
    written = []
    for file_format in formats:
        figure_path = figure_dir / f"pipeline_overview.{file_format}"
        draw_pipeline_overview(figure_path)
        written.append(figure_path)
    return written


def create_failure_comparison_files(
    output_dir=DEFAULT_OUTPUT_DIR,
    formats=("svg", "png"),
):
    """Schreibt den Kanten-/Knotenausfallvergleich für die Präsentation."""
    graph, metadata = failure_comparison_scene()
    figure_dir = Path(output_dir) / "figures"
    written = []
    for file_format in formats:
        figure_path = figure_dir / f"failure_comparison_link_node.{file_format}"
        draw_failure_comparison(graph, metadata, figure_path)
        written.append(figure_path)
    return written


def create_thesis_comparison_files(
    output_dir=DEFAULT_OUTPUT_DIR,
    formats=("svg", "png"),
):
    """Erzeugt drei gemeinsame Vergleichsabbildungen für die Ausarbeitung."""
    figure_dir = Path(output_dir) / "figures"
    graph, metadata = thesis_comparison_scene()
    figures = (
        (
            "thesis_comparison_edp_ndp_paths",
            draw_thesis_path_comparison,
        ),
        (
            "thesis_comparison_edp_ndp_one_tree",
            draw_thesis_one_tree_comparison,
        ),
        (
            "thesis_comparison_edp_ndp_multiple_trees",
            draw_thesis_multiple_trees_comparison,
        ),
    )
    written = []
    for stem, draw_function in figures:
        for file_format in formats:
            figure_path = figure_dir / f"{stem}.{file_format}"
            draw_function(graph, metadata, figure_path)
            written.append(figure_path)
    return written


def create_configured_scene_files(
    output_dir=DEFAULT_OUTPUT_DIR,
    formats=("svg", "png"),
    graph_type="erdos_renyi",
    nodes=12,
    p=0.28,
    degree=3,
    path_type="both",
    algorithm="none",
    max_paths=0,
    failure_type="node",
    failure_model="random",
    fail_factor=0.8,
    failure_start=0.8,
    failure_drop=0.3,
    seed=123,
):
    """Schreibt eine konfigurierbare Szene und gibt die Bildpfade zurück."""
    output_dir = Path(output_dir)
    figure_dir = output_dir / "figures"
    name, graph, metadata = configured_scene(
        graph_type=graph_type,
        nodes=nodes,
        p=p,
        degree=degree,
        path_type=path_type,
        algorithm=algorithm,
        max_paths=max_paths,
        failure_type=failure_type,
        failure_model=failure_model,
        fail_factor=fail_factor,
        failure_start=failure_start,
        failure_drop=failure_drop,
        seed=seed,
    )
    failure_token = (
        "nofail"
        if failure_model == "none"
        else f"ff{filename_token(fail_factor)}"
        if failure_model == "random"
        else f"fs{filename_token(failure_start)}_fd{filename_token(failure_drop)}"
    )
    structure_token = algorithm if algorithm != "none" else path_type
    failure_name = (
        "no_failure"
        if failure_model == "none"
        else f"{failure_model}_{failure_type}"
    )
    stem = (
        f"{name}_{graph_type}_{structure_token}_"
        f"{failure_name}_n{nodes}_seed{seed}_{failure_token}"
    )
    written = []
    for file_format in formats:
        figure_path = figure_dir / f"{stem}.{file_format}"
        draw_graph(graph, metadata["title"], figure_path, metadata)
        written.append(figure_path)
    return written


def parse_args(argv=None):
    """Liest Kommandozeilenargumente für die Abbildungserzeugung."""
    parser = argparse.ArgumentParser(
        description="Erzeugt Bildbeispiele für die BA-Ausarbeitung."
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Ausgabeordner für figures/.",
    )
    parser.add_argument(
        "--scene",
        choices=[
            "disjointness", "comparison", "failure_comparison",
            "pipeline", "configured", "all",
        ],
        default="comparison",
        help="Welche Abbildungen erzeugt werden.",
    )
    parser.add_argument(
        "--formats",
        nargs="+",
        choices=["svg", "png", "pdf"],
        default=["svg", "png"],
        help="Bildformate für die Abbildungen.",
    )
    parser.add_argument("--seed", type=int, default=123)
    parser.add_argument(
        "--graph-type",
        choices=["erdos_renyi", "random_regular"],
        default="erdos_renyi",
    )
    parser.add_argument("--nodes", type=int, default=12)
    parser.add_argument("--p", type=float, default=0.28)
    parser.add_argument("--degree", type=int, default=3)
    parser.add_argument(
        "--path-type",
        choices=["edp", "ndp", "both", "none"],
        default="both",
        help="Welche Pfade markiert werden; none erzeugt nur Graph und Ausfälle.",
    )
    parser.add_argument(
        "--algorithm",
        choices=ALGORITHM_CHOICES,
        default="none",
        help=(
            "Zeichnet genau einen Algorithmus. Bei none wird stattdessen "
            "--path-type verwendet."
        ),
    )
    parser.add_argument(
        "--max-paths",
        type=int,
        default=0,
        help="Maximale Pfadanzahl; 0 berücksichtigt alle berechneten Pfade.",
    )
    parser.add_argument(
        "--failure-type",
        choices=["link", "node"],
        default="node",
    )
    parser.add_argument(
        "--failure-model",
        choices=["none", "random", "clustered"],
        default="random",
    )
    parser.add_argument(
        "--fail-factor",
        "--failFactor",
        dest="fail_factor",
        type=float,
        default=0.8,
        help=(
            "failFactor für Random-Ausfälle wie in der Pipeline: "
            "round((Konnektivität - 1) * failFactor)."
        ),
    )
    parser.add_argument(
        "--failure-start",
        type=float,
        default=0.8,
        help="Failure Rate für clustered Ausfälle.",
    )
    parser.add_argument(
        "--failure-drop",
        type=float,
        default=0.3,
        help="Abnahme der Failure Rate pro Cluster-Schicht.",
    )
    return parser.parse_args(argv)


def main(argv=None):
    """Erzeugt alle Dateien und gibt die Pfade aus."""
    args = parse_args(argv)
    written = []
    if args.scene in ("pipeline", "all"):
        written.extend(
            create_pipeline_overview_files(args.output_dir, tuple(args.formats))
        )
    if args.scene in ("failure_comparison", "all"):
        written.extend(
            create_failure_comparison_files(args.output_dir, tuple(args.formats))
        )
    if args.scene in ("disjointness", "all"):
        written.extend(
            create_disjointness_comparison_files(
                args.output_dir,
                tuple(args.formats),
            )
        )
    if args.scene in ("comparison", "all"):
        written.extend(
            create_thesis_comparison_files(
                args.output_dir,
                tuple(args.formats),
            )
        )
    if args.scene in ("configured", "all"):
        written.extend(
            create_configured_scene_files(
                output_dir=args.output_dir,
                formats=tuple(args.formats),
                graph_type=args.graph_type,
                nodes=args.nodes,
                p=args.p,
                degree=args.degree,
                path_type=args.path_type,
                algorithm=args.algorithm,
                max_paths=args.max_paths,
                failure_type=args.failure_type,
                failure_model=args.failure_model,
                fail_factor=args.fail_factor,
                failure_start=args.failure_start,
                failure_drop=args.failure_drop,
                seed=args.seed,
            )
        )
    for path in written:
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
