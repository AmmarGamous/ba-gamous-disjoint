Pipeline-Automatisierung

Diese Pipeline führt die Schritt-4-Experimente konfigurationsgetrieben aus und
erzeugt danach automatisch Summary-CSV sowie PNG/SVG-Plots.

Der Ordner ist eigenständig nutzbar: Der Experiment-Code liegt unter `src/`,
die Plot-Auswertung unter `evaluation/` und die benötigten Real-World-Graphen
unter `data/topology_zoo/`. Relative Datenpfade in JSON-Konfigurationen werden
vom Schritt-5-Ordner aus aufgelöst. Relative Ausgabepfade landen ebenfalls im
Schritt-5-Ordner, standardmäßig unter `Output/`.

Der Ordner `Dokumentation/` enthält Protokolle für alle Python-Module.
Die Datei `Dokumentation/Modulenübersicht.txt` dient als Übersicht. Der

## Schnellstart

Vom Repository-Root:

```powershell
python schritt5_pipeline_automatisierung/pipeline.py --config schritt5_pipeline_automatisierung/config/pilot.json
```

Falls Windows auf den Microsoft-Store-Alias `WindowsApps/python.exe` zeigt und
der Start mit "Zugriff verweigert" scheitert, denselben Befehl mit einer
funktionierenden Python-Installation beziehungsweise auf dem Linux-Server im
aktivierten `venv` ausführen.

Vor einem langen Lauf kann mit `--dry-run` der geplante Jobplan ohne Berechnung
angezeigt werden:

```powershell
python schritt5_pipeline_automatisierung/pipeline.py --config schritt5_pipeline_automatisierung/config/full.json --dry-run
```

Vor dem eigentlichen Lauf kann mit `--preflight` geprüft werden, ob die
Konfiguration technisch ausführbar ist:

```powershell
python schritt5_pipeline_automatisierung/pipeline.py --config schritt5_pipeline_automatisierung/config/full.json --preflight
```

## GUI

Die Streamlit-GUI ist eine zusätzliche Bedienoberfläche. Sie erzeugt eine
JSON-Konfiguration im Ausgabeordner und startet danach dieselbe Pipeline wie die CLI.

