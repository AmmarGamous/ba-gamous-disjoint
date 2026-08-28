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
from matplotlib.patches import FancyArrowPatch
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


DEFAULT_OUTPUT_DIR = ILLUSTRATION_ROOT / "output"
SOURCE = "s"
DESTINATION = "d"
PATH_COLORS = list(dict.fromkeys(result_analysis.ALGORITHM_COLORS.values()))
ALGORITHM_CHOICES = [
    "none",
    "edp_paths",
    "edp_one_tree",
    "edp_multiple_trees",
    "ndp_paths",
    "ndp_one_tree",
    "ndp_multiple_trees",
]
NODE_POSITIONS = {
    "s": (0.0, 0.0),
    "a": (1.0, 1.2),
    "b": (1.0, -1.2),
    "x": (2.0, 0.0),
    "c": (3.0, 1.2),
    "e": (3.0, -1.2),
    "d": (4.0, 0.0),
    "u": (2.0, 2.2),
    "v": (2.0, -2.2),
}


def edge_id(edge):
    """Liefert eine stabile ID für eine ungerichtete Kante."""
    return "--".join(sorted(map(str, edge)))


def add_base_attributes(graph, title):
    """Ergänzt Rollen und neutrale Attribute für GraphML und Zeichnung."""
    graph.graph["title"] = title
    for node in graph.nodes:
        graph.nodes[node]["role"] = "source" if node == SOURCE else "destination" if node == DESTINATION else "normal"
        graph.nodes[node]["failed"] = False
    for first, second in graph.edges:
        graph.edges[first, second]["failed"] = False
        graph.edges[first, second]["edp_index"] = 0
        graph.edges[first, second]["ndp_index"] = 0
        graph.edges[first, second]["structure_index"] = 0
        graph.edges[first, second]["structure_kind"] = ""
        graph.edges[first, second]["failure_model"] = ""
    return graph


def mark_path(graph, path, attribute, index):
    """Markiert alle Kanten eines Pfads mit einem Attributwert."""
    for first, second in zip(path, path[1:]):
        graph.edges[first, second][f"{attribute}_index"] = index


def mark_structure(graph, structure, index):
    """Markiert eine Pfad- oder Baumstruktur eines konkreten Algorithmus."""
    kind = "Baum" if structure.is_tree else "Pfad"
    structure_edges = list(structure.graph.edges)
    structure_edges.extend((exit_node, DESTINATION) for exit_node in structure.exits)
    for first, second in structure_edges:
        if graph.has_edge(first, second):
            graph.edges[first, second]["structure_index"] = index
            graph.edges[first, second]["structure_kind"] = kind


def mark_failed_edges(graph, edges, failure_model):
    """Markiert ausgefallene Kanten im Graphen."""
    failed = {frozenset(edge) for edge in edges}
    for first, second in graph.edges:
        if frozenset((first, second)) in failed:
            graph.edges[first, second]["failed"] = True
            graph.edges[first, second]["failure_model"] = failure_model


def mark_failed_nodes(graph, nodes, failure_model):
    """Markiert ausgefallene Knoten im Graphen."""
    for node in nodes:
        graph.nodes[node]["failed"] = True
        graph.nodes[node]["failure_model"] = failure_model


def create_shared_node_graph():
    """Erzeugt einen Graphen, in dem EDPs einen inneren Knoten teilen können."""
    graph = nx.Graph()
    graph.add_edges_from(
        [
            ("s", "a"),
            ("a", "x"),
            ("x", "c"),
            ("c", "d"),
            ("s", "b"),
            ("b", "x"),
            ("x", "e"),
            ("e", "d"),
            ("a", "u"),
            ("u", "c"),
            ("b", "v"),
            ("v", "e"),
        ]
    )
    return add_base_attributes(graph, "EDP-Beispiel mit gemeinsamem inneren Knoten")


