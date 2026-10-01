"""Build a local HTML guide from the rendered UML diagrams (standard library only)."""

from html import escape
from pathlib import Path
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parent
ITEMS = [
    ("00_gesamtarchitektur", "Gesamtarchitektur", "Überblick", "",
     "GUI-Auswahl oder Pipeline-CLI mit JSON; direkter Aufruf von experiment.py als weiterer Einstieg.",
     "Die Pipeline steuert Experimentkern und Auswertung. Die Komponenten enthalten ihre zentralen Ein- und Ausgaben.",
     "Rohdaten, Summary, Plots und Laufmetadaten. Der gewählte Ausführungsmodus bestimmt den Umfang.",
     "Das Komponentendiagramm zeigt Abhängigkeiten, nicht die zeitliche Reihenfolge. Die Ablaufdiagramme darunter ergänzen diese Sicht."),
    ("01_gui", "GUI", "Module", "gui.py",
     "Auswahl von Graphen, Algorithmen, Ausfallmodellen, Metriken, Wiederholungszahl und Ausführungsmodus.",
     "main(), build_gui_config(), write_gui_config(), mode_to_pipeline_flags(), render_result().",
     "gui_config.json, Fortschritt und Ergebnisanzeige; bei Servervorbereitung zusätzlich run_on_server.sh.",
     "Die GUI schreibt ihre Konfiguration auch vor Dry Run und Preflight. Server vorbereiten startet keinen entfernten Prozess."),
    ("02_pipeline", "Pipeline", "Module", "pipeline.py",
     "Pfad einer JSON-Konfiguration und optionale Überschreibungen, Modusschalter und Fortschritts-Callback.",
     "run_pipeline(), build_experiment_plan(), validate_preflight(), run_experiments(), write_summary_and_plots(), write_manifest().",
     "Dictionary mit Plan und Dateipfaden; bei normalem Lauf raw/, summaries/, plots/, used_config.json und manifest.json.",
     "Die Pipeline-CLI benötigt --config. Nur die separate Experiment-CLI kann ohne JSON gestartet werden. Dry Run erzeugt im Pipeline-Kern keine Ergebnisdateien; Preflight kann den Ausgabeordner anlegen."),
    ("03_experiment", "Experimentsteuerung", "Module", "src/experiment.py",
     "Graphparameter oder GraphML-Pfad, Algorithmen, Ausfallparameter, runs, seed, Resume und Ausgabeordner.",
     "run_experiment_series(), create_graph(), choose_graph_endpoints(), create_instance_rows(), write_rows().",
     "Rohdaten-CSVs und deren Pfade. Eine Ergebniszeile entspricht einem Algorithmus in einer Szene und Failure-Konfiguration.",
     "Eine Szene enthält einen Graphen, Quell-/Zielknoten und Ausfälle. Alle ausgewählten Algorithmen erhalten dieselbe Szene. Bei Zufallsausfällen berechnet dieses Modul round(max(k - 1, 0) * failFactor), mit k = EDP-Anzahl für Kanten und NDP-Anzahl für Knoten. Der failure_rng-Schlüssel enthält Seed, Wiederholung, Typ, Modell, failFactor und failureStart, nicht failureDrop."),
    ("04_failures", "Ausfallerzeugung", "Module", "src/failures.py",
     "Unveränderter Graph, s, d, Ausfalltyp und -modell, gewünschte Ausfallzahl bzw. Clusterparameter sowie ein Zufallsgenerator.",
     "select_failures(), clustered_link_failures(), clustered_node_failures(), node_failures_to_edges().",
     "Zwei Listen: ausgefallene Kanten und ausgefallene Knoten. Bei Kantenausfällen ist die Knotenliste leer.",
     "Knotenausfälle werden als Ausfall aller inzidenten Kanten an das Routing übergeben. Cluster breiten sich aus allen aktuellen Kandidaten aus, nicht nur aus gezogenen Ausfällen. Für Cluster gelten 0 < failure_start <= 1 und 0 < failure_drop <= 1. Das Modul verändert den Graphen nicht und schreibt keine Dateien."),
    ("05_routing_algorithms", "Routingalgorithmen", "Module", "src/routing_algorithms.py",
     "Ursprünglicher Graph, s, d, Liste ausgefallener Kanten und ausgewählte Algorithmen.",
     "run_algorithms() → route_algorithm() → build_structures() → route_structure().",
     "Eine Liste von RoutingResult-Objekten, noch keine CSV-Dateien.",
     "Die sechs Basisverfahren teilen sich die Routingroutine. Registrierte Zusatzverfahren können eigene Runner verwenden. Aufbau und Trunkierung berücksichtigen nicht die Ausfälle; erst die Weiterleitung überspringt ausgefallene Kanten."),
    ("06_strukturaufbau", "Aufbau der Pfade und Bäume", "Routingdetails", "src/routing_algorithms.py",
     "Graph, s, d, berechnete EDPs oder NDPs und Strukturtyp paths, one_tree oder multiple_trees.",
     "build_structures(), _base_tree(), _grow_tree(), truncate_tree().",
     "RoutingStructure-Liste, für das Routing nach der Länge der ursprünglichen Pfade aufsteigend geordnet.",
     "One Tree schützt bei beiden Pfadtypen die übrigen Basispfade. Multiple Trees reserviert gemeinsam Kanten, aber keine inneren Knoten. Schlusskanten nach d liegen außerhalb der gespeicherten Baumgraphen. Trunkierung erfolgt nach dem gesamten Wachstum eines Baums, nicht nach jedem eingefügten Ast."),
    ("07_routing_tiefensuche", "Weiterleitung in einer Struktur", "Routingdetails", "src/routing_algorithms.py",
     "Eine RoutingStructure, s, d, normalisierte Ausfallkanten und das Flag prefer_original_path.",
     "route_structure(), _rooted_children(), _distance_to_exit() und die innere rekursive Funktion visit(node).",
     "Das Tupel (success, hops, route) einer einzelnen Struktur.",
     "Ein Rückweg zählt als Hop, eine übersprungene Ausfallkante nicht. Die Ausgangsdistanzen werden in der vorbereiteten Struktur berechnet, ohne die Ausfälle in der Rangordnung zu berücksichtigen. route_algorithm() addiert anschließend die Hops aller getesteten Strukturen."),
    ("08_result_analysis", "Ergebnisanalyse", "Module", "evaluation/result_analysis.py",
     "Dataset-Verzeichnisse mit Rohdaten sowie erwartete Parametergruppen, Algorithmen, Wiederholungszahl und Plotvorgaben.",
     "load_result_directories(), aggregate_results(), validate_summary(), plot_all_comparisons().",
     "DataFrames und PNG-/SVG-Plots. Die Summary-CSV wird vom aufrufenden pipeline.py geschrieben.",
     "Resilienz umfasst alle Szenen, mittlere Hops und Stretch nur erfolgreiche Routings. Die Plotfunktionen erhalten den aggregierten DataFrame, lesen nicht die Summary-CSV. Vollständig fehlende Gruppen werden mit dem Plan abgeglichen; eindeutige Wiederholungsnummern prüft validate_summary() nicht. Automatische Plotgruppen enthalten höchstens drei Datasets; manuelle Gruppen können abweichen."),
    ("09_environment_check", "Umgebungsprüfung", "Module", "src/environment_check.py",
     "Namen der Bibliotheken, die ein aufrufendes Modul benötigt, und die aktuelle Python-Umgebung.",
     "check_dependencies() kontrolliert die Python-Code-Mindestversion und versucht die angeforderten Imports.",
     "Bei Erfolg None; bei ungeeignetem Python oder fehlgeschlagenem Import ein RuntimeError mit Einrichtungshinweisen.",
     "Die Funktion installiert keine Pakete und erzwingt keinen vollständigen Versionsabgleich mit requirements.txt. Python 3.10 ist die Code-Mindestversion; die festgelegten Referenzpakete benötigen Python 3.11 oder neuer."),
    ("10_routing_datenklassen", "Datenklassen des Routings", "Routingdetails", "src/routing_algorithms.py",
     "Ergebnisse des Strukturaufbaus beziehungsweise der Weiterleitung.",
     "RoutingStructure und RoutingResult sind die beiden tatsächlichen Datenklassen, keine erfundenen Klassen je Algorithmus.",
     "Strukturinformationen für die Weiterleitung und Ergebnisinformationen für experiment.py.",
     "nr_structures zählt die vorbereiteten, nicht nur die getesteten Strukturen. Die Rohdaten-CSV speichert nicht die vollständige route. grown_graph ist eine optionale Diagnosekopie und im normalen Experiment None."),
    ("11_test_pipeline", "Pipeline- und Kerntests", "Tests", "tests/test_pipeline.py",
     "Kleine Testkonfigurationen, Graphen und feste Seeds.",
     "Step5PipelineTest prüft Planung, Parameter, deterministische Szenen, Strukturen und kleine vollständige Läufe.",
     "unittest-Bericht; vorübergehende Ergebnisdateien in Testordnern.",
     "Die Diagrammblöcke fassen unabhängige Testmethoden thematisch zusammen, nicht in einer verpflichtenden Testreihenfolge."),
    ("12_test_gui", "Tests der GUI-Hilfsfunktionen", "Tests", "tests/test_gui.py",
     "Beispielauswahlen und Konfigurationen, ohne interaktive Browserbedienung.",
     "Step5GuiTest prüft Zahlenbereiche, Datasets, Konfigurationsaufbau, Pfade, Modi und Serverbefehle.",
     "unittest-Bericht und temporäre Konfigurationsdateien.",
     "Diese Tests betreffen die Hilfsfunktionen. Die tatsächliche Streamlit-App wird im gesonderten Integrationstest geprüft."),
    ("13_test_feedback_improvements", "Regressionstests der Überarbeitung", "Tests", "tests/test_feedback_improvements.py",
     "Testregistrierungen, Konfigurationen und temporäre Ergebnisdaten.",
     "Prüfung von Defaults, Validierung, Metadaten, fehlenden Gruppen, Fortschritt und Resume.",
     "unittest-Bericht einschließlich gezielter Vergleiche neu berechneter und fortgesetzter Testläufe.",
     "Die Übersicht zeigt die nicht auf Illustrationen bezogenen Prüfbereiche. Sie ist kein Nachweis, dass alle möglichen Erweiterungen oder Konfigurationen korrekt sind."),
    ("14_test_gui_integration", "Streamlit-Integrationstests", "Tests", "tests/test_gui_integration.py",
     "Streamlit-AppTest, isolierte App-Zustände und ein kleiner Pilotlauf.",
     "GuiIntegrationTest: unbekannte Graphart, unveränderte Vorauswahl und vollständiger GUI-Pilot.",
     "unittest-Bericht; Pilot mit vier Rohdaten-CSVs und 24 Plotdateien. Ohne Streamlit werden die Tests übersprungen.",
     "AppTest benötigt keinen externen Browser. Damit werden weder visuelle Browserprüfungen noch Rückmeldungen echter Benutzer ersetzt."),
]


