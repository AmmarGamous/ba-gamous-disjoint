"""Vergleicht Routing über Edge-Disjoint Paths (EDPs) und Node-Disjoint Paths (NDPs).

Der Ablauf eines einzelnen Experiments ist:
1. Einen Graphen sowie einen Quell- und Zielknoten auswählen.
2. EDPs und NDPs zwischen Quelle und Ziel berechnen.
3. Zufallsbasierte oder zusammenhängende Link-/Knotenausfälle erzeugen.
4. Mit beiden Pfadarten versuchen, das Ziel trotz der Ausfälle zu erreichen.
5. Pfadanzahlen, Ausfälle, Hops, Stretch und Erfolg in einer CSV-Zeile speichern.

Ein Routing-Ergebnis von -1 bedeutet, dass keine vorberechnete Route das Ziel
erreichen konnte. Die Auswertungsnotebooks interpretieren alle anderen
Hop-Anzahlen als erfolgreiches Routing.
"""

import argparse
import copy
import csv
from itertools import combinations
import math
from pathlib import Path
import random

import networkx as nx


DEBUG = False

# Legt Reihenfolge und Namen aller Spalten in den erzeugten CSV-Dateien fest.
CSV_FIELDNAMES = [
    "rep",
    "failureType",
    "failureModel",
    "nrNodes",
    "nrEdges",
    "graphType",
    "graphParam",
    "graphName",
    "graphMLPath",
    "degree",
    "edgeProb",
    "source",
    "destination",
    "nrEDPs",
    "nrNDPs",
    "failFactor",
    "failureStart",
    "failureDrop",
    "nrFails",
    "nrFailedNodes",
    "spLength",
    "hopsEDP",
    "stretchEDP",
    "hopsNDP",
    "stretchNDP",
]


def kResiliencePathsPrecomp(g):
    """Behält die Schnittstelle des ursprünglichen Projekts bei.

    Für diesen Pfadalgorithmus ist keine separate Vorbereitung des Graphen
    erforderlich. Deshalb wird der Graph unverändert zurückgegeben.
    """
    return g


def getNodeDisjointPaths(g, s, d):
    """Berechnet intern knotendisjunkte Pfade von s nach d.

    Die Pfade dürfen Quelle s und Ziel d gemeinsam verwenden, aber keine
    inneren Knoten teilen. Kürzere Pfade werden beim Routing zuerst getestet.
    """
    paths = list(nx.node_disjoint_paths(g, s, d))
    paths.sort(key=len)
    return paths


def getEdgeDisjointPaths(g, s, d):
    """Berechnet kantendisjunkte Pfade von s nach d als Vergleichsbasis.

    Edge-Disjoint Paths dürfen Knoten teilen, aber keine Kanten. Auch hier
    werden kürzere Pfade zuerst getestet.
    """
    paths = list(nx.edge_disjoint_paths(g, s, d))
    paths.sort(key=len)
    return paths


def nodeFailuresToEdgeFailures(g, failed_nodes):
    """Stellt Knotenausfälle als Menge ihrer inzidenten Kantenausfälle dar.

    Der Routingalgorithmus verarbeitet ausgefallene Kanten. Ein ausgefallener
    Knoten wird deshalb simuliert, indem alle Kanten zu diesem Knoten gesperrt
    werden.
    """
    failed_edges = set()
    for node in failed_nodes:
        for edge in g.edges(node):
            # frozenset macht (u, v) und (v, u) bei ungerichteten Graphen gleich.
            failed_edges.add(frozenset(edge))
    return [tuple(edge) for edge in failed_edges]


def validateClusterParameters(failure_start, failure_drop):
    """Prüft die Parameter für die schichtweise Cluster-Ausbreitung."""
    if not 0.0 <= failure_start <= 1.0:
        raise ValueError("failure_start must be between 0 and 1.")
    if failure_drop <= 0.0:
        raise ValueError("failure_drop must be greater than 0.")


