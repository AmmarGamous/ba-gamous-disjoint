"""Prüft die Python-Umgebung vor dem Laden der Experimentmodule."""

import importlib
from pathlib import Path
import sys


def check_dependencies(modules=("networkx", "pandas", "matplotlib"), gui=False):
    """Meldet ungeeignetes Python und fehlende oder nicht ladbare Bibliotheken."""
    if sys.version_info < (3, 10):
        raise RuntimeError(
            "Schritt 5 benötigt mindestens Python 3.10; die festgelegten "
            "Paketversionen benötigen Python 3.11 oder neuer. "
            "Bitte eine passende virtuelle Umgebung anlegen."
        )
    requirements = Path(__file__).resolve().parents[1] / "Dokumentation" / "requirements.txt"
    for name in modules:
        try:
            importlib.import_module(name)
        except (ImportError, OSError) as exc:
            raise RuntimeError(
                f"Die Bibliothek {name!r} konnte nicht geladen werden: {exc}. "
                f'Installation in einer passenden Umgebung: python -m pip install -r "{requirements}"'
            ) from exc
