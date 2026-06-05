Schritt 2: Node/Vertex Failures

In diesem Schritt wurden die Experimente aus Schritt 1 von Link/Edge Failures auf Node/Vertex
Failures übertragen. Die fachlichen Routingalgorithmen wurden dabei nicht neu entworfen.
Weiterhin betrachtet werden:
- Edge-disjoint paths
- One Tree
- Multiple Trees
Der zentrale Unterschied liegt im Fehlermodell. Ein ausgefallener Knoten wird intern als
Ausfall aller inzidenten Kanten dieses Knotens modelliert. Dadurch kann die bestehende
Routinglogik weiterverwendet werden, während die Experimente nun Knotenausfälle
beschreiben.

Zentrale Dateien:
src/kResilienceTrees.py:
Diese Datei erzeugt die CSV-Dateien für Node Failures. Sie enthält die neuen Hilfsfunktionen
für Random Node Failures, Clustered Node Failures und die Umwandlung von Knotenausfällen in
Kantenausfälle. Die CSV-Ausgabe wurde um nrFailedNodes erweitert.

evaluation/notebooks/node_failure_random_graphs_paper.ipynb:
Dieses Notebook enthält die Paper-nahe Auswertung für synthetische Erdos-Renyi-Graphen.
Es liest vorhandene runs1000-CSV-Dateien ein und erstellt die finalen Plots.

evaluation/notebooks/node_failure_real_world_paper.ipynb:
Dieses Notebook enthält die Paper-nahe Auswertung für Real-World-Graphen aus dem
Topology-Zoo-Kontext. Dieses Notebook importiert die mit kResilienceTrees.py erzeugten Ergebnisdateien.

Separate Protokolle:
Zu den wichtigsten Schritt-2-Artefakten wurden eigene Protokolldateien angelegt:
- Dokumentation/kResilienceTrees.txt
- Dokumentation/node_failure_random_graphs_paper.txt
- Dokumentation/node_failure_real_world_paper.txt
- Dokumentation/test_node_failures.txt
und data/topology_zoo/README.txt
Diese Dateien dokumentieren Ziel, Änderungen, Kontrollen und Ergebnisse der jeweiligen
Komponente.

Fachliches Ergebnis
Bei Random Node Failures sinkt die Resilience mit steigendem Failure-Faktor. Multiple Trees
erreicht meist die hoechste Resilience, gefolgt von One Tree und EDPs. Der Abstand ist bei
Random Node Failures sichtbar, aber meist moderat.

Bei Clustered Node Failures fällt die Resilience deutlich staerker ab. Diese Ausfälle sind
kritischer, weil sie lokal in der Umgebung des Zielknotens konzentriert sind. In diesen
Szenarien wird der Vorteil von Multiple Trees gegenüber EDPs deutlicher sichtbar.

Multiple Trees benötigt jedoch häufig mehr Hops. Das bedeutet, dass die Methode zwar in mehr
Fällen noch eine gültige Route findet, diese Route aber oft länger ist. Die durchschnittlichen
Hops müssen deshalb immer gemeinsam mit der Resilience interpretiert werden.
