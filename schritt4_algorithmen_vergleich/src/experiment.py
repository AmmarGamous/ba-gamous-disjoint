"""Experimentgenerator für alle sechs Algorithmen und vier Failure-Arten."""

import argparse
import csv
from itertools import combinations
from pathlib import Path
import random
from typing import Iterable, Sequence

import networkx as nx

from failures import select_failures
from routing_algorithms import ALGORITHMS, get_disjoint_paths, run_algorithms


CSV_FIELDNAMES = [
    "rep",
    "algorithm",
    "pathType",
    "structureType",
    "failureType",
    "failureModel",
    "nrNodes",
    "nrEdges",
    "graphType",
    "graphParam",
    "graphName",
    "source",
    "destination",
    "nrPaths",
    "nrFails",
    "nrFailedNodes",
    "failFactor",
    "failureStart",
    "failureDrop",
    "spLength",
    "success",
    "hops",
    "stretch",
]


def shortest_path_after_failures(graph, source, destination, failed_edges):
    """Berechnet die kürzeste Restpfadlänge nach Entfernen der Ausfallkanten."""
    remaining = graph.copy()
    remaining.remove_edges_from(failed_edges)
    try:
        return nx.shortest_path_length(remaining, source, destination)
    except nx.NetworkXNoPath:
        return -1


def create_instance_rows(
    rep: int,
    graph: nx.Graph,
    source,
    destination,
    failed_edges: Iterable[Sequence],
    failure_type: str,
    failure_model: str,
    failed_nodes: Iterable = (),
    algorithms: Iterable[str] = ALGORITHMS,
    graph_type: str = "",
    graph_param="",
    graph_name: str = "",
    fail_factor="",
    failure_start="",
    failure_drop="",
) -> list[dict]:
    """Erzeugt eine lange CSV-Zeile je Algorithmus derselben Instanz."""
    failed_edges = tuple(tuple(edge) for edge in failed_edges)
    failed_nodes = tuple(failed_nodes)
    shortest = shortest_path_after_failures(
        graph, source, destination, failed_edges
    )
    results = run_algorithms(
        graph, source, destination, failed_edges, algorithms=algorithms
    )

    rows = []
    for result in results:
        path_type, structure_type = result.algorithm.split("_", 1)
        rows.append(
            {
                "rep": rep,
                "algorithm": result.algorithm,
                "pathType": path_type,
                "structureType": structure_type,
                "failureType": failure_type,
                "failureModel": failure_model,
                "nrNodes": graph.number_of_nodes(),
                "nrEdges": graph.number_of_edges(),
                "graphType": graph_type,
                "graphParam": graph_param,
                "graphName": graph_name,
                "source": source,
                "destination": destination,
                "nrPaths": result.nr_paths,
                "nrFails": len(failed_nodes) if failure_type == "node" else len(failed_edges),
                "nrFailedNodes": len(failed_nodes),
                "failFactor": fail_factor,
                "failureStart": failure_start,
                "failureDrop": failure_drop,
                "spLength": shortest,
                "success": int(result.success),
                "hops": result.hops,
                "stretch": (
                    result.hops - shortest
                    if result.success and shortest >= 0
                    else ""
                ),
            }
        )
    return rows


def write_rows(csv_path, rows: Iterable[dict], append: bool = False) -> str:
    """Schreibt Ergebniszeilen im pipelinefreundlichen langen Format."""
    csv_path = Path(csv_path)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    mode = "a" if append else "w"
    write_header = not append or not csv_path.exists() or csv_path.stat().st_size == 0
    with csv_path.open(mode, newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=CSV_FIELDNAMES)
        if write_header:
            writer.writeheader()
        writer.writerows(rows)
    return str(csv_path)


def create_graph(graph_type, nodes, graph_param, seed):
    """Erzeugt einen synthetischen Graphen für eine Wiederholung."""
    if graph_type == "erdos_renyi":
        return nx.erdos_renyi_graph(nodes, graph_param, seed=seed)
    if graph_type == "random_regular":
        return nx.random_regular_graph(int(graph_param), nodes, seed=seed)
    raise ValueError(f"Unknown graph type: {graph_type}")


def choose_endpoints(graph, rng):
    """Wählt ein verbundenes, nicht direkt benachbartes s-d-Paar."""
    # Nur Paare innerhalb derselben Zusammenhangskomponente betrachten. Das
    # vermeidet bei größeren Real-World-Graphen eine Pfadsuche für jedes der
    # O(n^2) möglichen Knotenpaare.
    candidates = [
        pair
        for component in nx.connected_components(graph)
        for pair in combinations(component, 2)
        if not graph.has_edge(*pair)
    ]
    if not candidates:
        raise nx.NetworkXNoPath("No connected non-adjacent endpoint pair")
    return rng.choice(candidates)