Installation, falls Streamlit noch fehlt. Empfohlen ist eine virtuelle
Python-Umgebung mit `venv`, damit die GUI-Abhängigkeiten getrennt vom System
installiert werden.

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r schritt5_pipeline_automatisierung/Dokumentation/requirements-gui.txt
```

Auf einem Linux-Server entsprechend:

```bash
python3 -m venv venv
source venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r schritt5_pipeline_automatisierung/Dokumentation/requirements-gui.txt
```

Start:

```powershell
streamlit run schritt5_pipeline_automatisierung/gui.py
```

Alternativ:

```powershell
python -m streamlit run schritt5_pipeline_automatisierung/gui.py
```

Die GUI bietet Auswahlfelder für:

- Algorithmen
- Fehlertypen
- `+ Hinzufügen` unter `Graphen`
- Random-Graphen als Erdos-Renyi mit frei wählbarem `n`, `p`,
  Failure-Rate-Bereichen und Schrittgrößen
- Real-World-Graphen: `Small: ATT-MPLS`, `Medium: Oteglobe`, `Large: Cogentco`
- `runs`, Failureparameter, `failureDrop` und Metriken

Der Seed ist in der GUI fest auf `123` gesetzt. Dadurch bleiben wiederholte
GUI-Läufe mit derselben Konfiguration reproduzierbar. Über die CLI kann der
Seed weiterhin überschrieben werden.
Die Pipeline sortiert Endpunkt-, Kanten- und Knotenkandidaten stabil, bevor
zufällig ausgewählt wird. Dadurch führen gleiche Konfiguration, gleiche
Inputdaten, gleiche Codeversion und gleicher Seed zu denselben Routing-Szenen.

Der Button `Experiment starten` schreibt zuerst `gui_config.json` und startet
dann die Pipeline. Dadurch bleiben GUI-Läufe genauso nachvollziehbar wie
CLI-Läufe.

Mit `+ Hinzufügen` wird zuerst eine neue Graph-Konfiguration geöffnet. Danach
wird zwischen `Random (Erdos-Renyi)` und `Real-World` gewählt. Durch erneutes
Hinzufügen können mehrere Graph-Sets in einem Lauf kombiniert werden.

Jede neue Graph-Konfiguration hat zwei Failure-Blöcke:

- `Random-Failure`: `Failure Rate` bedeutet `failFactor`.
- `Clustered-Failure`: `Failure Rate` bedeutet `failureStart`.
- `failureDrop` kann pro Graph-Konfiguration gesetzt werden.

Wenn alle Läufe analog zu Schritt 4 vorbereitet werden sollen, in der GUI:

- unter `Graphen` den Button `Paper-Graphsets` drücken
- `runs` auf `1000` setzen
- alle sechs Algorithmen und alle vier Fehlertypen aktiviert lassen

Die GUI verwendet dafür diese Schritt-4-Defaults:

- Erdos-Renyi `n=25,p=0.15`: Random-Failfactor `0.8` bis `8.8` in `0.8`-Schritten
- Erdos-Renyi `n=50,p=0.15`: Random-Failfactor `0.8` bis `16.8` in `0.8`-Schritten
- Erdos-Renyi `n=100,p=0.02`: Random-Failfactor `0.8` bis `49.6` in `0.8`-Schritten
- Real-World `ATT-MPLS`, `Cogentco`, `Oteglobe`: Random-Failfactor `1.0` bis `10.0` in `1.0`-Schritten
- Clustered-Failures für alle Graph-Sets: `failure_start = 0.3` bis `0.9` in `0.1`-Schritten, `failure_drop = 0.3`

Plots aus GUI-Konfigurationen werden automatisch getrennt:

- `plots/random_graphs/` für Random-Graphen
- `plots/real_world/` für Real-World-Graphen

Wenn jeweils drei Graphen ausgewählt sind, hat jede Plotdatei drei Teilplots.
Dadurch bleiben Random-Graphen und Real-World-Graphen getrennt lesbar.

Die GUI bietet diese Ausführungsmodi:

- `Experiment + Plots`: erzeugt Rohdaten, Summary und Plots.
- `Nur Experimente`: erzeugt nur Rohdaten-CSV-Dateien.
- `Nur Plots`: nutzt vorhandene Rohdaten und erzeugt Summary/Plots.
- `Dry Run`: zeigt nur den geplanten Jobplan.
- `Preflight`: prüft, ob die Konfiguration technisch ausführbar ist.

Die GUI kann zwei Arten von Ausführungsort vorbereiten:

- `Lokal ausführen`: rechnet auf dem Rechner, auf dem Streamlit läuft.
- `Server vorbereiten`: schreibt `gui_config.json` und `run_on_server.sh`, startet
  aber keinen entfernten Prozess.

Für echte Serverausführung gibt es zwei saubere Wege:

- Streamlit direkt auf dem Server starten; dann rechnet die GUI auf dem Server.
- Lokal die Config erzeugen und den angezeigten CLI-Befehl auf dem Server im
  Repository ausführen.

Ein lokaler Browser kann ohne SSH-/Scheduler-Integration nicht von selbst einen
Serverjob starten.

## Auswahl

Die JSON-Dateien steuern:

- `algorithms`: Auswahl aus `edp_paths`, `edp_one_tree`, `edp_multiple_trees`, `ndp_paths`, `ndp_one_tree`, `ndp_multiple_trees`
- `failures`: Auswahl aus `random_link`, `random_node`, `clustered_link`, `clustered_node`
- `datasets`: synthetische Graphen mit `graph_type` (`erdos_renyi` mit `p`,
  `random_regular` mit `degree`) oder GraphML-Topologien
- `runs`, `seed`, `fail_factors`, `failure_starts`, `failure_drop`

`fail_factors`, `failure_starts` und `failure_drop` können pro Dataset gesetzt
werden. Alte oder manuell geschriebene JSON-Dateien dürfen diese Werte auch
global angeben; Dataset-Werte überschreiben solche globalen Fallbacks. Die GUI
schreibt die tatsächlich gewählten Failure-Parameter direkt in das jeweilige
Dataset, damit die Konfiguration eindeutig lesbar bleibt.

Die JSON ist die Basis-Konfiguration. Häufige Parameter können direkt beim
Aufruf überschrieben werden; die effektiv verwendete Konfiguration wird danach
als `used_config.json` in den Ausgabeordner geschrieben.

Auswahlen können auf der CLI eingeschränkt werden:

```powershell
python schritt5_pipeline_automatisierung/pipeline.py --config schritt5_pipeline_automatisierung/config/pilot.json --algorithms edp_paths ndp_paths --failures random_link --datasets synthetic_n8_p04
```

Typische Testvariante ohne JSON-Änderung:

```powershell
python schritt5_pipeline_automatisierung/pipeline.py `
  --config schritt5_pipeline_automatisierung/config/pilot.json `
  --run-name quick_n50_p015 `
  --runs 10 `
  --nodes 50 `
  --p 0.15 `
  --failures random_link random_node `
  --fail-factor 1 2 3
```

