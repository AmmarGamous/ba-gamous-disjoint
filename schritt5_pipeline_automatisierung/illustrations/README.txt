Illustrationen für die Ausarbeitung
===================================

Dieser Ordner enthält ein separates Hilfsmodul für erklärende Abbildungen.
Es gehört nicht zur Experiment-Pipeline, verwendet aber dieselben Kernfunktionen
für EDPs, NDPs und Failure-Auswahl.

Genutzte Schritt-5-Module
-------------------------

- `src/experiment.py`: synthetische Graph-Erzeugung und Source-Destination-Auswahl
- `src/routing_algorithms.py`: EDP-/NDP-Berechnung und Aufbau von Pfad-/Baumstrukturen
- `src/failures.py`: Random- und Clustered-Failure-Auswahl
- `evaluation/result_analysis.py`: Algorithmusnamen und Farben

Nur die eigentliche Zeichnung der erklärenden Bilder bleibt in diesem Modul,
weil sie andere Anforderungen hat als die Ergebnisplots der Pipeline.

Ausführen
---------

Aus dem Repository-Wurzelordner:

python schritt5_pipeline_automatisierung/illustrations/create_thesis_figures.py

Ausgaben
--------

Standardmäßig entstehen die Dateien unter:

schritt5_pipeline_automatisierung/illustrations/output/figures

Der Seed steht im Titel und im Dateinamen. Dadurch überschreiben Abbildungen
mit unterschiedlichen Zufallsgraphen einander nicht.

Erzeugt werden Beispiele für:

- Edge-Disjoint Paths
- Node-Disjoint Paths
- Random Link Failure
- Random Node Failure
- Clustered Link Failure
- Clustered Node Failure
- direkter Vergleich der Stärke von EDP- und NDP-Disjunktheit

Die Bilddateien sind für die direkte Verwendung in der Ausarbeitung gedacht.
Standardmäßig werden SVG- und PNG-Dateien erzeugt.
Jeder markierte Pfad erhält eine eigene Farbe. NDP-Pfade werden zusätzlich
strichpunktiert dargestellt, damit sie von EDP-Pfaden unterscheidbar bleiben.

Optionen
--------

Anderer Ausgabeordner:

python schritt5_pipeline_automatisierung/illustrations/create_thesis_figures.py --output-dir C:/tmp/ba_figures

Nur SVG erzeugen:

python schritt5_pipeline_automatisierung/illustrations/create_thesis_figures.py --formats svg

Anderer Seed für die Failure-Beispiele:

python schritt5_pipeline_automatisierung/illustrations/create_thesis_figures.py --seed 42

EDP und NDP auf demselben Beispielgraphen vergleichen:

python schritt5_pipeline_automatisierung/illustrations/create_thesis_figures.py --scene disjointness --formats svg png

Der Graph wird nicht manuell im Illustrationsmodul aufgebaut. Die Abbildung
verwendet die vollständige Modulkette:

- `experiment.create_graph(...)`: Erdős-Rényi-Graph mit `n=8`, `p=0.3` und
  `seed=21`
- `experiment.choose_endpoints(...)`: reproduzierbare Auswahl von `s` und `d`
- `routing_algorithms.get_disjoint_paths(...)`: Berechnung der EDPs und NDPs
- `failures.node_failures_to_edges(...)`: Abbildung des Ausfalls von `x`
- `routing_algorithms.route_algorithm(...)`: Routing vor und nach dem Ausfall

Die linke Seite zeigt zwei EDPs, die keine Kante gemeinsam verwenden, aber den
inneren Knoten `x` teilen. Da jeder Weg von `s` nach `d` über `x` führt, kann
auf der rechten Seite nur ein NDP berechnet werden. Der Ausfall von `x` lässt
beide EDPs gleichzeitig scheitern. Damit zeigt die Abbildung, dass
Knotendisjunktheit eine stärkere Bedingung als Kantendisjunktheit ist.

Konfigurierbare Routing-Szene erzeugen:

python schritt5_pipeline_automatisierung/illustrations/create_thesis_figures.py --scene configured --graph-type erdos_renyi --nodes 14 --p 0.3 --path-type edp --failure-type link --failure-model random --fail-factor 0.8 --formats svg

Konfigurierbare Szene mit NDP und Node Failure:

python schritt5_pipeline_automatisierung/illustrations/create_thesis_figures.py --scene configured --graph-type erdos_renyi --nodes 14 --p 0.3 --path-type ndp --failure-type node --failure-model random --fail-factor 0.8 --formats svg