def getClusteredLinkFailures(g, destination, failure_start, failure_drop, rng):
    """Wählt zusammenhängende Kantenausfälle rund um den Zielknoten.

    Die erste Schicht besteht aus allen Kanten am Zielknoten. Anschließend
    wird die Suche über die äußeren Knoten der aktuellen Schicht erweitert.
    failure_start gibt den ausgewählten Anteil der ersten Schicht an.
    failure_drop verringert diesen Anteil nach jeder Schicht.
    """
    validateClusterParameters(failure_start, failure_drop)
    failed_edges = []
    seen_failed_edges = set()
    # Startschicht: alle Kanten, die direkt am Zielknoten liegen.
    incidents = list(g.edges(destination))
    failure_percent = failure_start

    while failure_percent > 0.0 and incidents:
        # floor kann bei kleinen Schichten zu null Ausfällen führen.
        sample_count = math.floor(failure_percent * len(incidents))
        for edge in rng.sample(incidents, sample_count):
            edge_key = frozenset(edge)
            if edge_key not in seen_failed_edges:
                failed_edges.append(edge)
                seen_failed_edges.add(edge_key)

        # Baut aus den Nachbarkanten der aktuellen Schicht die nächste Schicht.
        next_incidents = []
        seen_next_incidents = set()
        for _, outer_node in incidents:
            for edge in g.edges(outer_node):
                edge_key = frozenset(edge)
                if edge_key not in seen_next_incidents:
                    next_incidents.append(edge)
                    seen_next_incidents.add(edge_key)

        incidents = next_incidents
        failure_percent -= failure_drop

    return failed_edges


def getClusteredNodeFailures(g, source, destination, failure_start, failure_drop, rng):
    """Wählt zusammenhängende Knotenausfälle rund um den Zielknoten.

    Die Nachbarn des Zielknotens bilden die erste Schicht. Danach wird die
    Kandidatenmenge über deren Nachbarn erweitert. Quelle und Ziel werden nie
    als ausgefallene Knoten ausgewählt.
    """
    validateClusterParameters(failure_start, failure_drop)
    failed_nodes = []
    # Quelle und Ziel müssen erreichbar bleiben können und sind daher geschützt.
    candidates = [
        node
        for node in g.neighbors(destination)
        if node not in (source, destination)
    ]
    failure_percent = failure_start

    while failure_percent > 0.0 and candidates:
        sample_count = math.floor(failure_percent * len(candidates))
        failed_nodes.extend(rng.sample(candidates, sample_count))
        # dict.fromkeys entfernt Duplikate und behält die Reihenfolge bei.
        failed_nodes = list(dict.fromkeys(failed_nodes))

        # Erweitert den Cluster um die Nachbarn der aktuellen Kandidatenschicht.
        next_candidates = []
        for node in candidates:
            for neighbor in g.neighbors(node):
                if neighbor not in (source, destination) and neighbor not in failed_nodes:
                    next_candidates.append(neighbor)

        candidates = list(dict.fromkeys(next_candidates))
        failure_percent -= failure_drop

    return failed_nodes


def kResiliencePaths(s, d, fails, g):
    """Versucht das Routing von s nach d über vorberechnete knotendisjunkte Pfade."""
    return routeDisjointPaths(s, d, fails, g, getNodeDisjointPaths, "Node-disjoint")


def kResilienceEdgeDisjointPaths(s, d, fails, g):
    """Versucht dasselbe Routing über kantendisjunkte Vergleichspfade."""
    return routeDisjointPaths(s, d, fails, g, getEdgeDisjointPaths, "Edge-disjoint")


def routeDisjointPaths(s, d, fails, g, path_provider, debug_label):
    """Bereitet disjunkte Pfade vor und startet den eigentlichen Routingversuch.

    Jede Kante eines vorberechneten Pfades erhält als Attribut seine
    Pfadnummer. Kanten mit Attribut "0" gehören zu keinem vorberechneten Pfad.
    path_provider entscheidet, ob NDPs oder EDPs verwendet werden.
    """
    # Eine Kopie verhindert, dass Pfadattribute den Originalgraphen verändern.
    g_copy = copy.deepcopy(g)
    nx.set_edge_attributes(g_copy, "0", "attr")

    try:
        disjoint_paths = path_provider(g_copy, s, d)
    except nx.NetworkXException:
        # Ohne berechenbare Pfade ist kein Routing möglich.
        return -1, g_copy, [], []

    paths_attributes = []
    for path_number, path in enumerate(disjoint_paths, start=1):
        path_attribute = str(path_number)
        paths_attributes.append(path_attribute)
        # Markiert alle Kanten dieses Pfades mit derselben Pfadnummer.
        for node, next_node in zip(path, path[1:]):
            g_copy[node][next_node]["attr"] = path_attribute
        if DEBUG:
            print(debug_label, "path no.", path_number, ":", path)

    hops, route = routing_kResiliencePaths(
        s,
        d,
        fails,
        g_copy.copy(),
        paths_attributes=paths_attributes,
    )
    return hops, g_copy, route, paths_attributes


