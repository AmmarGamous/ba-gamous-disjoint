UML-Diagramme der Experimentierumgebung
Stand des Quellenabgleichs: 20.09.2026

Einstieg
-------
index.html zeigt alle Abbildungen mit einer Erklärung der Eingaben, der
Verarbeitung und der Ausgaben. Die Datei kann direkt im Browser geöffnet
werden; ein Webserver wird nicht benötigt.

Umfang
------
00: Gesamtarchitektur als UML-Komponentendiagramm.
01-05, 08-09: Aktivitätsdiagramme der sieben produktiven Module.
06-07: Zusätzliche Detailabläufe für Strukturaufbau und rekursives Routing.
10: Klassendiagramm der echten Datenklassen RoutingStructure und RoutingResult.
11-14: Thematische Übersichten der vier nicht auf Illustrationen ausgerichteten
Testmodule. Ihre Testmethoden sind unabhängig; die dargestellten Themenblöcke
schreiben keine Reihenfolge der Tests vor.

Das Illustrationsmodul und test_illustrations.py sind bewusst ausgeschlossen.
Die Dokumentation der Schritte 6 und 7 ist keine zusätzliche Laufzeitkomponente.
Frühere Entwicklungsstände in Schritt 1 bis 4 sind nicht Teil dieses Diagramms
der aktuellen Schritt-5-Implementierung.

Dateien
-------
*.puml: editierbare PlantUML-Quellen, je Diagramm eine Datei.
_style.iuml: gemeinsame Darstellung.
figures/*.svg: skalierbare Vektorgrafiken.
figures/*.png: Rasterbilder für Vorschau und unkomplizierte Einbindung.
build_index.py: erzeugt ausschließlich die lokale HTML-Übersicht.

Lesehilfe
---------
Im Komponentendiagramm zeigt ein gestrichelter Pfeil vom nutzenden Modul zum
verwendeten Modul. Zentrale Ein- und Ausgaben stehen in den Komponenten.
Das ist keine zeitliche Reihenfolge. Die Aktivitätsdiagramme zeigen dagegen
den Ablauf: Aktionen, Entscheidungen, Schleifen und frühe Rückgaben.
Signaturen sind teilweise verkürzt; Quellcode-Links stehen in index.html.

Die Fehlerbehandlung ist auf wichtige Entscheidungen reduziert. Die Diagramme
sind eine Beschreibung des Codes, keine automatisch aus dem AST gewonnene
Vollständigkeitsgarantie und kein Nachweis neuer Testausführungen.

Wichtige Abgrenzungen
--------------------
- pipeline.py benötigt eine JSON-Konfiguration. experiment.py besitzt eine
  separate CLI ohne JSON, führt aber allein keine gesamte Auswertung aus.
- gui.py schreibt gui_config.json und ruft dieselbe Pipeline auf. Server
  vorbereiten erzeugt nur Konfiguration und Startskript.
- experiment.py schreibt Rohdaten. routing_algorithms.py liefert Objekte.
  failures.py liefert Listen. Beide Module schreiben keine Ergebnisdateien.
- Die Pipeline schreibt die Summary-CSV. result_analysis.py erzeugt Plots
  aus dem aggregierten DataFrame; es liest dafür nicht die Summary-Datei.
- Ausfallkanten werden vor dem Aufruf der Routingverfahren ausgewählt. Der
  anschließende Strukturaufbau benutzt trotzdem den intakten Eingabegraphen.
  Erst beim Durchlaufen der Strukturen werden die Ausfälle berücksichtigt.
- One Tree schützt in EDP- und NDP-Varianten die übrigen Basispfade. Multiple
  Trees reserviert Kanten, nicht global innere Knoten. Die Schlusskanten zu d
  gehören nicht zu dieser Reservierung. Trunkierung folgt nach dem Wachstum
  jedes Baums; reservierte, später entfernte Kanten werden nicht freigegeben.
- nr_structures in RoutingResult ist die Anzahl vorbereiteter Strukturen.
  Die vollständige Route und nr_structures werden nicht als Rohdatenfelder
  gespeichert. Der Routingkern summiert Hops über alle getesteten Strukturen.
- Die Summary-Prüfung erkennt fehlende geplante Parametergruppen, garantiert
  aber keine eindeutigen Wiederholungsnummern bei gleicher Zeilenanzahl.

Erneut erzeugen
---------------
Benötigt werden Java und PlantUML (hier verwendet: PlantUML 1.2026.8).
Dies sind Werkzeuge für diese Dokumentationsgrafiken, keine zusätzlichen
Abhängigkeiten der Routingexperimente. Smetana rendert die Komponenten- und
Klassendiagramme ohne eine separate Graphviz-Installation.

Aus dem Repository-Hauptordner; Pfad zur eigenen plantuml.jar einsetzen:

java -jar plantuml.jar -charset UTF-8 -failfast2 -tsvg -o figures "schritt5_pipeline_automatisierung/Dokumentation/UML/*.puml"
java -jar plantuml.jar -charset UTF-8 -failfast2 -tpng -o figures "schritt5_pipeline_automatisierung/Dokumentation/UML/*.puml"
python schritt5_pipeline_automatisierung/Dokumentation/UML/build_index.py

Offizielle Hinweise:
https://plantuml.com/command-line
https://plantuml.com/smetana02

Für die Ausarbeitung eignet sich vor allem 00_gesamtarchitektur. Die vielen
Detaildiagramme sind zum Verständnis und gegebenenfalls für den Anhang gedacht;
sie müssen nicht alle in den Haupttext aufgenommen werden.
