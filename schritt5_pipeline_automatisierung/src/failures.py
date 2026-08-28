"""Link- und Knotenausfallmodelle für Schritt 4."""

import math


# Schritt-7-Erweiterungspunkt: neue Failure-Modelle zuerst hier beschreiben.
# Die konkrete Link-/Node-Auswahl danach in select_failures(...) ergänzen.
FAILURE_MODEL_SPECS = {
    "random": {
        "parameter": "fail_factor",
        "csv_prefix": "random",
        "uses_failure_count": True,
        "uses_cluster_parameters": False,
    },
    "clustered": {
        "parameter": "failure_start",
        "csv_prefix": "clustered",
        "uses_failure_count": False,
        "uses_cluster_parameters": True,
    },
}


def failure_model_spec(failure_model):
    """Liefert zentrale Metadaten für ein Failure-Modell."""
    try:
        return FAILURE_MODEL_SPECS[failure_model]
    except KeyError as exc:
        raise ValueError(f"Unknown failure model: {failure_model}") from exc


def failure_parameter_key(failure_model):
    """Liefert den Parameter-Schlüssel für ein Failure-Modell."""
    return failure_model_spec(failure_model)["parameter"]


def failure_model_csv_prefix(failure_model):
    """Liefert den Dateinamen-Präfix für ein Failure-Modell."""
    return failure_model_spec(failure_model)["csv_prefix"]


def uses_failure_count(failure_model):
    """Gibt zurück, ob ein Modell eine feste Anzahl Ausfälle verwendet."""
    return bool(failure_model_spec(failure_model)["uses_failure_count"])


def uses_cluster_parameters(failure_model):
    """Gibt zurück, ob ein Modell `failureStart` und `failureDrop` nutzt."""
    return bool(failure_model_spec(failure_model)["uses_cluster_parameters"])


def edge_key(edge):
    """Normalisiert eine ungerichtete Kante für Mengenvergleiche."""
    return frozenset(edge)


def node_sort_key(node):
    """Liefert einen stabilen Sortierschlüssel für Graphknoten."""
    return (node.__class__.__module__, node.__class__.__qualname__, str(node))


def stable_edge_tuple(edge):
    """Normalisiert eine ungerichtete Kante mit stabiler Endpunkt-Reihenfolge."""
    return tuple(sorted(tuple(edge), key=node_sort_key))


def edge_sort_key(edge):
    """Liefert einen stabilen Sortierschlüssel für ungerichtete Kanten."""
    return tuple(node_sort_key(node) for node in stable_edge_tuple(edge))


def sorted_edges(edges):
    """Sortiert Kanten stabil und normalisiert ihre Richtung."""
    return [stable_edge_tuple(edge) for edge in sorted(edges, key=edge_sort_key)]


def sorted_edge_sequence(edges):
    """Sortiert Kanten stabil, behält aber ihre aktuelle Richtung."""
    return [tuple(edge) for edge in sorted(edges, key=edge_sort_key)]


def unique_sorted_nodes(nodes):
    """Entfernt Duplikate und sortiert Knoten stabil."""
    return sorted(dict.fromkeys(nodes), key=node_sort_key)


def node_failures_to_edges(graph, failed_nodes):
    """Wandelt ausgefallene Knoten in alle inzidenten Kanten um."""
    failed = {edge_key(edge) for node in failed_nodes for edge in graph.edges(node)}
    return sorted_edges(failed)


def validate_cluster_parameters(failure_start, failure_drop):
    """Prüft die Parameter des Clustered-Failure-Modells."""
    if not 0.0 < failure_start <= 1.0:
        raise ValueError(
            "failure_start must be greater than 0 and less than or equal to 1"
        )

    if not 0.0 < failure_drop <= 1.0:
        raise ValueError(
            "failure_drop must be greater than 0 and less than or equal to 1"
        )


def clustered_link_failures(
    graph, source, destination, failure_start, failure_drop, rng
):
    """Wählt Linkausfälle schichtweise vom Zielknoten nach außen.

    Kanten zu `source` sind in allen Schichten geschützt. Nur die erste Schicht
    enthält direkte Kanten zu `destination`. Beim Aufbau aller weiteren
    Schichten werden diese Kanten ausgeschlossen, damit das Ziel nicht erneut
    als Kandidat der nach außen laufenden Ausbreitung dient.
    """
    validate_cluster_parameters(failure_start, failure_drop)
    failed = []
    seen_failed = set()
    incidents = [
        edge
        for edge in sorted_edge_sequence(graph.edges(destination))
        if source not in edge
    ]
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
            for edge in sorted_edge_sequence(graph.edges(outer_node)):
                if source in edge or destination in edge:
                    continue
                key = edge_key(edge)
                if key not in seen_next:
                    next_incidents.append(edge)
                    seen_next.add(key)
        incidents = sorted_edge_sequence(next_incidents)
        probability -= failure_drop
    return failed


def clustered_node_failures(
    graph, source, destination, failure_start, failure_drop, rng
):
    """Wählt Knotenausfälle schichtweise um d und schützt s sowie d."""
    validate_cluster_parameters(failure_start, failure_drop)
    failed = []
    candidates = unique_sorted_nodes(
        node for node in graph.neighbors(destination)
        if node not in (source, destination)
    )
    probability = failure_start

    while probability > 0.0 and candidates:
        count = math.floor(probability * len(candidates))
        failed.extend(rng.sample(candidates, count))
        failed = list(dict.fromkeys(failed))
        next_candidates = []
        for node in candidates:
            for neighbor in sorted(graph.neighbors(node), key=node_sort_key):
                if neighbor not in (source, destination) and neighbor not in failed:
                    next_candidates.append(neighbor)
        candidates = unique_sorted_nodes(next_candidates)
        probability -= failure_drop
    return unique_sorted_nodes(failed)


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
    # Schritt-7-Erweiterungspunkt: neue Failure-Modelle hier ausführen.
    failure_model_spec(failure_model)
    if failure_model == "random" and failure_type == "link":
        edges = sorted_edges(graph.edges)
        return rng.sample(edges, min(nr_failures, len(edges))), []
    if failure_model == "random" and failure_type == "node":
        candidates = unique_sorted_nodes(
            node for node in graph if node not in (source, destination)
        )
        nodes = rng.sample(candidates, min(nr_failures, len(candidates)))
        return node_failures_to_edges(graph, nodes), unique_sorted_nodes(nodes)
    if failure_model == "clustered" and failure_type == "link":
        return (
            clustered_link_failures(
                graph, source, destination, failure_start, failure_drop, rng
            ),
            [],
        )
    if failure_model == "clustered" and failure_type == "node":
        nodes = clustered_node_failures(
            graph, source, destination, failure_start, failure_drop, rng
        )
        return node_failures_to_edges(graph, nodes), nodes
    raise ValueError(f"Unknown failure combination: {failure_type}/{failure_model}")