Weitere direkte Overrides:

- `--seed 123`
- `--output-root Output/mein_lauf`
- `--failure-start 0.3 0.6 0.9`
- `--failure-drop 0.3`
- `--graph-type erdos_renyi --nodes 25 --p 0.15`
- `--graph-type random_regular --nodes 25 --degree 4`

Graphparameter-Overrides wirken auf die ausgewählten synthetischen Datasets;
GraphML-Real-World-Datasets bleiben dabei unverändert.

CLI-Overrides für `--fail-factor`, `--failure-start` und `--failure-drop`
überschreiben auch dataset-spezifische Werte für den aktuellen Lauf.
Numerisch gleiche Failure-Parameter wie `1` und `1.0` werden für die
Zufallsinitialisierung gleich behandelt.

## Dry Run und Preflight

`--dry-run` zeigt den geplanten Jobplan, ohne Experimente oder Plots zu
erzeugen. Damit lässt sich prüfen, welche Datasets, Fehlertypen,
Graphparameter und Ausgabeordner verwendet würden.

`--preflight` prüft ohne Experimente:

- Run-Anzahl und ausgewählte Algorithmen
- Failureparameter und Metriken
- synthetische Graphparameter (`n`, `p`, (`degree` bei random_regular))
- Existenz von GraphML-Dateien
- Schreibbarkeit des Ausgabeordners

Kurz gesagt:

```text
--dry-run   = Was würde laufen?
--preflight = Kann das so laufen?
```

Bei Erfolg erscheint eine kurze Zusammenfassung, z. B.:

```text
preflight ok datasets=1, jobs=4, output_root=...
```

## Ausgabe

Standardausgabe für `pilot.json`:

```text
schritt5_pipeline_automatisierung/Output/pilot/
  raw/
  plots/
  summaries/
  manifest.json
  used_config.json
```

`manifest.json` dokumentiert die verwendeten Algorithmen, Datasets, Seeds,
Python-Version, erzeugten CSVs und Plot-Dateien. Das ist der zentrale Nachweis
für Repeatability.

Die Rohdaten-CSV-Dateien unter `raw/` verwenden ein langes Format mit einer
Zeile pro Algorithmus, Wiederholung und Failure-Konfiguration. 
Bei Link-Failure zählt `nrFailedEdges` die ausgefallenen Kanten; bei
Node-Failure zählt `nrFailedNodes` die ausgefallenen Knoten und
`nrFailedEdges` die dadurch betroffenen inzidenten Kanten.

## Lange Läufe

`config/full.json` beschreibt die vollständige 1000-Run-Pipeline für drei
synthetische Graphgrößen und drei Real-World-GraphML-Topologien. Für
Serverläufe ist `resume` aktiviert. Unterbrochene Reihen werden dann mit
denselben Parametern fortgesetzt.

Einzelne Phasen:

```powershell
python schritt5_pipeline_automatisierung/pipeline.py --config schritt5_pipeline_automatisierung/config/full.json --only-experiments
python schritt5_pipeline_automatisierung/pipeline.py --config schritt5_pipeline_automatisierung/config/full.json --only-plots
```
