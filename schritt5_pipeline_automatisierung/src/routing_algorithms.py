"""Paper-nahe Routingverfahren für Schritt 4.

Der gemeinsame Kern bildet die sechs Kombinationen aus EDP/NDP und
Paths/One Tree/Multiple Trees ab. Die Baumvarianten folgen Abschnitt 4 und
Algorithmus 1--3 des TREE-Papers (arXiv:2111.14123v1): längste Pfade werden
zuerst erweitert, das Ziel gehört nicht zum Baum, redundante Äste werden
trunkiert und das Routing probiert die Strukturen danach kürzeste zuerst.
"""

from dataclasses import dataclass
from typing import Iterable, Sequence

import networkx as nx


PATH_TYPES = ("edp", "ndp")
STRUCTURE_TYPES = ("paths", "one_tree", "multiple_trees")
BASE_ALGORITHMS = tuple(
    f"{path_type}_{structure_type}"
    for path_type in PATH_TYPES
    for structure_type in STRUCTURE_TYPES
)

@dataclass
class RoutingStructure:
    """Beschreibt genau eine Routing-Struktur für ein s-d-Paar.

    Eine Struktur kann entweder ein reiner disjunkter Pfad oder ein aus einem
    Pfad gewachsener Baum sein. Wichtig ist die paper-nahe Modellierung: Der
    Zielknoten `destination` ist nie Teil des gespeicherten Baums. Stattdessen
    merkt sich `exits`, über welche Baumknoten das Ziel noch direkt erreicht
    werden kann. Dadurch lässt sich dieselbe Datenklasse für Paths, One Tree
    und Multiple Trees verwenden.
    """

    graph: nx.Graph  # Pfad bzw. trunkierten Baum ohne Zielknoten d.
    original_path: tuple  # Ursprünglicher s-d-Pfad, aus dem die Struktur entstand.
    exits: tuple  # Baum-/Pfadknoten mit direkter Kante zum Ziel d.
    is_tree: bool  # True bei gewachsenem Baum, False bei reinem Pfad.
    grown_graph: nx.Graph | None = None  # Baum vor dem abschließenden Trunkieren.


@dataclass
class RoutingResult:
    """Speichert das Ergebnis eines Algorithmus auf einer Failure-Instanz.

    Die Klasse kapselt alles, was später in die Long-CSV geschrieben und für
    die Auswertung aggregiert wird: Erfolg/Misserfolg, Hop-Anzahl, tatsächlich
    gelaufene Kantenfolge sowie die Größe der vorbereiteten Strukturmenge. Bei
    einem Fehlschlag wird `hops` bewusst auf `-1` gesetzt, damit fehlgeschlagene
    Routen nicht versehentlich als kurze Pfade in Mittelwerte eingehen.
    """

    algorithm: str  # Name der Variante, z. B. "edp_one_tree".
    success: bool  # True, wenn trotz Ausfällen ein Weg nach d gefunden wurde.
    hops: int  # Anzahl der gelaufenen Kanten; bei Fehlschlag: -1.
    route: list  # Chronologische Kantenfolge inklusive Rückwegen beim Backtracking.
    nr_paths: int  # Anzahl berechneter EDPs/NDPs für diese Instanz.
    nr_structures: int  # Anzahl getesteter Pfad-/Baumstrukturen.


# Schritt-7-Erweiterungspunkt: einfache Zusatzalgorithmen hier registrieren,
# z. B. "shortest_path": route_shortest_path.
EXTRA_ALGORITHM_RUNNERS = {}
ALGORITHMS = BASE_ALGORITHMS + tuple(EXTRA_ALGORITHM_RUNNERS)


def algorithm_path_type(algorithm):
    """Liefert den Pfadtyp für paper-nahe Algorithmen, sonst None."""
    prefix = algorithm.split("_", 1)[0]
    return prefix if algorithm in BASE_ALGORITHMS and prefix in PATH_TYPES else None


def get_disjoint_paths(graph: nx.Graph, source, destination, path_type: str) -> list[list]:
    """Berechnet EDPs oder intern knotendisjunkte NDPs, kürzeste zuerst."""
    if path_type == "edp":
        paths = list(nx.edge_disjoint_paths(graph, source, destination))
    elif path_type == "ndp":
        paths = list(nx.node_disjoint_paths(graph, source, destination))
    else:
        raise ValueError(f"Unknown path type: {path_type}")
    return sorted((list(path) for path in paths), key=lambda path: (len(path), tuple(map(str, path))))


def _edge_key(first, second) -> frozenset:
    """Normalisiert eine ungerichtete Kante als hashbaren Schlüssel."""
    return frozenset((first, second))


def _base_tree(path: Sequence) -> nx.Graph:
    """Erzeugt den Ausgangspfad ohne d; d darf laut Paper kein Baumknoten sein."""
    tree = nx.Graph()
    tree.add_nodes_from(path[:-1])
    tree.add_edges_from(zip(path[:-2], path[1:-1]))
    return tree


