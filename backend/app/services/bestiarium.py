"""Bestiarium: schreibgeschützte Kreaturen-Bibliothek für den Kampfsimulator.

Analog zu den Archetypen liegen die Kreaturen als JSON im Repo
(gamelogic/bestiarium/<Setting>.json) und sind damit für alle Nutzer
verfügbar, ohne in der Datenbank zu liegen. Anders als Archetypen sind
Kreaturen aber keine Charaktere: sie haben kein Volk, keine Steigerungen
und ihre Parade/Robustheit steht fest im Buch, statt aus Fertigkeiten
abgeleitet zu werden. Deshalb liefert dieses Modul direkt ein
Kampfprofil (siehe services/kampfprofil.py) statt charakter_daten.

In der JSON-Datei ist ``robustheit`` der gedruckte Gesamtwert inklusive
Panzerung — das Kampfprofil zieht die Panzerung ab, weil der Simulator
PB (Panzerbrechend) gegen die Panzerung verrechnet.
"""

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.config import settings

BESTIARIUM_DIR: Path = settings.gamelogic_path / "bestiarium"

WILDCARD_BENNYS = 3
FERTIGKEIT_NAHKAMPF = "Kämpfen"


@lru_cache(maxsize=1)
def _index() -> dict[str, dict[str, Any]]:
    """Baut einmalig den Index {id: kreatur}. Die id ist im JSON vergeben
    und muss über alle Setting-Dateien hinweg eindeutig sein."""
    eintraege: dict[str, dict[str, Any]] = {}
    if not BESTIARIUM_DIR.is_dir():
        return eintraege
    for pfad in sorted(BESTIARIUM_DIR.glob("*.json")):
        try:
            daten = json.loads(pfad.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        for kreatur in daten.get("kreaturen") or []:
            kreatur_id = kreatur.get("id")
            if not kreatur_id or kreatur_id in eintraege:
                continue
            eintraege[kreatur_id] = {**kreatur, "setting": pfad.stem}
    return eintraege


def liste_kreaturen() -> list[dict[str, Any]]:
    """Kurzinfos aller Kreaturen, sortiert nach Kategorie, dann Name."""
    eintraege = [
        {
            "id": k["id"],
            "name": k["name"],
            "kategorie": k.get("kategorie", ""),
            "setting": k["setting"],
            "wildcard": bool(k.get("wildcard")),
            "parade": k.get("parade", 2),
            "robustheit": k.get("robustheit", 4),
            "panzerung": k.get("panzerung", 0),
            "groesse": k.get("groesse", 0),
            "seite": k.get("seite"),
        }
        for k in _index().values()
    ]
    return sorted(
        eintraege, key=lambda e: (e["kategorie"].lower(), e["name"].lower())
    )


def lade_kreatur(kreatur_id: str) -> dict[str, Any] | None:
    """Vollständiger Eintrag inklusive Spezialfähigkeiten (oder None)."""
    return _index().get(kreatur_id)


def generiere_kampfprofil(kreatur: dict[str, Any]) -> dict[str, Any]:
    """Kreatur → Kampfprofil, wie es src/kampf/domain.ts erwartet."""
    panzerung = kreatur.get("panzerung", 0)
    waffen = [
        {
            "name": w.get("name", ""),
            "fertigkeit": w.get("fertigkeit") or FERTIGKEIT_NAHKAMPF,
            "schaden": w.get("schaden", ""),
            "pb": w.get("pb", 0),
            "mindeststaerke": w.get("mindeststaerke", 0),
            "reichweite": w.get("reichweite", ""),
        }
        for w in kreatur.get("waffen") or []
        if w.get("schaden")
    ]
    return {
        "name": kreatur.get("name", "Kreatur"),
        "attribute": dict(kreatur.get("attribute") or {}),
        "fertigkeiten": dict(kreatur.get("fertigkeiten") or {}),
        "parade": kreatur.get("parade", 2),
        "robustheit": kreatur.get("robustheit", 4) - panzerung,
        "panzerung": panzerung,
        "bennys": WILDCARD_BENNYS if kreatur.get("wildcard") else 0,
        "waffen": waffen,
        "talente": list(kreatur.get("talente") or []),
        "handicaps": list(kreatur.get("handicaps") or []),
        # Spezialfähigkeiten, die der Simulator regeltechnisch auswertet.
        "widerstandsfaehig": kreatur.get("widerstandsfaehig", 0),
        "zaeh": bool(kreatur.get("zaeh")),
        "arkane_fertigkeit": kreatur.get("arkane_fertigkeit", ""),
        "machtpunkte": kreatur.get("machtpunkte", 0),
        "maechte": list(kreatur.get("maechte") or []),
    }
