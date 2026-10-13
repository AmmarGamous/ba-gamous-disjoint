Schritt 3: Node-Disjoint Paths (NDPs)

In Schritt 3 wird der Pfadalgorithmus aus der Reproduktion so erweitert, 
dass neben Edge-Disjoint Paths (EDPs) auch Node-Disjoint Paths (NDPs) untersucht werden. 
NDPs dürfen Quelle und Ziel gemeinsam verwenden, aber keine inneren Knoten teilen.
Die Experimente vergleichen EDP und NDP immer auf derselben Instanz:
- gleicher Graph
- gleiche Quelle und gleiches Ziel
- gleiche ausgefallene Links oder Knoten
Dadurch sind Resilience, Hops und Stretch direkt vergleichbar.

Zentrale Dateien:
- src/kResiliencePaths.py
  Implementiert NDP/EDP-Routing, Failure-Modelle, Graphgeneratoren, GraphML-Laden und CSV-Erzeugung.
- evaluation/notebooks/ndp_edp_random_runs1000.ipynb
  Wertet alle synthetischen Random-Graph-Reihen aus. 
  Dazu gehören die frühen Random-Regular-Piloten, die paper-nahen Pilot5-Reihen und die vollständigen 1000-Run-Reihen.
- evaluation/notebooks/ndp_edp_real_world_runs1000.ipynb
  Wertet die Pilot5- und 1000-Run-Reihen auf ATT-MPLS, Cogentco und Oteglobe aus.
- evaluation/test_node_disjoint_paths.py
  Testet NDP-Eigenschaft, Routingverhalten, Failure-Modelle, CSV-Erzeugung, GraphML-Laden und gepaarte Instanzen.

Detailprotokolle:
- Dokumentation/kResiliencePaths-Protokoll.txt
- Dokumentation/test_node_disjoint_paths-Protokoll.txt
- Dokumentation/ndp_edp_random_runs1000-Protokoll.txt
- Dokumentation/ndp_edp_real_world_runs1000-Protokoll.txt

Die README beschreibt nur den Überblick und die Protokolle erklären jeweils den
genauen Aufbau, die Eingaben, die Ausgaben und die wichtigsten Prüfpunkte.

Implementierter Algorithmus:
Die Datei src/kResiliencePaths.py enthält 23 dokumentierte Funktionen.

Wichtige Funktionen:
- getNodeDisjointPaths(...)
  Berechnet NDPs mit networkx.node_disjoint_paths(...).

- getEdgeDisjointPaths(...)
  Berechnet EDPs mit networkx.edge_disjoint_paths(...).

- kResiliencePaths(...)
  Führt das Routing über NDPs aus.

- kResilienceEdgeDisjointPaths(...)
  Führt das Routing über EDPs als Baseline aus.

- routeDisjointPaths(...)
  Gemeinsame Routinglogik für NDP und EDP.

- selectFailures(...)
  Erzeugt Random oder Clustered Link-/Node-Failures.

- runExperiments(...)
  Schreibt die Experiment-CSV-Dateien.

Failure-Modelle:
Random Failures:
Die Anzahl der Ausfälle wird aus der NDP-Anzahl abgeleitet:
nrFails = round((nrNDPs - 1) * failFactor)
Der Failure Factor ist daher die x-Achse für Random-Failure-Plots.
Clustered Failures:
Clustered Link Failures starten bei den inzidenten Kanten des Zielknotens.
Clustered Node Failures starten bei den Nachbarknoten des Zielknotens.
Quelle und Ziel werden bei Node Failures geschützt.
failureStart bestimmt den Anteil in der ersten Schicht.
failureDrop reduziert diesen Anteil pro weiterer Schicht.
Die tatsächliche Ausfallanzahl hängt von der lokalen Graphstruktur ab. 
Deshalb wird nrFails in den CSV-Dateien gespeichert und im Notebook mit ausgewertet.