def create_node_disjoint_graph():
    """Erzeugt einen Graphen mit klar getrennten NDPs."""
    graph = nx.Graph()
    graph.add_edges_from(
        [
            ("s", "a"),
            ("a", "u"),
            ("u", "c"),
            ("c", "d"),
            ("s", "b"),
            ("b", "v"),
            ("v", "e"),
            ("e", "d"),
            ("a", "x"),
            ("x", "b"),
            ("c", "x"),
            ("x", "e"),
        ]
    )
    return add_base_attributes(graph, "NDP-Beispiel mit getrennten inneren Knoten")


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
    graph = add_base_attributes(
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
    elif graph_type == "complete":
        # Vollständige Graphen sind für Schritt 7/Illustrationen nützlich, aber
        # aktuell nicht Teil der Experiment-Graph-Registry.
        graph = nx.complete_graph(nodes)
        title = f"Vollständiger Graph n={nodes}"
    else:
        raise ValueError(f"Unbekannter Graph-Typ: {graph_type}")
    return add_base_attributes(graph, title)


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
    return add_base_attributes(relabeled, graph.graph.get("title", "Konfigurierter Graph"))


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
        for index, structure in enumerate(structures, start=1):
            mark_structure(graph, structure, index)

    path_types = (
        []
        if algorithm != "none" or path_type == "none"
        else ["edp", "ndp"] if path_type == "both" else [path_type]
    )
    for current_path_type in path_types:
        paths = safe_disjoint_paths(graph, current_path_type, max_paths)
        paths_by_type[current_path_type] = paths
        for index, path in enumerate(paths, start=1):
            mark_path(graph, path, current_path_type, index)

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
    mark_failed_edges(graph, failed_edges, f"{failure_model}_{failure_type}")
    mark_failed_nodes(graph, failed_nodes, f"{failure_model}_{failure_type}")
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


def edp_example():
    """Erzeugt das Beispiel für Edge-Disjoint Paths."""
    graph = create_shared_node_graph()
    paths = first_paths(get_disjoint_paths(graph, SOURCE, DESTINATION, "edp"), 2)
    for index, path in enumerate(paths, start=1):
        mark_path(graph, path, "edp", index)
    return "edp_paths", graph, {"paths": paths, "title": "Edge-Disjoint Paths"}


def ndp_example():
    """Erzeugt das Beispiel für Node-Disjoint Paths."""
    graph = create_node_disjoint_graph()
    paths = first_paths(get_disjoint_paths(graph, SOURCE, DESTINATION, "ndp"), 2)
    for index, path in enumerate(paths, start=1):
        mark_path(graph, path, "ndp", index)
    return "ndp_paths", graph, {"paths": paths, "title": "Node-Disjoint Paths"}


def random_link_failure_example(seed):
    """Erzeugt ein Beispiel für zufällige Link Failures."""
    graph = create_node_disjoint_graph()
    failed_edges, failed_nodes = select_failures(
        graph, SOURCE, DESTINATION, "link", "random", 2, 0.0, 0.3, random.Random(seed)
    )
    mark_failed_edges(graph, failed_edges, "random_link")
    mark_failed_nodes(graph, failed_nodes, "random_link")
    return "random_link_failure", graph, {
        "failed_edges": failed_edges,
        "failed_nodes": failed_nodes,
        "title": "Random Link Failure",
    }


def random_node_failure_example(seed):
    """Erzeugt ein Beispiel für zufällige Node Failures."""
    graph = create_node_disjoint_graph()
    failed_edges, failed_nodes = select_failures(
        graph, SOURCE, DESTINATION, "node", "random", 1, 0.0, 0.3, random.Random(seed)
    )
    mark_failed_edges(graph, failed_edges, "random_node")
    mark_failed_nodes(graph, failed_nodes, "random_node")
    return "random_node_failure", graph, {
        "failed_edges": failed_edges,
        "failed_nodes": failed_nodes,
        "title": "Random Node Failure",
    }


def clustered_link_failure_example(seed):
    """Erzeugt ein Beispiel für geclusterte Link Failures um das Ziel."""
    graph = create_node_disjoint_graph()
    failed_edges, failed_nodes = select_failures(
        graph, SOURCE, DESTINATION, "link", "clustered", 0, 0.9, 0.3, random.Random(seed)
    )
    mark_failed_edges(graph, failed_edges, "clustered_link")
    mark_failed_nodes(graph, failed_nodes, "clustered_link")
    return "clustered_link_failure", graph, {
        "failed_edges": failed_edges,
        "failed_nodes": failed_nodes,
        "title": "Clustered Link Failure",
    }


def clustered_node_failure_example(seed):
    """Erzeugt ein Beispiel für geclusterte Node Failures um das Ziel."""
    graph = create_node_disjoint_graph()
    failed_edges, failed_nodes = select_failures(
        graph, SOURCE, DESTINATION, "node", "clustered", 0, 0.9, 0.3, random.Random(seed)
    )
    mark_failed_edges(graph, failed_edges, "clustered_node")
    mark_failed_nodes(graph, failed_nodes, "clustered_node")
    return "clustered_node_failure", graph, {
        "failed_edges": failed_edges,
        "failed_nodes": failed_nodes,
        "title": "Clustered Node Failure",
    }


def _path_edges(path):
    """Liefert die gerichtungsunabhängigen Kanten eines vollständigen Pfads."""
    return [tuple(edge) for edge in zip(path, path[1:])]


def _structure_edges(structure):
    """Liefert Baumkanten einschließlich der möglichen Ausgänge zu d."""
    edges = list(structure.graph.edges)
    edges.extend((exit_node, DESTINATION) for exit_node in structure.exits)
    return edges


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
    all_structure_edges = [
        edge for structure in structures for edge in _structure_edges(structure)
    ]
    _draw_nodes_and_background(
        path_ax, graph, positions, all_path_edges, set()
    )
    _draw_nodes_and_background(
        structure_ax,
        graph,
        positions,
        all_structure_edges,
        set(),
    )
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

    for index, structure in enumerate(structures, start=1):
        color = PATH_COLORS[(index - 1) % len(PATH_COLORS)]
        base_edges = _path_edges(structure.original_path)
        base_keys = {frozenset(edge) for edge in base_edges}
        added_tree_edges = [
            edge
            for edge in structure.graph.edges
            if frozenset(edge) not in base_keys
        ]
        additional_exits = [
            (exit_node, DESTINATION)
            for exit_node in structure.exits
            if frozenset((exit_node, DESTINATION)) not in base_keys
        ]
        nx.draw_networkx_edges(
            graph,
            positions,
            ax=structure_ax,
            edgelist=base_edges,
            width=3.2,
            edge_color=color,
            style="solid",
        )
        if added_tree_edges:
            nx.draw_networkx_edges(
                graph,
                positions,
                ax=structure_ax,
                edgelist=added_tree_edges,
                width=3.2,
                edge_color=color,
                style="dashdot",
            )
        if additional_exits:
            nx.draw_networkx_edges(
                graph,
                positions,
                ax=structure_ax,
                edgelist=additional_exits,
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


def draw_graph(graph, title, output_path, metadata=None):
    """Speichert eine erklärende Abbildung als SVG oder PNG."""
    if metadata and metadata.get("algorithm") not in (None, "none"):
        draw_algorithm_graph(graph, title, output_path, metadata)
        return
    if all(node in NODE_POSITIONS for node in graph.nodes):
        positions = {node: NODE_POSITIONS[node] for node in graph.nodes}
    else:
        positions = nx.spring_layout(graph, seed=123, k=1.2)
    plt.figure(figsize=(7.4, 4.6))
    ax = plt.gca()
    ax.set_title(title, fontsize=14)
    ax.axis("off")

    normal_nodes = [node for node in graph.nodes if not graph.nodes[node].get("failed")]
    failed_nodes = [node for node in graph.nodes if graph.nodes[node].get("failed")]
    source_target_nodes = [node for node in (SOURCE, DESTINATION) if node in graph]

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

    failed_edges = [
        edge for edge in graph.edges if graph.edges[edge].get("failed")
    ]
    path_edge_groups = []
    for path_type in ("edp", "ndp"):
        index_key = f"{path_type}_index"
        indexes = sorted(
            {
                graph.edges[edge].get(index_key, 0)
                for edge in graph.edges
                if graph.edges[edge].get(index_key, 0)
            }
        )
        for index in indexes:
            edges = [
                edge for edge in graph.edges
                if graph.edges[edge].get(index_key, 0) == index
            ]
            path_edge_groups.append((path_type.upper(), index, edges))

    structure_edge_groups = []
    structure_indexes = sorted(
        {
            graph.edges[edge].get("structure_index", 0)
            for edge in graph.edges
            if graph.edges[edge].get("structure_index", 0)
        }
    )
    for index in structure_indexes:
        edges = [
            edge for edge in graph.edges
            if graph.edges[edge].get("structure_index", 0) == index
        ]
        kind = next(
            (
                graph.edges[edge].get("structure_kind", "Struktur")
                for edge in edges
                if graph.edges[edge].get("structure_kind")
            ),
            "Struktur",
        )
        structure_edge_groups.append((kind, index, edges))

    highlighted_edges = failed_edges[:]
    for _, _, edges in path_edge_groups:
        highlighted_edges.extend(edges)
    for _, _, edges in structure_edge_groups:
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
    for color_index, (kind, index, edges) in enumerate(structure_edge_groups):
        color = PATH_COLORS[color_index % len(PATH_COLORS)]
        style = "solid" if kind == "Pfad" else "dashdot"
        nx.draw_networkx_edges(
            graph,
            positions,
            edgelist=edges,
            width=3.3,
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
    for color_index, (kind, index, _) in enumerate(structure_edge_groups):
        color = PATH_COLORS[color_index % len(PATH_COLORS)]
        style = "-" if kind == "Pfad" else "-."
        legend_items.append((f"{kind} {index}", color, style))
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


def write_graphml(graph, output_path):
    """Schreibt optional eine GraphML-Datei mit den gesetzten Erklärattributen."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    nx.write_graphml(graph, output_path)


def create_examples(
    output_dir=DEFAULT_OUTPUT_DIR,
    formats=("svg", "png"),
    seed=123,
    write_graphml_files=False,
):
    """Erzeugt alle BA-Beispielbilder und gibt die geschriebenen Dateien zurück."""
    output_dir = Path(output_dir)
    figure_dir = output_dir / "figures"
    graphml_dir = output_dir / "graphml"
    examples = [
        edp_example(),
        ndp_example(),
        random_link_failure_example(seed),
        random_node_failure_example(seed),
        clustered_link_failure_example(seed),
        clustered_node_failure_example(seed),
    ]

    written = []
    for name, graph, metadata in examples:
        if write_graphml_files:
            graphml_path = graphml_dir / f"{name}.graphml"
            write_graphml(graph, graphml_path)
            written.append(graphml_path)
        for file_format in formats:
            figure_path = figure_dir / f"{name}.{file_format}"
            draw_graph(graph, metadata["title"], figure_path)
            written.append(figure_path)
    return written


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
        choices=["examples", "disjointness", "configured", "all"],
        default="examples",
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
        choices=["erdos_renyi", "random_regular", "complete"],
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
    parser.add_argument(
        "--write-graphml",
        action="store_true",
        help="Schreibt zusätzlich GraphML-Dateien mit Erklärattributen.",
    )
    return parser.parse_args(argv)


def main(argv=None):
    """Erzeugt alle Dateien und gibt die Pfade aus."""
    args = parse_args(argv)
    written = []
    if args.scene in ("examples", "all"):
        written.extend(
            create_examples(
                args.output_dir,
                tuple(args.formats),
                args.seed,
                write_graphml_files=args.write_graphml,
            )
        )
    if args.scene in ("disjointness", "all"):
        written.extend(
            create_disjointness_comparison_files(
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