def routing_kResiliencePaths(s, d, fails, g_copy, paths_attributes=None):
    """Entfernt unbenutzbare Kanten und testet die Pfade der Reihe nach.

    Nur Kanten vorberechneter Pfade bleiben erhalten. Danach wird für jede
    Pfadnummer geprüft, ob der zugehörige Pfad Quelle und Ziel trotz der
    Ausfälle noch verbindet.
    """
    # frozenset erlaubt richtungsunabhängige Vergleiche ungerichteter Kanten.
    failed_edges = {frozenset(edge) for edge in fails}

    for edge in list(g_copy.edges):
        edge_data = g_copy.get_edge_data(*edge)
        # Entfernt ausgefallene Kanten und Kanten, die zu keinem Pfad gehören.
        if frozenset(edge) in failed_edges or edge_data.get("attr") == "0":
            g_copy.remove_edge(*edge)

    if paths_attributes is None:
        # Wird keine Reihenfolge übergeben, werden vorhandene Pfadnummern gesammelt.
        paths_attributes = []
        for _, _, data in g_copy.edges(data=True):
            if data["attr"] not in paths_attributes:
                paths_attributes.append(data["attr"])

    hops = 0
    route = []
    for path_attribute in paths_attributes:
        # Betrachtet immer nur die Kanten eines einzelnen vorberechneten Pfades.
        path_graph = nx.Graph(
            (node, next_node)
            for node, next_node, data in g_copy.edges(data=True)
            if data["attr"] == path_attribute
        )
        if s not in path_graph:
            continue

        # Der bereinigte DFS folgt dem Pfad und zählt die benötigten Hops.
        for node, next_node, label in cleanDfsEdges(nx.dfs_labeled_edges(path_graph, s)):
            route.append((node, next_node))
            hops += 1
            if d in (node, next_node):
                return hops, route

    # Kein vorberechneter Pfad konnte das Ziel erreichen.
    return -1, route


def cleanDfsEdges(dfs_edges):
    """Entfernt DFS-Hilfskanten, die keine echten Routingschritte darstellen."""
    return [
        (node, next_node, label)
        for node, next_node, label in dfs_edges
        if label != "nontree" and node != next_node
    ]


def chooseEndpoints(g, rng):
    """Wählt zufällig verbundene, aber nicht direkt benachbarte Endpunkte.

    Nicht benachbarte Endpunkte verhindern, dass eine direkte Kante das
    gesamte Mehrpfad-Routing trivial macht.
    """
    candidates = [
        (source, destination)
        for source, destination in combinations(g.nodes, 2)
        if not g.has_edge(source, destination) and nx.has_path(g, source, destination)
    ]
    if not candidates:
        raise nx.NetworkXNoPath("No connected, non-adjacent endpoint pair exists.")
    return rng.choice(candidates)


def createGraph(graph_type, no_nodes, graph_param, seed):
    """Erzeugt einen synthetischen Graphen für einen Experimentlauf."""
    if graph_type == "random_regular":
        # graph_param ist hier der Grad jedes Knotens.
        return nx.random_regular_graph(int(graph_param), no_nodes, seed=seed)
    if graph_type == "erdos_renyi":
        # graph_param ist hier die unabhängige Wahrscheinlichkeit jeder Kante.
        return nx.erdos_renyi_graph(no_nodes, graph_param, seed=seed)
    raise ValueError("Unknown graph type: {}".format(graph_type))


def loadGraphML(graphml_path):
    """Lädt eine feste Real-World-Topologie aus einer GraphML-Datei."""
    return nx.Graph(nx.read_graphml(graphml_path))


