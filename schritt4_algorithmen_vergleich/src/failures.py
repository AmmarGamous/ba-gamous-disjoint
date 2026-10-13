"""Link- und Knotenausfallmodelle für Schritt 4."""

import math


def edge_key(edge):
    """Normalisiert eine ungerichtete Kante für Mengenvergleiche."""
    return frozenset(edge)


def node_failures_to_edges(graph, failed_nodes):
    """Wandelt ausgefallene Knoten in alle inzidenten Kanten um."""
    failed = {edge_key(edge) for node in failed_nodes for edge in graph.edges(node)}
    return [tuple(edge) for edge in failed]


def validate_cluster_parameters(failure_start, failure_drop):
    """Prüft die Parameter des clustered Failure-Modells."""
    if not 0.0 <= failure_start <= 1.0:
        raise ValueError("failure_start must be between 0 and 1")
    if failure_drop <= 0.0:
        raise ValueError("failure_drop must be greater than 0")


def clustered_link_failures(graph, destination, failure_start, failure_drop, rng):
    """Wählt Linkausfälle schichtweise vom Zielknoten nach außen."""
    validate_cluster_parameters(failure_start, failure_drop)
    failed = []
    seen_failed = set()
    incidents = list(graph.edges(destination))
    probability = failure_start

    while probability > 0.0 and incidents:
        count = math.floor(probability * len(incidents))
        for edge in rng.sample(incidents, count):
            key = edge_key(edge)
            if key not in seen_failed:
                failed.append(edge)
                seen_failed.add(key)

        next_incidents = []
        seen_next = set()
        for _, outer_node in incidents:
            for edge in graph.edges(outer_node):
                key = edge_key(edge)
                if key not in seen_next:
                    next_incidents.append(edge)
                    seen_next.add(key)
        incidents = next_incidents
        probability -= failure_drop
    return failed


def clustered_node_failures(
    graph, source, destination, failure_start, failure_drop, rng
):
    """Wählt Knotenausfälle schichtweise um d und schützt s sowie d."""
    validate_cluster_parameters(failure_start, failure_drop)
    failed = []
    candidates = [
        node for node in graph.neighbors(destination)
        if node not in (source, destination)
    ]
    probability = failure_start

    while probability > 0.0 and candidates:
        count = math.floor(probability * len(candidates))
        failed.extend(rng.sample(candidates, count))
        failed = list(dict.fromkeys(failed))
        next_candidates = []
        for node in candidates:
            for neighbor in graph.neighbors(node):
                if neighbor not in (source, destination) and neighbor not in failed:
                    next_candidates.append(neighbor)
        candidates = list(dict.fromkeys(next_candidates))
        probability -= failure_drop
    return failed


def select_failures(
    graph,
    source,
    destination,
    failure_type,
    failure_model,
    nr_failures,
    failure_start,
    failure_drop,
    rng,
):
    """Wählt je nach Typ/Modell die Ausfälle und liefert Kanten plus Knoten."""
    if failure_model == "random" and failure_type == "link":
        edges = list(graph.edges)
        return rng.sample(edges, min(nr_failures, len(edges))), []
    if failure_model == "random" and failure_type == "node":
        candidates = [node for node in graph if node not in (source, destination)]
        nodes = rng.sample(candidates, min(nr_failures, len(candidates)))
        return node_failures_to_edges(graph, nodes), nodes
    if failure_model == "clustered" and failure_type == "link":
        return (
            clustered_link_failures(
                graph, destination, failure_start, failure_drop, rng
            ),
            [],
        )
    if failure_model == "clustered" and failure_type == "node":
        nodes = clustered_node_failures(
            graph, source, destination, failure_start, failure_drop, rng
        )
        return node_failures_to_edges(graph, nodes), nodes
    raise ValueError(f"Unknown failure combination: {failure_type}/{failure_model}")