def build():
    navigation = []
    sections = []
    for stem, title, group, module, inputs, process, outputs, note in ITEMS:
        svg = ROOT / "figures" / f"{stem}.svg"
        png = svg.with_suffix(".png")
        if not png.is_file() or not (ROOT / f"{stem}.puml").is_file():
            raise FileNotFoundError(f"Missing source or PNG for {stem}")
        diagram = ET.parse(svg).getroot()
        width, height = diagram.attrib["viewBox"].split()[2:]
        if "Syntax Error" in "".join(diagram.itertext()):
            raise ValueError(f"PlantUML error in {svg}")
        number = stem.split("_", 1)[0]
        navigation.append((group, f'<a href="#{stem}"><span>{number}</span> {escape(title)}</a>'))
        source = (f'<a href="../../{module}"><code>{escape(module)}</code></a>'
                  if module else 'Schritt 5: produktive Module und zentrale Abhängigkeiten')
        sections.append(f'''<section id="{stem}">
<p class="eyebrow">{escape(group)} / {number}</p><h2>{escape(title)}</h2><p>{source}</p>
<dl><dt>Eingabe</dt><dd>{escape(inputs)}</dd><dt>Verarbeitung</dt><dd>{escape(process)}</dd>
<dt>Ausgabe</dt><dd>{escape(outputs)}</dd></dl>
<div class="links"><a href="figures/{stem}.svg">SVG</a><a href="figures/{stem}.png">PNG</a>
<a href="{stem}.puml">PlantUML-Quelle</a></div>
<figure><a href="figures/{stem}.svg"><img src="figures/{stem}.svg" width="{width}" height="{height}" alt="UML: {escape(title)}" loading="lazy"></a></figure>
<p class="note">{escape(note)}</p></section>''')
    nav = []
    for group in ("Überblick", "Module", "Routingdetails", "Tests"):
        nav.append(f'<p class="navgroup">{group}</p>')
        nav.extend(item for category, item in navigation if category == group)
    html = '''<!doctype html><html lang="de"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>UML | Experimentierumgebung</title>
<style>
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;color:#20292d;background:#fff;font:16px/1.6 Arial,sans-serif;letter-spacing:0}
a{color:#27686a;text-underline-offset:3px}a:hover{color:#7d4d16}a:focus-visible{outline:2px solid #27686a;outline-offset:4px}
nav{position:fixed;inset:0 auto 0 0;width:270px;overflow:auto;border-right:1px solid #d7dfe0;background:#f4f7f7;padding:20px 18px}
nav a{display:block;padding:6px 0;text-decoration:none;line-height:1.35;font-size:14px}nav span{color:#68777c;font-size:12px;margin-right:6px}
.navgroup{margin:22px 0 6px;font-size:12px;font-weight:bold;text-transform:uppercase;color:#56646b}.brand{font-size:18px;font-weight:bold;margin:0}
main{margin-left:270px;max-width:1700px;padding:36px 44px}header{border-bottom:2px solid #27686a;padding-bottom:22px}h1{font-size:30px;line-height:1.2;margin:0 0 14px}h2{font-size:24px;line-height:1.3;margin:4px 0 12px}
header p{max-width:920px;margin:8px 0}section{padding:32px 0 40px;border-bottom:1px solid #ccd6d9;scroll-margin-top:20px}.eyebrow{font-size:12px;color:#68777c;text-transform:uppercase;margin:0}
dl{display:grid;grid-template-columns:115px minmax(0,1fr);gap:10px 18px;max-width:1000px}dt{font-weight:bold}dd{margin:0}code{font:14px Consolas,monospace;overflow-wrap:anywhere}
.links{display:flex;gap:24px;margin:22px 0 14px;font-size:14px}figure{margin:0;overflow:auto}figure img{display:block;max-width:100%;height:auto}
.note{max-width:1000px;border-left:3px solid #b49a60;padding:5px 0 5px 16px;color:#4e5a60}footer{padding:24px 0;color:#68777c;font-size:14px}
@media(max-width:850px){nav{position:static;width:100%;max-height:250px;border-right:0;border-bottom:1px solid #ccd6d9}main{margin:0;padding:24px 18px}h1{font-size:26px}h2{font-size:22px}dl{grid-template-columns:1fr;gap:2px}dd{margin-bottom:12px}}
@media print{nav,.links{display:none}main{margin:0;padding:0}section{break-before:page}figure img{max-height:220mm;object-fit:contain}header{border:0}}
</style></head><body><nav aria-label="Diagrammübersicht"><p class="brand">UML · Schritt 5</p>'''
    html += "\n".join(nav)
    html += '''</nav><main><header><h1>Architektur der Experimentierumgebung</h1>
<p>Gesamtübersicht und Ablaufdiagramme der aktuellen Implementierung, ohne Illustrationsmodul.
Die sieben produktiven Module sind einzeln dargestellt; Routingdetails und die vier Testmodule ergänzen die Übersicht.</p>
<p>In den Aktivitätsdiagrammen stehen Rauten für Entscheidungen und Pfeile für den Ablauf.
Kreis und Abschlusskreis markieren Anfang und Ende. Die Diagramme zeigen die wesentlichen Schritte, nicht jede Fehlerprüfung.</p>
<p><a href="README.txt">Erläuterungen und erneute Erzeugung</a></p></header>'''
    html += "\n".join(sections)
    html += '''<footer>Quellenabgleich: 20.09.2026. Die Diagramme beschreiben den Code, nicht einen neuen Testlauf.
SVG und PNG wurden aus denselben PlantUML-Quellen erzeugt.</footer></main></body></html>'''
    (ROOT / "index.html").write_text(html, encoding="utf-8")
    print(f"Created index.html for {len(ITEMS)} diagrams")


if __name__ == "__main__":
    build()