def selectFailures(
    g,
    source,
    destination,
    failure_type,
    failure_model,
    nr_failures,
    failure_start,
    failure_drop,
    rng,
):
    """Erzeugt Ausfälle passend zur Kombination aus Typ und Modell.

    Rückgabewert ist immer ein Paar:
    - failed_edges: vom Routing zu sperrende Kanten
    - failed_nodes: ursprünglich ausgefallene Knoten für die CSV-Auswertung

    Bei Knotenausfällen werden zusätzlich alle inzidenten Kanten gesperrt.
    """
    if failure_model == "random":
        if failure_type == "link":
            # Wählt unabhängige Kanten gleichverteilt aus dem gesamten Graphen.
            failed_edges = rng.sample(list(g.edges), min(nr_failures, g.number_of_edges()))
            return failed_edges, []

        if failure_type == "node":
            # Quelle und Ziel werden bei Knotenausfällen immer geschützt.
            candidates = [node for node in g.nodes if node not in (source, destination)]
            failed_nodes = rng.sample(candidates, min(nr_failures, len(candidates)))
            return nodeFailuresToEdgeFailures(g, failed_nodes), failed_nodes

    if failure_model == "clustered":
        if failure_type == "link":
            # Clustered Link Failures breiten sich vom Zielknoten aus.
            failed_edges = getClusteredLinkFailures(
                g,
                destination,
                failure_start,
                failure_drop,
                rng,
            )
            return failed_edges, []

        if failure_type == "node":
            # Clustered Node Failures beginnen bei den Nachbarn des Zielknotens.
            failed_nodes = getClusteredNodeFailures(
                g,
                source,
                destination,
                failure_start,
                failure_drop,
                rng,
            )
            return nodeFailuresToEdgeFailures(g, failed_nodes), failed_nodes

    raise ValueError(
        "Unknown failure type/model combination: {}/{}".format(
            failure_type,
            failure_model,
        )
    )


def getTrueShortestPathLength(g, source, destination, failed_edges):
    """Berechnet die kürzeste Route im Restgraphen nach Anwendung der Ausfälle.

    Dieser Wert dient als Referenzwert für die Stretch-Kennzahl.
    """
    graph_after_failures = g.copy()
    graph_after_failures.remove_edges_from(failed_edges)
    try:
        return nx.shortest_path_length(graph_after_failures, source, destination)
    except nx.NetworkXNoPath:
        return -1


def calculateStretch(hops, shortest_path_length):
    """Berechnet die zusätzlichen Hops gegenüber dem kürzesten Pfad.

    Bei einem erfolglosen Routing oder einem getrennten Graphen bleibt das
    CSV-Feld leer, weil dann kein sinnvoller Stretch existiert.
    """
    if hops == -1 or shortest_path_length == -1:
        return ""
    return hops - shortest_path_length


def formatCsvParam(value):
    """Formatiert einen Parameter für einen stabilen, lesbaren Dateinamen."""
    if value == 0:
        return "0"
    return str(value)


def createExperimentRow(
    rep,
    g,
    source,
    destination,
    failure_type,
    failure_model,
    fail_factor,
    failure_start,
    failure_drop,
    rng,
    graph_type,
    graph_param,
    graph_name="",
    graphml_path="",
):
    """Führt einen einzelnen EDP-/NDP-Vergleich aus und erzeugt eine CSV-Zeile."""
    # Beide Algorithmen werden auf demselben Graphen und denselben Endpunkten verglichen.
    edge_disjoint_paths = getEdgeDisjointPaths(g, source, destination)
    node_disjoint_paths = getNodeDisjointPaths(g, source, destination)

    # Random Failures skalieren die Anzahl der Ausfälle mit der NDP-Anzahl.
    # Bei Clustered Failures wird dieser Wert nicht verwendet; dort bestimmen
    # failure_start und failure_drop die schichtweise Auswahl.
    nr_failures = int(round(max(len(node_disjoint_paths) - 1, 0) * fail_factor))
    failed_edges, failed_nodes = selectFailures(
        g,
        source,
        destination,
        failure_type,
        failure_model,
        nr_failures,
        failure_start,
        failure_drop,
        rng,
    )

    # Die kürzeste Route nach den Ausfällen ist die Referenz für den Stretch.
    shortest_path_length = getTrueShortestPathLength(g, source, destination, failed_edges)

    # EDP und NDP erhalten exakt dieselben ausgefallenen Kanten.
    hops_edp, _, _, _ = kResilienceEdgeDisjointPaths(source, destination, failed_edges, g)
    hops_ndp, _, _, _ = kResiliencePaths(source, destination, failed_edges, g)

    # Leere Felder kennzeichnen Parameter, die für diese Konfiguration nicht gelten.
    return {
        "rep": rep,
        "failureType": failure_type,
        "failureModel": failure_model,
        "nrNodes": g.number_of_nodes(),
        "nrEdges": g.number_of_edges(),
        "graphType": graph_type,
        "graphParam": graph_param,
        "graphName": graph_name,
        "graphMLPath": str(graphml_path) if graphml_path else "",
        "degree": graph_param if graph_type == "random_regular" else "",
        "edgeProb": graph_param if graph_type == "erdos_renyi" else "",
        "source": source,
        "destination": destination,
        "nrEDPs": len(edge_disjoint_paths),
        "nrNDPs": len(node_disjoint_paths),
        "failFactor": fail_factor if failure_model == "random" else "",
        "failureStart": failure_start if failure_model == "clustered" else "",
        "failureDrop": failure_drop if failure_model == "clustered" else "",
        # Bei Link-Failures zählt nrFails die ausgefallenen Kanten.
        "nrFails": len(failed_edges) if failure_type == "link" else len(failed_nodes),
        # Bei Node-Failures zählt nrFails die ursprünglich ausgefallenen Knoten.
        "nrFailedNodes": len(failed_nodes),
        "spLength": shortest_path_length,
        "hopsEDP": hops_edp,
        "stretchEDP": calculateStretch(hops_edp, shortest_path_length),
        "hopsNDP": hops_ndp,
        "stretchNDP": calculateStretch(hops_ndp, shortest_path_length),
    }