Graphen:
Synthetische Random Graphs:
- frühe Random-Regular-Piloten mit n=25 und Grad 4
- paper-nahe Erdos-Renyi-Graphen, im Notebook und in den Plots als
  Random Graphs bezeichnet:
  - n=25, p=0.15
  - n=50, p=0.15
  - n=100, p=0.02
Real-World Graphs:
- ATT-MPLS: 25 Knoten, 56 Kanten
- Cogentco: 197 Knoten, 243 Kanten
- Oteglobe: 93 Knoten, 103 Kanten
Die GraphML-Dateien liegen unter:
data/topology_zoo

CSV-Erzeugung:
Die CSV-Dateien werden ausschließlich von src/kResiliencePaths.py erzeugt.
Die Notebooks lesen nur vorhandene CSV-Dateien und erstellen Plots.
Wichtige CSV-Spalten:
- failureType: link oder node
- failureModel: random oder clustered
- graphType, graphParam, graphName, graphMLPath
- source, destination
- nrEDPs, nrNDPs
- failFactor oder failureStart/failureDrop
- nrFails, nrFailedNodes
- spLength
- hopsEDP, stretchEDP
- hopsNDP, stretchNDP

Auswertungsnotebooks:
Random-Notebook:
evaluation/notebooks/ndp_edp_random_runs1000.ipynb
Eingelesene Daten:
- Random-Regular-Piloten: 2 Ordner, 18 CSVs, 1.800 Zeilen
- paper-nahe Pilot5-Reihen: 6 Ordner, 48 CSVs, 240 Zeilen
- paper-nahe 1000-Run-Reihen: 6 Ordner, 230 CSVs, 230.000 Zeilen
Ausgabeordner:
evaluation/output/ndp_edp_random_runs1000
Erzeugte Plots:
10 PNG-Dateien
Real-World-Notebook:
evaluation/notebooks/ndp_edp_real_world_runs1000.ipynb
Eingelesene Daten:
- Pilot5-Reihen: 6 Ordner, 36 CSVs, 180 Zeilen
- 1000-Run-Reihen: 6 Ordner, 102 CSVs, 102.000 Zeilen
Ausgabeordner:
evaluation/output/ndp_edp_real_world_runs1000
Erzeugte Plots:
8 PNG-Dateien

Serverbefehle:
Die Befehle für die vollständigen Random-Graph-Reihen liegen unter:
Dokumentation/server_commands_paper_erdos_renyi.txt

Die Befehle für die vollständigen Real-World-Reihen liegen unter:
Dokumentation/server_commands_real_world.txt

Hinweis:
Die Dateinamen behalten bei den synthetischen Graphen den Begriff erdos_renyi,
weil das der technische Graphgenerator ist. Im Notebook und in den Plots wird
für die Nähe zum Paper der Begriff Random Graphs verwendet.

Validierung
Der aktuelle Stand wurde mit 19 Unit-Tests geprüft:
python -m unittest discover -s schritt3_knoten_disjunkte_pfade/evaluation -p "test_*.py" -v

Geprüft wird unter anderem:
- NDPs teilen keine inneren Knoten.
- EDP und NDP werden auf derselben Instanz verglichen.
- Link und Node Failures werden korrekt behandelt.
- Clustered Failures speichern failureStart und failureDrop.
- Erdos-Renyi- und GraphML-Metadaten werden korrekt in CSVs geschrieben.
- Parameterreihen verwenden gepaarte Graphen und Endpunkte.

Aktueller Abschluss
Schritt 3 erfüllt die geforderte Erweiterung:
- NDPs sind implementiert.
- EDP bleibt als Vergleichsbasis erhalten.
- Random und Clustered Link Failures sind umgesetzt.
- Random und Clustered Node Failures sind umgesetzt.
- Random-Graph- und Real-World-Experimente wurden als CSV erzeugt.
- Die finalen Notebooks lesen die CSVs und erzeugen die Plots.