Pipeline-Automatisierung

## 1. Einstieg und Voraussetzungen

CLI und Streamlit-GUI führen dieselbe Pipeline aus: Routingexperimente,
Rohdaten-CSV, Summary und Vergleichsplots als PNG/SVG. Der Schritt-5-Ordner
enthält alle Projektmodule und die drei Real-World-Topologien; frühere Schritte
werden nicht benötigt.

Die bereitgestellten Bibliotheken benötigen Python ab 3.11. Geprüft wurde
Windows mit Python 3.11.3; andere Systeme und Versionen sind dadurch nicht
automatisch geprüft. Für bestehende Versuchsreihen die ursprüngliche Umgebung
beibehalten.

Alle Befehle beginnen im Elternordner von `schritt5_pipeline_automatisierung/`
(normalerweise im Repository-Hauptordner). Wer bereits im Schritt-5-Ordner
arbeitet, lässt diesen Präfix in den Befehlen weg.

## 2. Installation

`Dokumentation/requirements.txt` ist der Startpunkt: Sie enthält kommentierte
Einrichtungsschritte und alle 44 festgelegten Paketversionen für CLI, GUI,
Auswertung und Illustrationen. Python selbst muss vorher installiert werden,
etwa von https://www.python.org/downloads/ oder über die Systempaketverwaltung.
`venv` gehört zu Python, nicht in die pip-Paketliste. Unter Linux kann dafür
ein zusätzliches, zur Python-Version passendes venv-Systempaket nötig sein.

Eine neue virtuelle Umgebung erstellen und aktivieren. Existiert `.venv`
bereits für andere Versuche, einen anderen Namen und entsprechende Pfade wählen.

