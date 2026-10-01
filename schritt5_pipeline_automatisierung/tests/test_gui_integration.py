"""Optionale Streamlit-AppTests für Vorauswahl und einen vollständigen GUI-Lauf."""

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


PIPELINE_ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(importlib.util.find_spec("streamlit"), "Benötigt Streamlit aus requirements.txt")
class GuiIntegrationTest(unittest.TestCase):
    """Prüft die Streamlit-Oberfläche ohne einen externen Browser."""

    def test_unknown_graph_kind_is_not_treated_as_real_world(self):
        """Ein neuer Anzeigename allein darf keinen falschen GraphML-Datensatz erzeugen."""
        from streamlit.testing.v1 import AppTest

        script = f'''
import sys
from unittest.mock import patch
sys.path.insert(0, {str(PIPELINE_ROOT)!r})
import gui
import streamlit as st
st.session_state.setdefault("add_graph_open", True)
st.session_state.setdefault("graph_datasets", [])
gui.GRAPH_TYPE_LABELS = {{**gui.GRAPH_TYPE_LABELS, "complete_graph": "Vollständiger Graph"}}
gui.main()
'''
        app = AppTest.from_string(script).run(timeout=30)
        next(widget for widget in app.radio if widget.label == "Graph-Typ").set_value("complete_graph").run(timeout=30)
        self.assertEqual(len(app.exception), 0)
        self.assertTrue(any("kein Eingabedialog" in error.value for error in app.error))
        self.assertFalse(any(widget.label == "Real-World Graph" for widget in app.selectbox))
        self.assertFalse(any(button.label == "Graph speichern" for button in app.button))
        self.assertEqual(app.session_state["graph_datasets"], [])

    def test_extensions_remain_unselected_in_gui(self):
        """Neue Optionen erscheinen, verändern jedoch nicht die Basis-Vorauswahl."""
        from streamlit.testing.v1 import AppTest

        script = f'''
import sys
from unittest.mock import patch
sys.path.insert(0, {str(PIPELINE_ROOT)!r})
import gui
with patch.object(gui.pipeline, "ALGORITHMS", gui.pipeline.ALGORITHMS + ("extra",)), patch.dict(gui.pipeline.FAILURE_COMBINATIONS, {{"extra_link": ("random", "link")}}), patch.dict(gui.ALGORITHM_LABELS, {{"extra": "Zusatzalgorithmus"}}), patch.dict(gui.FAILURE_LABELS, {{"extra_link": "Zusatzmodell"}}):
    gui.main()
'''
        app = AppTest.from_string(script).run(timeout=30)
        self.assertEqual(len(app.exception), 0)
        algorithms = next(widget for widget in app.multiselect if widget.label == "Algorithmen")
        failures = next(widget for widget in app.multiselect if widget.label == "Fehlertypen")
        self.assertEqual(len(algorithms.value), 6)
        self.assertEqual(len(failures.value), 4)
        self.assertNotIn("extra", algorithms.value)
        self.assertNotIn("extra_link", failures.value)
        self.assertIn("Zusatzalgorithmus", algorithms.options)
        self.assertIn("Zusatzmodell", failures.options)

    def test_gui_pilot_produces_results(self):
        """Ein kleiner GUI-Lauf erzeugt Rohdaten, Plots und erweiterte Metadaten."""
        from streamlit.testing.v1 import AppTest

        script = f'''
import sys
sys.path.insert(0, {str(PIPELINE_ROOT)!r})
import gui
import streamlit as st
st.session_state.setdefault("graph_datasets", [{{
    "name": "gui_small", "display_name": "GUI-Test", "type": "synthetic",
    "graph_type": "erdos_renyi", "nodes": 8, "p": 0.4,
    "fail_factors": [0.8], "failure_starts": [0.3], "failure_drop": 0.3
}}])
gui.main()
'''
        with tempfile.TemporaryDirectory() as directory:
            app = AppTest.from_string(script).run(timeout=30)
            self.assertEqual(len(app.exception), 0)
            next(widget for widget in app.text_input if widget.label == "Ausgabeordner").input(directory)
            next(widget for widget in app.number_input if widget.label == "Läufe").set_value(1)
            next(button for button in app.button if button.label == "Experiment starten").click().run(timeout=60)
            self.assertEqual(len(app.exception), 0)
            self.assertEqual(len(app.error), 0)
            manifest = json.loads((Path(directory) / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(len(manifest["generated_csvs"]), 4)
            self.assertEqual(len(manifest["plots"]), 24)
            self.assertIn("code_fingerprint", manifest["provenance"])
            progress = app.get("progress")
            self.assertEqual(len(progress), 1)
            self.assertEqual(progress[0].proto.value, 100)
            self.assertEqual(progress[0].proto.text, "Pipeline abgeschlossen")


if __name__ == "__main__":
    unittest.main()
