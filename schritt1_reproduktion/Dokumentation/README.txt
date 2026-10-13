# Schritt 1: Reproduktion der TREE-Referenzimplementierung

Ziel von Schritt 1 war die Reproduktion der bestehenden TREE-Arbeit für Kantenausfälle.
Dafür wurde zunächst die Referenzimplementierung analysiert. Die Algorithmen befinden sich im src-Ordner,
während die experimentelle Auswertung über Jupyter-Notebooks und CSV-Dateien im evaluation-Ordner erfolgt.
Im Rahmen der Reproduktion wurden die vorhandenen Notebooks lauffähig gemacht,
Pfade an die neue Projektstruktur angepasst und die Plots aus den bereitgestellten bzw. erzeugten CSV-Dateien rekonstruiert.
Zusätzlich wurden die zentralen Python-Dateien der Referenzimplementierung in schritt1_reproduktion/src überarbeitet, damit sie für Schritt 1 direkt ausführbar sind:

kResiliencePaths.py: Implementierung und Testausführung für Edge-Disjoint Paths (EDPs)
kResilienceTrees.py: Implementierung der One-Tree- und Multiple-Trees-Verfahren sowie CSV-Erzeugung
Colorizer.py: Visualisierung von Graphen, Baumstrukturen und Routing-Ergebnissen

Die fachliche Algorithmik wurde dabei nicht grundlegend verändert. Die Anpassungen betreffen vor allem Ausführbarkeit, robuste Pfadbehandlung, reproduzierbare Testläufe, CSV-Kompatibilität und die Bedienbarkeit über Kommandozeilenparameter.