def runExperiments(
    runs,
    failure_type,
    failure_model="random",
    no_nodes=25,
    graph_type="random_regular",
    graph_param=None,
    degree=4,
    graphml_path=None,
    graph_name=None,
    fail_factor=1.0,
    failure_start=0.9,
    failure_drop=0.3,
    output_dir=None,
    seed=None,
):
    """Führt eine komplette Experimentkonfiguration aus und schreibt eine CSV.

    Eine Konfiguration besitzt genau einen Fehlertyp und einen Failure Factor
    beziehungsweise Failure Start. Jede Wiederholung erzeugt eine CSV-Zeile.
    Bei GraphML wird immer dieselbe Topologie verwendet; bei synthetischen
    Graphen wird pro Wiederholung eine neue Instanz erzeugt.
    """
    graph_template = None
    if graphml_path:
        # Real-World-Reihen verwenden für alle Wiederholungen dieselbe Topologie.
        graph_template = loadGraphML(graphml_path)
        graph_type = "graphml"
        no_nodes = graph_template.number_of_nodes()
        graph_name = graph_name or Path(graphml_path).stem
        graph_param = graph_name
    elif graph_param is None:
        graph_param = degree

    # Getrennte Zufallsgeneratoren verhindern, dass die Ausfallauswahl die
    # spätere Graph- und Endpunktauswahl beeinflusst.
    graph_rng = random.Random(seed)
    failure_seed = None if seed is None else seed + 1
    failure_rng = random.Random(failure_seed)

    if output_dir is None:
        output_dir = "output_ndp_edp_{}_failures_series".format(failure_model)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Der Dateiname speichert den jeweils variierten Experimentparameter.
    if failure_model == "random":
        csv_name = "ndp_edp_{}_ff{}.csv".format(
            failure_type,
            formatCsvParam(fail_factor),
        )
    else:
        csv_name = "ndp_edp_clustered_{}_fs{}_fd{}.csv".format(
            failure_type,
            formatCsvParam(failure_start),
            formatCsvParam(failure_drop),
        )
    csv_path = output_path / csv_name

    with open(csv_path, "w", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=CSV_FIELDNAMES)
        writer.writeheader()

        for rep in range(1, runs + 1):
            # Manche synthetischen Graphen besitzen keine geeigneten Endpunkte.
            # In diesem Fall werden maximal 100 neue Graphinstanzen versucht.
            for _ in range(100):
                if graph_template is not None:
                    graph = graph_template.copy()
                else:
                    graph = createGraph(
                        graph_type,
                        no_nodes,
                        graph_param,
                        seed=graph_rng.randint(0, 2**32 - 1),
                    )
                try:
                    source, destination = chooseEndpoints(graph, graph_rng)
                    row = createExperimentRow(
                        rep,
                        graph,
                        source,
                        destination,
                        failure_type,
                        failure_model,
                        fail_factor,
                        failure_start,
                        failure_drop,
                        failure_rng,
                        graph_type,
                        graph_param,
                        graph_name or "",
                        graphml_path or "",
                    )
                    writer.writerow(row)
                    break
                except nx.NetworkXException:
                    # Versucht eine neue Instanz, wenn keine gültige Route existiert.
                    continue
            else:
                raise RuntimeError("Could not create a valid experiment instance.")

    return str(csv_path)