Windows / PowerShell:
```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Linux oder macOS / Bash:
```bash
python3.11 -m venv .venv
source .venv/bin/activate
```

Anschließend in beiden Fällen:
```text
python --version
python -m pip install --upgrade pip
python -m pip install -r schritt5_pipeline_automatisierung/Dokumentation/requirements.txt
python -m pip check
```

Fehlt `py -3.11` bzw. `python3.11`, den Pfad einer geeigneten Python-Installation
verwenden. Ist die PowerShell-Aktivierung gesperrt, statt `python` direkt
`.\.venv\Scripts\python.exe` aufrufen; keine Änderung der Sicherheitsrichtlinie nötig.

## 3. Erster CLI-Lauf

Zunächst prüfen, dann mit einem bisher unbenutzten Laufnamen starten:
```text
python schritt5_pipeline_automatisierung/pipeline.py --config schritt5_pipeline_automatisierung/config/pilot.json --run-name feedback_pilot --preflight
python schritt5_pipeline_automatisierung/pipeline.py --config schritt5_pipeline_automatisierung/config/pilot.json --run-name feedback_pilot
```

`pilot.json` verwendet Erdős-Rényi mit `n=25, p=0.15` und ATT-MPLS, fünf
Wiederholungen, sechs Algorithmen und vier Failure-Kombinationen. Beide Datasets
nutzen failFactor 0.8/4.0/8.0, failureStart 0.3/0.6/0.9 und failureDrop 0.3.
Erwartet werden im frischen Ausgabeordner ohne Erweiterungen:
- acht Jobs und 24 Rohdaten-CSVs mit je 30 Ergebniszeilen;
- eine Summary-CSV mit 144 Ergebniszeilen (jeweils ohne Kopfzeile);
- 24 Vergleichsabbildungen als PNG und SVG, also 48 Plotdateien;
- `used_config.json` und `manifest.json`.

Ausgabe: `schritt5_pipeline_automatisierung/Output/feedback_pilot/`.
Der vollständige Lauf ist in `config/full.json` mit 1000 Wiederholungen
konfiguriert. Vor einem solchen Lauf zuerst den Pilotversuch prüfen.

## 4. GUI verwenden

```text
python -m streamlit run schritt5_pipeline_automatisierung/gui.py
```

Für einen kleinen Test fünf Wiederholungen, einen neuen Laufnamen und zunächst
ein Dataset wählen. Über `+ Hinzufügen` Erdős-Rényi (`n`, `p`) oder Real-World
(ATT-MPLS, Oteglobe, Cogentco) konfigurieren und mit `Graph speichern` übernehmen.
Beide Graphkategorien bieten Parameterbereiche für Random- und Clustered-Failure.
`Experiment starten` speichert `gui_config.json` und startet die Pipeline.

`Paper-Graphsets` lädt die sechs vorbereiteten Datasets. Für vollständige
Paper-Läufe 1000 Wiederholungen einstellen. Die sechs Basisalgorithmen und vier
Basisfälle bleiben auch nach Erweiterungen vorausgewählt; Zusatzverfahren
müssen ausdrücklich ausgewählt werden. Der GUI-Seed ist fest `123`.
Details zu den GUI-Funktionen: `Dokumentation/gui.txt`.

## 5. Konfiguration und Parameter

Die JSON-Datei enthält `run_name`, `runs`, `seed`, `resume`, `algorithms`,
`failures`, `datasets` und `metrics`; optional `output_root` und `plot_groups`.
`runs` gilt je Dataset und Failure-Konfiguration, nicht für den gesamten Lauf.
Bei Erdős-Rényi stehen `nodes` für n und `p` für die Kantenwahrscheinlichkeit.
Random-Regular ist über JSON/CLI mit `degree` verfügbar, nicht im GUI-Graphdialog.
Graphparameter ändern keine eingelesenen Real-World-Topologien.

Die wichtigsten Failure-Parameter:
- `fail_factors` / `--fail-factor`: skaliert bei Random Failure die Ausfallzahl
  als `round(max(k - 1, 0) * failFactor)`, begrenzt auf verfügbare Kandidaten.
  Dabei ist k die Anzahl der EDPs bei Link- und der NDPs bei Knotenausfällen.
- `failure_starts` / `--failure-start`: anfänglicher Auswahlanteil bei
  Clustered Failure; zulässig `0 < Wert <= 1`.
- `failure_drop` / `--failure-drop`: Abnahme dieses Anteils pro Runde,
  ebenfalls `0 < Wert <= 1`. Beispielsweise ergeben 0.8 und 0.3 die Raten
  0.8, 0.5 und 0.2. Details zur Auswahl: `Dokumentation/src_failures.txt`.

Vorrang für Failure-Parameter: CLI > Dataset > globale JSON-Werte. Die GUI
speichert diese Werte je Dataset. Die Plotachse `Failure Rate` bezeichnet
failFactor oder failureStart, keine einheitliche prozentuale Ausfallrate.

Beispiel für Overrides (einzeilig in PowerShell und Bash ausführbar):
```text
python schritt5_pipeline_automatisierung/pipeline.py --config schritt5_pipeline_automatisierung/config/pilot.json --run-name quick_n50 --runs 5 --seed 123 --nodes 50 --p 0.15 --failures random_link random_node --fail-factor 1 2 3
```

Graphparameter betreffen nur ausgewählte synthetische Datasets. Alle Optionen:
```text
python schritt5_pipeline_automatisierung/pipeline.py --help
```

## 6. Ausführungsmodi

- Normaler Aufruf: Experimente, Summary und Plots erzeugen.
- `--dry-run`: Jobplan anzeigen, ohne Experimente oder neue Ausgabedateien.
- `--preflight`: grundlegende Konfigurations-, Datei- und Schreibprüfungen;
  kann den Ausgabeordner anlegen, startet aber keine Experimente.
- `--only-experiments`: Rohdaten und Metadaten erzeugen, keine Plots.
- `--only-plots`: vollständige Rohdaten derselben Konfiguration und desselben
  Laufordners neu aggregieren und plotten; liest nicht die Summary-CSV.

Diese Modi sind auch in der GUI auswählbar. Die GUI schreibt jedoch auch bei
Dry Run vorher `gui_config.json`; der direkte CLI-Dry-Run tut dies nicht.
Dry Run und Preflight sowie
Only Experiments und Only Plots sind jeweils nicht miteinander kombinierbar.
Die Vorabprüfungen erfolgen auch vor normalen Läufen, ersetzen aber keine
Funktionstests neuer Erweiterungen. Details: `Dokumentation/pipeline.txt`.

## 7. Ergebnisdateien und Plotgruppen

Standardziel ist `Output/<run_name>/` innerhalb des Schritt-5-Ordners:
- `raw/<dataset>/`: einzelne Versuchsergebnisse;
- `summaries/`: aggregierte Ergebnis-CSV;
- `plots/`: PNG- und SVG-Abbildungen;
- `used_config.json` und `manifest.json`: Konfiguration und Laufmetadaten.

`--run-name` setzt auch den Standardausgabeordner neu. Ein eigenes `output_root`
bzw. `--output-root` kann relativ zum Schritt-5-Ordner oder absolut sein.
Vorhandene Ordner werden nicht automatisch umbenannt; unter Linux sind `Output` und `output`
verschiedene Verzeichnisse.

CLI und GUI trennen standardmäßig `plots/random_graphs/` und `plots/real_world/`
mit höchstens drei Datasets je Gruppe. Jede Abbildung zeigt eine Metrik und
eine Failure-Kombination. Eigene JSON-`plot_groups` umgehen die automatische
Dreieraufteilung; für denselben Aufbau maximal drei Datasets derselben Kategorie
je Gruppe eintragen. Die ausgegebene Plotanzahl zählt PNG und SVG einzeln.

Resilience berücksichtigt alle Szenen, Average Hops und Stretch nur erfolgreiche
Routings. Stretch ist die additive Differenz zur kürzesten verbleibenden Route.
Details zur Auswertung: `Dokumentation/evaluation_result_analysis.txt`.

## 8. Wiederholbarkeit und lange Läufe

Für reproduzierbare Ergebnisse müssen Seed, Konfiguration, Inputgraphen,
Codeversion, Python und relevante Bibliotheksversionen übereinstimmen.
Bei Real-World-Graphen bleibt die Topologie fest; der Seed steuert weiterhin
Start-/Zielknoten und Ausfälle. Bei synthetischen Graphen steuert er zusätzlich
die Graphgenerierung.

Beide Beispielkonfigurationen aktivieren Resume. Ein erneuter Aufruf setzt
gespeicherte Wiederholungen fort. ACHTUNG: `--no-resume` entfernt vorhandene
Rohdaten der betroffenen Konfiguration vor der Neuberechnung. Für geänderte
Parameter oder unabhängige Wiederholungstests immer neue Laufnamen verwenden.

Zum Vergleich denselben Pilotbefehl aus Abschnitt 3 mit zwei neuen Namen
ausführen und entsprechende Rohdaten sowie numerische Summary-Werte vergleichen.
Ein abgeschlossener Resume-Lauf ist kein Neuberechnungstest. Zeitstempel und
Ausgabepfade in den Metadaten dürfen sich unterscheiden.

Das Manifest protokolliert Paketversionen und Code-/GraphML-Prüfsummen des
aktuellen Aufrufs, nicht nachträglich die Herkunft wiederverwendeter Rohdaten.
Ursprüngliche Konfigurationen, Code und Manifeste deshalb aufbewahren.
CLI-Auswahl- und Resume-Overrides werden als wirksame Werte in `used_config.json`
und im Manifest gespeichert. Vor Summary und Plots gleicht die Pipeline alle
erwarteten Parametergruppen mit den vorhandenen Ergebnissen ab. Vorhandene Gruppen
müssen außerdem für jeden ausgewählten Algorithmus die erwartete Zeilenzahl besitzen.
Die Eindeutigkeit der Wiederholungsnummern wird noch nicht geprüft
(Details: Dokumentation/evaluation_result_analysis.txt).
CLI und GUI zeigen Job- und Wiederholungsfortschritt in Blöcken; einzelne
langsame Wiederholungen liefern keine Zwischenmeldung oder Restzeitschätzung.

## 9. Serverausführung

`Lokal ausführen` rechnet dort, wo Streamlit läuft, gegebenenfalls auf dem Server.
`Server vorbereiten` erzeugt `gui_config.json` und `run_on_server.sh`, startet
aber keinen entfernten Prozess. Konfiguration übertragen und dort per CLI
ausführen oder Streamlit direkt auf dem Server starten. Serverzugang und dort
installierte Abhängigkeiten sind erforderlich; SSH ist nicht in die GUI eingebaut.

## 10. Tests und weitere Hilfe

```text
python -m unittest discover -s schritt5_pipeline_automatisierung/tests -p "test_*.py" -v
```

Mit Streamlit laufen auch die GUI-AppTests; ohne Streamlit werden sie
übersprungen. Sie ersetzen keinen visuellen Browsertest oder unabhängigen
Wiederholungstest.

Häufige Startprobleme:
- Importfehler: Pakete mit `python -m pip` in derselben Umgebung installieren.
- Falsches Python / WindowsApps-Fehler: den tatsächlichen Interpreter der
  virtuellen Umgebung verwenden und `python --version` prüfen.
- `JSONDecodeError`: Kommentare und Kommas hinter letzten Listeneinträgen
  sind in JSON nicht erlaubt.
- Fehlende Plotlabels oder Farben: Metadaten des Zusatzalgorithmus in
  `evaluation/result_analysis.py` ergänzen; siehe zugehöriges Modulprotokoll.

Weiterführende Dokumentation (Pfade relativ zum Schritt-5-Ordner):
- `Dokumentation/Modulübersicht.txt`: Projektmodule und ihre Protokolle.
- `Dokumentation/Feedback_Ueberarbeitung.txt`: Feedbackänderungen und Testnachweise.
- `illustrations/README.txt`: einzelne Graph- und Routingabbildungen.
- `../schritt7_erweiterung/ERWEITERUNG.txt`: Erweiterungsanleitung und Checkliste.
