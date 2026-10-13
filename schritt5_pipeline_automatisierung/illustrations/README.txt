Illustrationen für die Ausarbeitung
===================================

Das Modul erzeugt erklärende Abbildungen getrennt von der Experiment-Pipeline.
Graphen, Endpunkte, Pfade, Baumstrukturen, Ausfälle und Routen werden mit den
Kernfunktionen aus `src/` berechnet. Nur Layout und Darstellung befinden sich
in `create_thesis_figures.py`.

Verwendete Kernmodule
---------------------

- `src/experiment.py`: Graphen sowie Auswahl von Start- und Zielknoten
- `src/routing_algorithms.py`: EDPs, NDPs, Baumaufbau und Routing
- `src/failures.py`: zufällige und geclusterte Ausfälle
- `evaluation/result_analysis.py`: Algorithmusfarben und Beschriftungen

Ausgabe
-------

Standardordner:

schritt5_pipeline_automatisierung/Output/illustrations/figures

SVG eignet sich für die Ausarbeitung, PNG für eine schnelle Vorschau. Ein
abweichender Zielordner kann mit `--output-dir` angegeben werden.

Vergleichsabbildungen
---------------------

Der Aufruf ohne weitere Optionen erzeugt die drei zentralen Abbildungen als
SVG und PNG:

python schritt5_pipeline_automatisierung/illustrations/create_thesis_figures.py

Explizit lautet derselbe Aufruf:

python schritt5_pipeline_automatisierung/illustrations/create_thesis_figures.py --scene comparison --formats svg png

Verwendet wird reproduzierbar ein Erdős-Rényi-Graph mit `n=10`, `p=0.35`
und `seed=430`. Es entstehen:

- `thesis_comparison_edp_ndp_paths`: EDPs und NDPs
- `thesis_comparison_edp_ndp_one_tree`: EDP/NDP One Tree
- `thesis_comparison_edp_ndp_multiple_trees`: EDP/NDP Multiple Trees

Alle Teilbilder verwenden denselben Graphen und dieselben Knotenpositionen.
Die Abbildungen enthalten keine Überschriften. In allen drei Vergleichen steht
die EDP-Variante links und die NDP-Variante rechts. Jeder Ausgangspfad erhält
eine eigene Farbe und wird mit einer durchgezogenen Linie dargestellt.
Hinzugefügte Baumäste werden einheitlich rot und ebenfalls mit durchgezogenen
Linien dargestellt. Führt ein neuer Ast zu einem zusätzlichen Ausgang nach
`d`, wird auch diese gepunktete Verbindung rot gezeichnet. Gehört die
Ausgangskante bereits zu einem farbigen Basispfad, wird sie nicht rot
überzeichnet. Die
Knotendisjunktheit gilt für die NDP-Ausgangspfade; hinzugefügte Baumäste können
gemeinsame innere Knoten enthalten.

Direkter Disjunktheitsvergleich
-------------------------------

python schritt5_pipeline_automatisierung/illustrations/create_thesis_figures.py --scene disjointness --formats svg png

Diese Abbildung nutzt einen über `experiment.create_graph(...)` erzeugten
Erdős-Rényi-Graph mit `n=8`, `p=0.3` und `seed=21`. Zwei EDPs teilen dort einen
inneren Knoten, während nur ein NDP existiert. Zusätzlich wird das Routing vor
und nach dem Ausfall dieses Knotens verglichen.

Kanten- und Knotenausfall vergleichen
------------------------------------

python schritt5_pipeline_automatisierung/illustrations/create_thesis_figures.py --scene failure_comparison --formats svg png

Die Datei `failure_comparison_link_node` zeigt denselben Graphen nebeneinander:
links einen Kantenausfall, rechts einen Knotenausfall mit allen inzidenten
Kanten. Die kurzen Beschriftungen eignen sich für eine Präsentationsfolie.
Die Knotenpositionen sind identisch. Verfügbare Kanten sind grau und
durchgezogen, ausgefallene Kanten rot und gestrichelt. Der ausgefallene
Knoten ist zusätzlich rot hervorgehoben. Pfade werden nicht eingezeichnet.

Verwendet wird der obige Kernmodul-Graph mit n=8, p=0.3 und seed=21.
Für dieses erklärende Beispiel sind die Ausfälle gezielt gewählt: links
die Kante zwischen s und x, rechts der innere Knoten x. Dessen fünf
inzidente Kanten bestimmt `node_failures_to_edges(...)` aus `src/failures.py`.
Es handelt sich nicht um eine zufällig gezogene Ausfallmenge oder eine
Failure-Rate-Auswertung. Die Originaltopologie bleibt unverändert; Ausfälle
werden in der Abbildung markiert, nicht aus dem gezeichneten Graphen entfernt.
Die Graph- und Failure-Parameter der konfigurierbaren Szene gelten hier nicht.

Ablaufgrafik der Experimentpipeline
-----------------------------------

python schritt5_pipeline_automatisierung/illustrations/create_thesis_figures.py --scene pipeline --formats svg png

`pipeline_overview.svg` und `pipeline_overview.png` zeigen vier Stationen:
Konfiguration -> Experimente -> Auswertung -> Plots. Kurze Stichworte unter
den Stationen erläutern Bedienung und Ausgaben. Die Szene erzeugt nur eine
schematische Präsentationsgrafik; sie startet keine Routingexperimente und
liest keine Versuchsergebnisse ein. Die Standardauswahl bleibt `comparison`.

Konfigurierbare Szenen
----------------------

`--scene configured` unterstützt Erdős-Rényi- und Random-Regular-Graphen, alle
sechs Basisalgorithmen sowie zufällige und geclusterte Link- und Node-Failures.

Nur Graph und Ausfälle:

python schritt5_pipeline_automatisierung/illustrations/create_thesis_figures.py --scene configured --graph-type erdos_renyi --nodes 25 --p 0.15 --path-type none --failure-type link --failure-model clustered --failure-start 0.8 --failure-drop 0.3 --formats svg png

Pfade ohne Ausfälle:

python schritt5_pipeline_automatisierung/illustrations/create_thesis_figures.py --scene configured --graph-type random_regular --nodes 10 --degree 4 --path-type both --failure-model none --seed 4 --formats svg

Ein Algorithmus ohne Ausfälle:

python schritt5_pipeline_automatisierung/illustrations/create_thesis_figures.py --scene configured --graph-type random_regular --nodes 10 --degree 4 --algorithm ndp_one_tree --failure-model none --seed 4 --formats svg png

Zulässige Algorithmen:

- `edp_paths`, `edp_one_tree`, `edp_multiple_trees`
- `ndp_paths`, `ndp_one_tree`, `ndp_multiple_trees`

Bei One Tree und Multiple Trees zeigt die Algorithmusabbildung vier Phasen:

1. alle berechneten EDPs beziehungsweise NDPs,
2. Baumwachstum vor dem Trunkieren,
3. finale Strukturen nach dem Trunkieren,
4. Ausfälle und tatsächlich ausgeführte Route.

Mit `--max-paths N` kann die Zahl dargestellter Pfade begrenzt werden. Der
Standardwert `0` berücksichtigt alle berechneten Pfade.

Failure-Parameter
-----------------

- Random Failure: `--fail-factor`; die Anzahl wird wie in der Pipeline aus
  EDP- beziehungsweise NDP-Anzahl berechnet.
- Clustered Failure: `--failure-start` und `--failure-drop`.
- Ohne Ausfälle: `--failure-model none`.

Alle verfügbaren Szenen gemeinsam erzeugen:

python schritt5_pipeline_automatisierung/illustrations/create_thesis_figures.py --scene all --formats svg png
