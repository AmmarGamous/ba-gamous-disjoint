Schritt 4: Vergleich von sechs Routingalgorithmen

Ziel
Schritt 4 bildet den Kern der Vergleichspipeline. Die TREE-Methodik aus
arXiv:2111.14123v1 wird für Edge-Disjoint Paths (EDPs) reproduziert und
analog auf Node-Disjoint Paths (NDPs) übertragen. Verglichen werden sechs
Verfahren:

- edp_paths
- edp_one_tree
- edp_multiple_trees
- ndp_paths
- ndp_one_tree
- ndp_multiple_trees

Die Bezeichnung der synthetischen Graphen orientiert sich in der Auswertung am Paper und
wird deshalb sichtbar als "Random Graphs" geführt.
Einige Datei- und Ordnernamen enthalten weiterhin "synthetic", damit vorhandene Pfade und Ausgaben stabil bleiben.

Paper-nahe Konstruktion
- EDPs beziehungsweise NDPs werden zuerst berechnet.
- Für die Baumkonstruktion werden die Pfade längste zuerst betrachtet.
- One Tree erweitert ausschließlich den längsten Pfad.
- Multiple Trees erweitert alle Pfade, beginnend mit dem längsten.
- Der Zielknoten gehört nicht zu den Bäumen.
- Algorithmus 3 (Truncation) entfernt alle Äste, die nicht zu einem Nachbarn des Zielknotens führen.
- Beim Routing werden die Ausgangsstrukturen kürzeste zuerst probiert.
- Das Routing ist ein nach der kürzesten Entfernung zu einem Ausgang geordnetes Depth-First Routing.
- One Tree priorisiert innerhalb seines Baumes den ursprünglichen Pfad.

NDP-Erweiterung
Das Paper definiert die Verfahren für EDPs. 
Die NDP-Varianten behalten Konstruktion, Trunkierung und Routing bei und 
tauschen nur die initiale Pfadberechnung gegen networkx.node_disjoint_paths aus. 
Diese Übertragung ist eine Erweiterung des Papers und wird in der Auswertung entsprechend bezeichnet.

Implementierungsübersicht

src/routing_algorithms.py
Diese Datei enthält den gemeinsamen Kern der sechs Routingverfahren.
Implementiert sind:

- RoutingStructure: speichert Pfade, Bäume, Exit-Knoten und den ursprünglichen Hauptpfad einer Routingstruktur.
- RoutingResult speichert Erfolg, Hops, Route, Anzahl Pfade und Anzahl Strukturen. 
   Der Stretch wird anschließend in experiment.py anhand der kürzesten Restpfadlänge berechnet und in die CSV geschrieben.
- ALGORITHMS: zentrale Liste der sechs implementierten Verfahren.
- get_disjoint_paths: berechnet EDPs oder NDPs abhängig vom Verfahren.
- build_structures: baut je nach Modus Pfad-, One-Tree- oder Multiple-Tree- Strukturen.
- truncate_tree: setzt die Trunkierung aus Algorithmus 3 des Papers um.
- route_structure: routet innerhalb einer einzelnen Struktur unter Beachtung der Ausfälle.
- route_algorithm: führt ein konkretes Verfahren aus.
- run_algorithms: führt mehrere Verfahren auf derselben Instanz aus.

src/failures.py
Diese Datei erzeugt die Ausfallmengen für die Experimente. Implementiert sind:

- Random Link Failures
- Random Node Failures
- Clustered Link Failures
- Clustered Node Failures
- Umwandlung von Node-Failures in betroffene Kanten für das Routing
- Validierung der Clustered-Failure-Parameter

Random Link Failures skalieren mit nrEDPs - 1, Random Node Failures analog mit nrNDPs - 1. 
Der Failure Factor multipliziert diesen Wert.
Eine so erzeugte Ausfallmenge wird unverändert für alle sechs Algorithmen verwendet.
Clustered Failures breiten sich vom Ziel aus; failureStart steuert die erste Schicht und
failureDrop die Abnahme pro weiterer Schicht.

src/experiment.py
Diese Datei enthält die Experiment-CLI und die CSV-Erzeugung. Implementiert sind:

- Erzeugung von Random Graphs über Erdos-Renyi-Parameter
- Einlesen von Real-World-Topologien aus GraphML
- Auswahl zusammenhängender Quelle-Ziel-Paare
- Aufbau aller Failure-Konfigurationen
- gemeinsames langes CSV-Format mit einer Zeile je Algorithmus und Instanz
- optional eingeschränkte Algorithmusauswahl über --algorithms
- --resume für unterbrochene Läufe
- stabile Ausgabeordner für lokale Pilotläufe und Serverläufe

Eine Instanz verwendet für alle ausgewählten Algorithmen denselben Graphen,
dieselben Endpunkte und dieselbe Ausfallmenge. 
Dadurch bleibt der Vergleich zwischen den Algorithmen fair.

evaluation/result_analysis.py
Diese Datei enthält die gemeinsame Auswertungslogik für die Notebooks. Implementiert sind:

- Laden mehrerer Ergebnisordner
- Aggregation der Rohdaten zu Resilience, Avg. Hops und Avg. Stretch
- Vollständigkeitsprüfung pro Graph, Failure-Typ, Failure-Modell,
  Failure-Parameter und Algorithmus
- Erzeugung einer Summary-CSV
- Erzeugung der finalen PNG- und SVG-Plots
- einheitliche X-Achse "Failure Rate"
- optionale Plot-Auswahl, damit Avg. Stretch separat erzeugt werden kann

