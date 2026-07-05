"""Archetypen-Bibliothek: schreibgeschützte Vorlage-Charaktere aus dem Original.

Analog zu den nativen Settings liegen die Archetypen als JSON-Dateien im Repo
(gamelogic/archetypen) und sind damit für alle Nutzer verfügbar, ohne in der
Datenbank zu liegen. Nutzer können sie ansehen und per „Duplizieren" als
eigenen (editierbaren) Charakter übernehmen.
"""

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.config import settings
from app.services.charakter_init import ergaenze_fehlende_eigenschaften

ARCHETYPEN_DIR: Path = settings.gamelogic_path / "archetypen"


@lru_cache(maxsize=1)
def _index() -> dict[str, dict[str, Any]]:
    """Baut einmalig den Index {id: {id, name, setting, pfad}}. Die id ist der
    Dateiname ohne Endung — stabil und über die Dateimenge eindeutig."""
    eintraege: dict[str, dict[str, Any]] = {}
    if not ARCHETYPEN_DIR.is_dir():
        return eintraege
    for pfad in sorted(ARCHETYPEN_DIR.glob("*.json")):
        try:
            daten = json.loads(pfad.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        name = (daten.get("profil_daten", {}) or {}).get("Name") or pfad.stem
        eintraege[pfad.stem] = {
            "id": pfad.stem,
            "name": name.strip() or pfad.stem,
            "setting": daten.get("active_setting_name") or "Unbekannt",
            "char_gen_completed": bool(daten.get("char_gen_completed", False)),
            "pfad": pfad,
        }
    return eintraege


def liste_archetypen() -> list[dict[str, Any]]:
    """Alle Archetypen als Kurzinfos, sortiert nach Setting, dann Name."""
    eintraege = [
        {k: v for k, v in e.items() if k != "pfad"} for e in _index().values()
    ]
    return sorted(eintraege, key=lambda e: (e["setting"].lower(), e["name"].lower()))


def ordner_uebersicht() -> list[dict[str, Any]]:
    """Ein virtueller Ordner je Setting mit Anzahl der enthaltenen Archetypen."""
    zaehler: dict[str, int] = {}
    for e in _index().values():
        zaehler[e["setting"]] = zaehler.get(e["setting"], 0) + 1
    return [
        {"setting": setting, "anzahl": anzahl}
        for setting, anzahl in sorted(zaehler.items(), key=lambda x: x[0].lower())
    ]


def lade_daten(archetyp_id: str) -> dict[str, Any] | None:
    """Vollständige, normalisierte charakter_daten eines Archetyps (oder None)."""
    eintrag = _index().get(archetyp_id)
    if not eintrag:
        return None
    try:
        daten = json.loads(eintrag["pfad"].read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    daten, _ = ergaenze_fehlende_eigenschaften(daten)
    return daten