def parseArgs(argv=None):
    """Definiert und liest alle Kommandozeilenparameter des Experimentgenerators."""
    parser = argparse.ArgumentParser(
        description="Generate EDP/NDP comparison CSVs for link and node failures."
    )
    parser.add_argument("--runs", type=int, default=100)
    parser.add_argument("--failure-type", choices=["link", "node", "both"], default="both")
    parser.add_argument(
        "--failure-model",
        choices=["random", "clustered"],
        default="random",
    )
    parser.add_argument("--nodes", type=int, default=25)
    parser.add_argument(
        "--graph-type",
        choices=["random_regular", "erdos_renyi"],
        default="random_regular",
    )
    parser.add_argument("--degree", type=int, default=4)
    parser.add_argument(
        "--p",
        type=float,
        default=None,
        help="Edge probability for Erdos-Renyi graphs.",
    )
    parser.add_argument(
        "--graphml",
        default=None,
        help="GraphML input for a fixed real-world topology.",
    )
    parser.add_argument(
        "--graph-name",
        default=None,
        help="Optional label stored for a GraphML topology.",
    )
    parser.add_argument(
        "--fail-factor",
        type=float,
        nargs="+",
        default=[0.0, 0.5, 1.0, 1.5, 2.0],
        help="One or more factors multiplied with the number of NDPs minus one.",
    )
    parser.add_argument(
        "--failure-start",
        type=float,
        nargs="+",
        default=[0.9],
        help="One or more initial layer percentages for clustered failures.",
    )
    parser.add_argument(
        "--failure-drop",
        type=float,
        default=0.3,
        help="Percentage decrease per expanded layer for clustered failures.",
    )
    parser.add_argument("--output-dir", default=None)
    parser.add_argument("--seed", type=int, default=None)
    return parser.parse_args(argv)


def runFromArgs(args):
    """Uebersetzt Kommandozeilenparameter in einzelne Experimentkonfigurationen.

    Für --failure-type both werden Link- und Node-Reihen erzeugt. Mehrere
    Failure Factors oder Failure Starts erzeugen jeweils eine eigene CSV.
    Da jede Konfiguration denselben Seed erhält, werden Graph- und Endpunktwahl
    über die Parameterreihe hinweg möglichst konsistent gehalten.
    """
    failure_types = ["link", "node"] if args.failure_type == "both" else [args.failure_type]

    # Bestimmt den graphabhängigen Parameter: Name, Kantenwahrscheinlichkeit
    # oder Grad eines random-regulaeren Graphen.
    if args.graphml:
        graph_param = args.graph_name or Path(args.graphml).stem
    elif args.graph_type == "erdos_renyi":
        if args.p is None:
            raise ValueError("--p is required for Erdos-Renyi graphs.")
        graph_param = args.p
    else:
        graph_param = args.degree

    # Random- und Clustered-Modelle variieren unterschiedliche Parameter.
    if args.failure_model == "random":
        configurations = [
            {"fail_factor": fail_factor}
            for fail_factor in args.fail_factor
        ]
    else:
        configurations = [
            {"failure_start": failure_start}
            for failure_start in args.failure_start
        ]

    return [
        runExperiments(
            runs=args.runs,
            failure_type=failure_type,
            failure_model=args.failure_model,
            no_nodes=args.nodes,
            graph_type=args.graph_type,
            graph_param=graph_param,
            degree=args.degree,
            graphml_path=args.graphml,
            graph_name=args.graph_name,
            fail_factor=configuration.get("fail_factor", 1.0),
            failure_start=configuration.get("failure_start", 0.9),
            failure_drop=args.failure_drop,
            output_dir=args.output_dir,
            seed=args.seed,
        )
        for failure_type in failure_types
        for configuration in configurations
    ]


if __name__ == "__main__":
    # Schreibt für jede erzeugte Konfiguration den Pfad der CSV auf die Konsole.
    for output in runFromArgs(parseArgs()):
        print("wrote", output)