def format_parameter(value):
    """Formatiert Parameterwerte stabil für Dateinamen."""
    return "0" if value == 0 else str(value)


def build_configurations(failure_types, failure_models, fail_factors, failure_starts):
    """Erzeugt alle Failure-Kombinationen mit ihren Parameterwerten."""
    configurations = []
    for failure_type in failure_types:
        for failure_model in failure_models:
            values = fail_factors if failure_model == "random" else failure_starts
            key = "fail_factor" if failure_model == "random" else "failure_start"
            configurations.extend(
                {
                    "failure_type": failure_type,
                    "failure_model": failure_model,
                    key: value,
                }
                for value in values
            )
    return configurations


def configuration_filename(configuration, failure_drop):
    """Leitet aus einer Konfiguration den passenden CSV-Dateinamen ab."""
    failure_type = configuration["failure_type"]
    failure_model = configuration["failure_model"]
    if failure_model == "random":
        return f"algorithms_random_{failure_type}_ff{format_parameter(configuration['fail_factor'])}.csv"
    return (
        f"algorithms_clustered_{failure_type}_fs"
        f"{format_parameter(configuration['failure_start'])}_fd"
        f"{format_parameter(failure_drop)}.csv"
    )


def completed_rep_prefix(csv_path, algorithms):
    """Liefert die lückenlose Anzahl vollständiger Reps einer CSV."""
    csv_path = Path(csv_path)
    if not csv_path.exists() or csv_path.stat().st_size == 0:
        return 0
    expected_algorithms = set(algorithms)
    rows_by_rep = {}
    with csv_path.open(newline="", encoding="utf-8") as csv_file:
        for row in csv.DictReader(csv_file):
            try:
                rep = int(row["rep"])
            except (KeyError, TypeError, ValueError):
                return 0
            rows_by_rep.setdefault(rep, []).append(row)

    completed = 0
    while True:
        rep = completed + 1
        rows = rows_by_rep.get(rep, [])
        if (
            len(rows) != len(expected_algorithms)
            or {row.get("algorithm") for row in rows} != expected_algorithms
        ):
            return completed
        completed = rep


def truncate_to_completed_reps(csv_path, completed_reps):
    """Entfernt beim Resume eine unvollständige letzte Wiederholung."""
    csv_path = Path(csv_path)
    if not csv_path.exists():
        return
    with csv_path.open(newline="", encoding="utf-8") as csv_file:
        rows = [
            row
            for row in csv.DictReader(csv_file)
            if int(row["rep"]) <= completed_reps
        ]
    write_rows(csv_path, rows, append=False)