def _grow_tree(
    graph: nx.Graph,
    tree: nx.Graph,
    destination,
    start_nodes: Sequence,
    globally_used_edges: set[frozenset] | None = None,
    protected_nodes: set | None = None,
) -> None:
    """Erweitert einen Ausgangspfad von seinen inneren Knoten aus.

    Bereits vorhandene disjunkte Pfade können über `globally_used_edges` und
    `protected_nodes` reserviert werden. Dadurch wächst ein One Tree nur über
    freie Graphbereiche und übernimmt keine Teile der verbleibenden Pfade. Die
    Quelle gehört zum Baumgrundgerüst, ist gemäß TREE-Konstruktion aber kein
    Startpunkt für das Baumwachstum.
    """
    protected_nodes = protected_nodes or set()
    for start_node in start_nodes:
        queue = [start_node]
        index = 0
        while index < len(queue):
            node = queue[index]
            index += 1
            for neighbor in sorted(graph.neighbors(node), key=str):
                if neighbor == destination:
                    continue
                edge = _edge_key(node, neighbor)
                if globally_used_edges is not None and edge in globally_used_edges:
                    continue
                if neighbor in tree:
                    continue
                if neighbor in protected_nodes:
                    continue
                tree.add_edge(node, neighbor)
                queue.append(neighbor)
                if globally_used_edges is not None:
                    globally_used_edges.add(edge)


def truncate_tree(graph: nx.Graph, tree: nx.Graph, source, destination) -> tuple[nx.Graph, tuple]:
    """Algorithmus 3: behält nur Äste zu erreichbaren Nachbarn von d."""
    if source not in tree:
        return nx.Graph(), tuple()

    exit_nodes = {
        node for node in tree.nodes
        if graph.has_edge(node, destination)
    }
    kept_edges = set()
    reachable_exits = []
    for exit_node in sorted(exit_nodes, key=str):
        if not nx.has_path(tree, source, exit_node):
            continue
        reachable_exits.append(exit_node)
        path = nx.shortest_path(tree, source, exit_node)
        kept_edges.update(_edge_key(a, b) for a, b in zip(path, path[1:]))

    truncated = nx.Graph()
    if reachable_exits:
        truncated.add_node(source)
    truncated.add_edges_from(
        (a, b) for a, b in tree.edges if _edge_key(a, b) in kept_edges
    )
    return truncated, tuple(reachable_exits)


def build_structures(
    graph: nx.Graph,
    source,
    destination,
    paths: Sequence[Sequence],
    structure_type: str,
    retain_growth_stage: bool = False,
) -> list[RoutingStructure]:
    """Konstruiert Paths, One Tree oder Multiple Trees nach dem Paper.

    `retain_growth_stage` bewahrt für Illustrationen zusätzlich den noch nicht
    trunkierten Baum. Normale Experimente speichern diese Diagnosekopie nicht.
    """
    if structure_type not in STRUCTURE_TYPES:
        raise ValueError(f"Unknown structure type: {structure_type}")
    if not paths:
        return []

    ascending = sorted((list(path) for path in paths), key=lambda path: (len(path), tuple(map(str, path))))
    longest = ascending[-1]

    if structure_type == "paths":
        return [
            RoutingStructure(_base_tree(path), tuple(path), (path[-2],), False)
            for path in ascending
        ]

    trees_by_path = {}
    if structure_type == "one_tree":
        tree = _base_tree(longest)
        # Wie in der TREE-Konstruktion bleiben die übrigen disjunkten Pfade
        # eigenständige Ausweichstrukturen. Ihre Kanten und inneren Knoten
        # dürfen deshalb nicht in den längsten, zum Baum erweiterten Pfad
        # aufgenommen werden.
        reserved_path_edges = {
            _edge_key(a, b)
            for path in ascending
            for a, b in zip(path[:-2], path[1:-1])
        }
        protected_path_nodes = {
            node
            for path in ascending[:-1]
            for node in path[1:-1]
            if node not in tree
        }
        _grow_tree(
            graph,
            tree,
            destination,
            longest[1:-1],
            reserved_path_edges,
            protected_path_nodes,
        )
        grown_graph = tree.copy() if retain_growth_stage else None
        tree, exits = truncate_tree(graph, tree, source, destination)
        trees_by_path[tuple(longest)] = RoutingStructure(
            tree,
            tuple(longest),
            exits,
            True,
            grown_graph,
        )
    else:
        # Alle Ausgangspfade sind bereits Teil der Strukturen und werden deshalb
        # vor der Erweiterung global reserviert (Algorithmus 2).
        globally_used = {
            _edge_key(a, b)
            for path in ascending
            for a, b in zip(path[:-2], path[1:-1])
        }
        for path in reversed(ascending):
            tree = _base_tree(path)
            _grow_tree(
                graph,
                tree,
                destination,
                path[1:-1],
                globally_used,
            )
            grown_graph = tree.copy() if retain_growth_stage else None
            tree, exits = truncate_tree(graph, tree, source, destination)
            trees_by_path[tuple(path)] = RoutingStructure(
                tree,
                tuple(path),
                exits,
                True,
                grown_graph,
            )

    structures = []
    for path in ascending:
        key = tuple(path)
        if key in trees_by_path:
            structures.append(trees_by_path[key])
        else:
            structures.append(RoutingStructure(_base_tree(path), key, (path[-2],), False))
    return structures