evaluation/test_routing_algorithms.py
Diese Datei enthält deterministische Tests für den Schritt-4-Kern. Geprüft werden unter anderem:

- EDP- und NDP-Pfadberechnung
- One-Tree- und Multiple-Tree-Konstruktion
- Trunkierung
- Routing-Erfolg und Routing-Fehlschlag
- Random und Clustered Failures
- CSV-Erzeugung
- Resume-Verhalten bei unterbrochenen Reihen
- finale Analyse auf serverartigen Ergebnisdaten

Failure-Kombinationen
Alle Experimente unterstützen vier Failure-Kombinationen:

- Random Link Failures
- Random Node Failures
- Clustered Link Failures
- Clustered Node Failures

CLI-Beispiel
python schritt4_algorithmen_vergleich/src/experiment.py --runs 5 \
  --failure-type both --failure-model both \
  --graph-type erdos_renyi --nodes 25 --p 0.15 \
  --fail-factor 0.8 1.6 --failure-start 0.3 0.6 0.9 \
  --failure-drop 0.3 --seed 123 --resume \
  --output-dir schritt4_algorithmen_vergleich/output/pilot

Mit --algorithms können ein oder mehrere der sechs Verfahren ausgewählt werden. 
Ohne den Parameter laufen alle sechs.

Mit --resume wird eine unterbrochene passende Reihe fortgesetzt. 
Der Generator ermittelt den gemeinsamen lückenlosen Stand aller Konfigurationsdateien,
entfernt eine eventuell unvollständige letzte Wiederholung und 
rekonstruiert den Zufallszustand bis zum Fortsetzungspunkt. 
Für einen Resume müssen alle Parameter und der Seed identisch zum ursprünglichen Aufruf bleiben. 
Wenn eine Reihe bereits vollständig ist, wird sie nicht neu überschrieben.

Aktueller Umfang
Implementiert und angebunden sind:

- sechs Routingalgorithmen
- Konstruktion, Trunkierung und Routing
- alle vier Failure-Kombinationen
- Random Graphs und Real-World-GraphML-Topologien
- gepaarte Parameterreihen
- CSV-Erzeugung im langen Format
- Resume-Funktion für Serverläufe
- Pilotläufe
- finale 1000-Run-Auswertung
- Summary-CSV-Dateien
- PNG- und SVG-Plots
- getrennte Stretch-Auswertung
- Protokolldateien zu Modulen und Notebooks

Notebooks

evaluation/notebooks/synthetic_graphs_runs1000.ipynb
Hauptnotebook für Random Graphs. Es enthält zuerst einen 
Pilotabschnitt und danach die finale 1000-Run-Auswertung für:

- n = 25, p = 0.15
- n = 50, p = 0.15
- n = 100, p = 0.02

Der finale Abschnitt liest die Serverordner:

- schritt4_algorithmen_vergleich/output/server/synthetic_n25_p015
- schritt4_algorithmen_vergleich/output/server/synthetic_n50_p015
- schritt4_algorithmen_vergleich/output/server/synthetic_n100_p002

evaluation/notebooks/real_world_graphs_runs1000.ipynb
Hauptnotebook für die Real-World-Graphen. Es enthält zuerst einen 
Pilotabschnitt und danach die finale 1000-Run-Auswertung für:

- ATT-MPLS (n=25)
- Cogentco (n=197)
- Oteglobe (n=93)

Der finale Abschnitt liest die Serverordner:

- schritt4_algorithmen_vergleich/output/server/real_attmpls
- schritt4_algorithmen_vergleich/output/server/real_cogentco
- schritt4_algorithmen_vergleich/output/server/real_oteglobe

Plotstruktur
Die X-Achse wird paper-nah einheitlich als "Failure Rate" bezeichnet.
Technisch entspricht failureParameter bei Random Failures dem failFactor und
bei Clustered Failures dem failureStart.

Die Hauptplots enthalten:

- Resilience
- Avg. Hops

Avg. Stretch wird in den Hauptnotebooks in einer getrennten Zelle erzeugt,
damit die Hauptauswertung übersichtlicher bleibt.

Summary-CSV-Anzeige
Die beiden Hauptnotebooks enthalten jeweils eine eigene Zelle zum erneuten
Einlesen und Anzeigen der gespeicherten Summary-CSV:

- synthetic_graphs_runs1000_summary.csv
- real_world_graphs_runs1000_summary.csv

Finale Ausgaben

evaluation/output/synthetic_graphs_runs1000
- 12 PNG-Plots
- 12 SVG-Plots
- synthetic_graphs_runs1000_summary.csv

evaluation/output/real_world_graphs_runs1000
- 12 PNG-Plots
- 12 SVG-Plots
- real_world_graphs_runs1000_summary.csv

Pilot-Ausgaben

evaluation/output/synthetic_graphs_pilot
- 12 PNG-Plots
- synthetic_graphs_pilot_summary.csv

evaluation/output/real_world_graphs_pilot
- 12 PNG-Plots
- real_world_graphs_pilot_summary.csv

Protokolle
Die Protokolle liegen direkt unter schritt4_algorithmen_vergleich/Dokumentation:

- experiment.txt
- failures.txt
- routing_algorithms.txt
- result_analysis.txt
- test_routing_algorithms.txt
- synthetic_graphs_runs1000.txt
- real_world_graphs_runs1000.txt

Zusätzlich enthält server_commands.txt die Serverbefehle für die 1000-Run-Erzeugung.

Tests
python -m unittest discover -s schritt4_algorithmen_vergleich/evaluation -p "test_*.py" -v