def run_experiment_series(
    runs,
    failure_types,
    failure_models,
    algorithms=ALGORITHMS,
    graph_type="erdos_renyi",
    nodes=25,
    graph_param=0.15,
    graphml_path=None,
    graph_name="",
    fail_factors=(0.8,),
    failure_starts=(0.9,),
    failure_drop=0.3,
    output_dir="output",
    seed=None,
    resume=False,
):
    """Erzeugt gepaarte Reihen; jede CSV enthält sechs Zeilen je Instanz."""
    configurations = build_configurations(
        failure_types, failure_models, fail_factors, failure_starts
    )
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        tuple(configuration.items()): output_dir
        / configuration_filename(configuration, failure_drop)
        for configuration in configurations
    }
    if not configurations:
        raise ValueError("At least one experiment configuration is required")

    if resume:
        completed_reps = min(
            completed_rep_prefix(csv_path, algorithms)
            for csv_path in paths.values()
        )
        for csv_path in paths.values():
            truncate_to_completed_reps(csv_path, completed_reps)
        if completed_reps:
            print(f"resume: {completed_reps} complete repetitions found")
        if completed_reps >= runs:
            return [str(path) for path in paths.values()]
    else:
        completed_reps = 0
        for csv_path in paths.values():
            if csv_path.exists():
                csv_path.unlink()

    master_rng = random.Random(seed)
    loaded_graph = nx.Graph(nx.read_graphml(graphml_path)) if graphml_path else None
    effective_graph_type = "graphml" if graphml_path else graph_type
    effective_param = graph_name or Path(graphml_path).stem if graphml_path else graph_param

    for rep in range(1, runs + 1):
        for _ in range(1000):
            graph_seed = master_rng.randrange(2**32)
            graph = loaded_graph.copy() if loaded_graph is not None else create_graph(
                graph_type, nodes, graph_param, graph_seed
            )
            try:
                source, destination = choose_endpoints(graph, master_rng)
                edps = get_disjoint_paths(graph, source, destination, "edp")
                ndps = get_disjoint_paths(graph, source, destination, "ndp")
                break
            except nx.NetworkXException:
                continue
        else:
            raise RuntimeError("Could not create a valid experiment instance")

        # Auch übersprungene Reps werden oben rekonstruiert, damit der Zustand
        # des Master-RNG exakt dem ursprünglichen Lauf entspricht.
        if rep <= completed_reps:
            continue

        for configuration in configurations:
            failure_type = configuration["failure_type"]
            failure_model = configuration["failure_model"]
            fail_factor = configuration.get("fail_factor", "")
            failure_start = configuration.get("failure_start", "")
            # Link- und Node-Ausfälle skalieren mit ihrer passenden lokalen
            # Konnektivität; alle sechs Algorithmen erhalten dieselbe Auswahl.
            connectivity = len(edps) if failure_type == "link" else len(ndps)
            nr_failures = (
                round(max(connectivity - 1, 0) * fail_factor)
                if failure_model == "random"
                else 0
            )
            failure_rng = random.Random(
                f"{seed}:{rep}:{failure_type}:{failure_model}:"
                f"{fail_factor}:{failure_start}"
            )
            failed_edges, failed_nodes = select_failures(
                graph,
                source,
                destination,
                failure_type,
                failure_model,
                nr_failures,
                failure_start if failure_model == "clustered" else 0.0,
                failure_drop,
                failure_rng,
            )
            rows = create_instance_rows(
                rep,
                graph,
                source,
                destination,
                failed_edges,
                failure_type,
                failure_model,
                failed_nodes=failed_nodes,
                algorithms=algorithms,
                graph_type=effective_graph_type,
                graph_param=effective_param,
                graph_name=graph_name,
                fail_factor=fail_factor,
                failure_start=failure_start,
                failure_drop=failure_drop if failure_model == "clustered" else "",
            )
            write_rows(
                paths[tuple(configuration.items())],
                rows,
                append=True,
            )
    return [str(path) for path in paths.values()]


def parse_args(argv=None):
    """Parst die Kommandozeilenparameter für Server- und Pilotläufe."""
    parser = argparse.ArgumentParser(
        description="Run the six Step-4 routing algorithms on paired instances"
    )
    parser.add_argument("--runs", type=int, default=100)
    parser.add_argument("--algorithms", nargs="+", choices=ALGORITHMS, default=list(ALGORITHMS))
    parser.add_argument("--failure-type", choices=["link", "node", "both"], default="both")
    parser.add_argument("--failure-model", choices=["random", "clustered", "both"], default="both")
    parser.add_argument("--graph-type", choices=["erdos_renyi", "random_regular"], default="erdos_renyi")
    parser.add_argument("--nodes", type=int, default=25)
    parser.add_argument("--p", type=float, default=None)
    parser.add_argument("--degree", type=int, default=4)
    parser.add_argument("--graphml", default=None)
    parser.add_argument("--graph-name", default="")
    parser.add_argument("--fail-factor", type=float, nargs="+", default=[0.8])
    parser.add_argument("--failure-start", type=float, nargs="+", default=[0.9])
    parser.add_argument("--failure-drop", type=float, default=0.3)
    parser.add_argument("--output-dir", default="schritt4_algorithmen_vergleich/output")
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Continue a matching interrupted series from complete repetitions.",
    )
    return parser.parse_args(argv)


def run_from_args(args):
    """Übersetzt CLI-Argumente in den Aufruf der Experimentserie."""
    failure_types = ["link", "node"] if args.failure_type == "both" else [args.failure_type]
    failure_models = ["random", "clustered"] if args.failure_model == "both" else [args.failure_model]
    if args.graphml:
        graph_param = args.graph_name or Path(args.graphml).stem
    elif args.graph_type == "erdos_renyi":
        if args.p is None:
            raise ValueError("--p is required for Erdos-Renyi graphs")
        graph_param = args.p
    else:
        graph_param = args.degree
    return run_experiment_series(
        runs=args.runs,
        failure_types=failure_types,
        failure_models=failure_models,
        algorithms=args.algorithms,
        graph_type=args.graph_type,
        nodes=args.nodes,
        graph_param=graph_param,
        graphml_path=args.graphml,
        graph_name=args.graph_name,
        fail_factors=args.fail_factor,
        failure_starts=args.failure_start,
        failure_drop=args.failure_drop,
        output_dir=args.output_dir,
        seed=args.seed,
        resume=args.resume,
    )


if __name__ == "__main__":
    for output in run_from_args(parse_args()):
        print("wrote", output)