def _rooted_children(tree: nx.Graph, source) -> tuple[dict, dict]:
    """Wurzelt den Baum bei s und liefert Eltern- sowie Kindbeziehungen."""
    parent = {source: None}
    children = {node: [] for node in tree.nodes}
    queue = [source]
    for node in queue:
        for neighbor in sorted(tree.neighbors(node), key=str):
            if neighbor == parent[node] or neighbor in parent:
                continue
            parent[neighbor] = node
            children[node].append(neighbor)
            queue.append(neighbor)
    return parent, children


def _distance_to_exit(children: dict, exits: set, node, cache: dict) -> float:
    """Berechnet die minimale Baumdistanz zum nächsten möglichen Ausgang."""
    if node in cache:
        return cache[node]
    distances = [0] if node in exits else []
    distances.extend(
        1 + _distance_to_exit(children, exits, child, cache)
        for child in children.get(node, [])
    )
    cache[node] = min(distances, default=float("inf"))
    return cache[node]


def route_structure(
    structure: RoutingStructure,
    source,
    destination,
    failed_edges: set[frozenset],
    prefer_original_path: bool = False,
) -> tuple[bool, int, list]:
    """Führt ranked depth-first routing auf genau einer Struktur aus."""
    tree = structure.graph
    if source not in tree:
        return False, 0, []
    _, children = _rooted_children(tree, source)
    exits = set(structure.exits)
    distance_cache = {}
    original_successor = {
        first: second
        for first, second in zip(structure.original_path[:-2], structure.original_path[1:-1])
    }
    route = []

    def visit(node):
        """Besucht einen Knoten rekursiv und backtrackt bei Sackgassen."""
        if node in exits and _edge_key(node, destination) not in failed_edges:
            route.append((node, destination))
            return True

        ordered = sorted(
            children.get(node, []),
            key=lambda child: (
                0 if prefer_original_path and original_successor.get(node) == child else 1,
                _distance_to_exit(children, exits, child, distance_cache),
                str(child),
            ),
        )
        for child in ordered:
            if _edge_key(node, child) in failed_edges:
                continue
            route.append((node, child))
            if visit(child):
                return True
            route.append((child, node))
        return False

    success = visit(source)
    return success, len(route), route


def route_algorithm(
    graph: nx.Graph,
    source,
    destination,
    failures: Iterable[Sequence],
    algorithm: str,
    paths: Sequence[Sequence] | None = None,
) -> RoutingResult:
    """Führt einen der sechs Algorithmen auf einer vorbereiteten Instanz aus."""
    if algorithm in EXTRA_ALGORITHM_RUNNERS:
        return EXTRA_ALGORITHM_RUNNERS[algorithm](
            graph, source, destination, failures
        )
    if algorithm not in ALGORITHMS:
        raise ValueError(f"Unknown algorithm: {algorithm}")
    path_type, structure_suffix = algorithm.split("_", 1)
    structure_type = structure_suffix
    selected_paths = get_disjoint_paths(graph, source, destination, path_type) if paths is None else list(paths)
    structures = build_structures(graph, source, destination, selected_paths, structure_type)
    failed_edges = {_edge_key(*edge) for edge in failures}
    total_hops = 0
    full_route = []

    for structure in structures:
        success, hops, route = route_structure(
            structure,
            source,
            destination,
            failed_edges,
            prefer_original_path=(structure_type == "one_tree" and structure.is_tree),
        )
        total_hops += hops
        full_route.extend(route)
        if success:
            return RoutingResult(algorithm, True, total_hops, full_route, len(selected_paths), len(structures))

    return RoutingResult(algorithm, False, -1, full_route, len(selected_paths), len(structures))


def run_algorithms(
    graph: nx.Graph,
    source,
    destination,
    failures: Iterable[Sequence],
    algorithms: Iterable[str] = BASE_ALGORITHMS,
) -> list[RoutingResult]:
    """Vergleicht ausgewählte Algorithmen mit identischen Pfaden und Ausfällen."""
    algorithms = tuple(algorithms)
    unknown = set(algorithms) - set(ALGORITHMS)
    if unknown:
        raise ValueError(f"Unknown algorithms: {sorted(unknown)}")
    path_cache = {
        path_type: get_disjoint_paths(graph, source, destination, path_type)
        for path_type in {
            path_type
            for algorithm in algorithms
            for path_type in [algorithm_path_type(algorithm)]
            if path_type is not None
        }
    }
    failures = tuple(tuple(edge) for edge in failures)
    return [
        route_algorithm(
            graph,
            source,
            destination,
            failures,
            algorithm,
            paths=(
                path_cache[algorithm_path_type(algorithm)]
                if algorithm_path_type(algorithm) is not None
                else None
            ),
        )
        for algorithm in algorithms
    ]