Konfigurierbare Szene mit geclustertem Ausfall:

python schritt5_pipeline_automatisierung/illustrations/create_thesis_figures.py --scene configured --graph-type random_regular --nodes 12 --degree 3 --path-type both --failure-type node --failure-model clustered --failure-start 0.8 --failure-drop 0.3 --formats svg

Nur Graph und Ausfälle ohne Pfadmarkierung:

python schritt5_pipeline_automatisierung/illustrations/create_thesis_figures.py --scene configured --graph-type erdos_renyi --nodes 25 --p 0.15 --path-type none --failure-type link --failure-model clustered --failure-start 0.8 --failure-drop 0.3 --formats svg png

Nur Graph ohne Ausfälle:

python schritt5_pipeline_automatisierung/illustrations/create_thesis_figures.py --scene configured --graph-type erdos_renyi --nodes 25 --p 0.15 --path-type none --failure-model none --formats svg png

Einzelnen Algorithmus ohne Ausfälle zeichnen:

Bei One Tree und Multiple Trees enthält eine Abbildung vier Teilbilder:

- links alle berechneten EDPs beziehungsweise NDPs ohne Ausfälle
- danach das Baumwachstum ohne Ausfälle; bei One Tree wird der längste Pfad,
  bei Multiple Trees werden alle Pfade längenabsteigend erweitert
- anschließend die finalen Strukturen nach dem Trunkieren, weiterhin ohne
  Ausfälle
- zusätzliche direkte Ausgänge zum Ziel `d` als gepunktete Linien
- rechts die Ausfälle und die von `routing_algorithms.route_algorithm(...)`
  tatsächlich ausgeführte Route; Pfeile und Nummern zeigen ihre Reihenfolge

Innerhalb eines Grundpfads beginnt das Baumwachstum beim inneren Knoten neben
`s` und läuft in Richtung des letzten inneren Knotens `d-1`. Das spätere
Routing probiert die finalen Strukturen dagegen nach der Länge ihres
Grundpfads aufsteigend und damit den kürzesten Pfad zuerst aus.

Sind mehrere Pfade maximal lang, wird der durch die stabile Sortierung gewählte
One-Tree-Grundpfad mit `Längengleichstand` gekennzeichnet. Dadurch wird nicht
fälschlich behauptet, dass es genau einen längsten Pfad gibt.

Standardmäßig werden alle berechneten Pfade berücksichtigt. Mit
`--max-paths N` kann die Darstellung bei sehr großen Graphen auf höchstens N
Pfade begrenzt werden.

python schritt5_pipeline_automatisierung/illustrations/create_thesis_figures.py --scene configured --graph-type erdos_renyi --nodes 25 --p 0.15 --algorithm edp_paths --failure-model none --formats svg

python schritt5_pipeline_automatisierung/illustrations/create_thesis_figures.py --scene configured --graph-type erdos_renyi --nodes 25 --p 0.15 --algorithm ndp_paths --failure-model none --formats svg

python schritt5_pipeline_automatisierung/illustrations/create_thesis_figures.py --scene configured --graph-type erdos_renyi --nodes 25 --p 0.15 --algorithm edp_one_tree --failure-model none --formats svg

python schritt5_pipeline_automatisierung/illustrations/create_thesis_figures.py --scene configured --graph-type erdos_renyi --nodes 25 --p 0.15 --algorithm edp_multiple_trees --failure-model none --formats svg

python schritt5_pipeline_automatisierung/illustrations/create_thesis_figures.py --scene configured --graph-type erdos_renyi --nodes 25 --p 0.15 --algorithm ndp_one_tree --failure-model none --formats svg

python schritt5_pipeline_automatisierung/illustrations/create_thesis_figures.py --scene configured --graph-type erdos_renyi --nodes 25 --p 0.15 --algorithm ndp_multiple_trees --failure-model none --formats svg

Hinweis zu Failure-Parametern:

- Bei `--failure-model random` steuert `--fail-factor` die Ausfallanzahl wie in der Pipeline:
  `round((Konnektivität - 1) * failFactor)`.
- Für Link-Failures wird dafür die Anzahl der EDPs verwendet.
- Für Node-Failures wird dafür die Anzahl der NDPs verwendet.
- Bei `--failure-model clustered` steuern `--failure-start` und `--failure-drop` die Failure Rate.

Optional zusätzlich GraphML schreiben:

python schritt5_pipeline_automatisierung/illustrations/create_thesis_figures.py --write-graphml
