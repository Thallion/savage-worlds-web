"""Migration: die beiden "Größe -1"-Handicaps zu einem zusammenführen.

Savage Pathfinder und Savage Aventurien führten dasselbe Handicap doppelt
("Größe -1 (Reduzierte Robustheit)" und "Größe -1 (Reduzierte Größe und
Robustheit)"). Beide heißen jetzt "Größe -1" und wirken über groesse: -1.

Gespeicherte Charaktere tragen die alten Namen an mehreren Stellen und —
wichtiger — einen eingefrorenen Snapshot ihres Volkes mit
groesse_modifikator: -1 *und* dem Handicap in auto_handicaps. Ohne
Korrektur des Snapshots würde die Größe nach der Umbenennung doppelt
zählen. Dasselbe gilt für selbst angelegte Settings unter data/settings/.

Aufruf aus backend/:
    python scripts/migriere_groesse_handicap.py            # Probelauf
    python scripts/migriere_groesse_handicap.py --apply    # schreibt
"""

from __future__ import annotations

import argparse
import json
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from app.config import settings  # noqa: E402

ALT_NAMEN = (
    "Größe -1 (Reduzierte Robustheit)",
    "Größe -1 (Reduzierte Größe und Robustheit)",
)
NEU = "Größe -1"
BESCHREIBUNG = "Größe und Robustheit sinken um 1"
BETROFFENE_SETTINGS = ("Savage Pathfinder", "Savage Aventurien")


def _liste(werte: list, protokoll: list[str], wo: str) -> tuple[list, bool]:
    """Alte Namen umbenennen, dabei entstehende Duplikate entfernen."""
    neu, geaendert = [], False
    for wert in werte:
        if wert in ALT_NAMEN:
            geaendert = True
            protokoll.append(f"{wo}: {wert!r} -> {NEU!r}")
            wert = NEU
        if wert == NEU and NEU in neu:
            protokoll.append(f"{wo}: doppeltes {NEU!r} entfernt")
            continue
        neu.append(wert)
    return neu, geaendert


def _dict(tabelle: dict, protokoll: list[str], wo: str) -> bool:
    """Nach Handicap-Namen geschlüsselte Tabelle umbenennen."""
    geaendert = False
    for alt in ALT_NAMEN:
        if alt not in tabelle:
            continue
        eintrag = tabelle.pop(alt)
        protokoll.append(f"{wo}: Schlüssel {alt!r} -> {NEU!r}")
        geaendert = True
        if isinstance(eintrag, dict):
            eintrag = {**eintrag, "name": NEU}
            if eintrag.get("beschreibung") in (
                "Reduzierte Robustheit um 1",
                "Reduzierte Größe und Robustheit um 1",
            ):
                eintrag["beschreibung"] = BESCHREIBUNG
        # bereits vorhandener Eintrag unter dem neuen Namen gewinnt
        tabelle.setdefault(NEU, eintrag)
    return geaendert


def migriere_charakter(daten: dict, protokoll: list[str]) -> bool:
    geaendert = False

    if isinstance(daten.get("selected_handicaps"), list):
        daten["selected_handicaps"], g = _liste(
            daten["selected_handicaps"], protokoll, "selected_handicaps"
        )
        geaendert |= g

    overrides = daten.get("setting_overrides") or {}
    if isinstance(overrides.get("handicaps"), dict):
        geaendert |= _dict(overrides["handicaps"], protokoll, "setting_overrides.handicaps")
    geloescht = overrides.get("geloescht") or {}
    if isinstance(geloescht.get("handicaps"), list):
        geloescht["handicaps"], g = _liste(
            geloescht["handicaps"], protokoll, "setting_overrides.geloescht.handicaps"
        )
        geaendert |= g

    elemente = daten.get("selected_elements") or {}
    if isinstance(elemente.get("handicaps"), dict):
        geaendert |= _dict(elemente["handicaps"], protokoll, "selected_elements.handicaps")

    volk_effekte = daten.get("volk_effekte") or {}
    if isinstance(volk_effekte.get("handicaps"), list):
        volk_effekte["handicaps"], g = _liste(
            volk_effekte["handicaps"], protokoll, "volk_effekte.handicaps"
        )
        geaendert |= g

    # Eingefrorener Volks-Snapshot: Größe kommt künftig aus dem Handicap,
    # der groesse_modifikator des Volkes würde sie sonst doppelt zählen
    for volk_name, volk in (daten.get("voelker_selected") or {}).items():
        if not isinstance(volk, dict):
            continue
        effekte = volk.get("effects")
        if not isinstance(effekte, dict):
            continue
        wo = f"voelker_selected.{volk_name}"
        if isinstance(effekte.get("auto_handicaps"), list):
            effekte["auto_handicaps"], g = _liste(
                effekte["auto_handicaps"], protokoll, f"{wo}.auto_handicaps"
            )
            geaendert |= g
        if NEU in (effekte.get("auto_handicaps") or []) and effekte.get("groesse_modifikator") == -1:
            effekte["groesse_modifikator"] = 0
            protokoll.append(f"{wo}: groesse_modifikator -1 -> 0 (Größe kommt aus dem Handicap)")
            geaendert = True

    return geaendert


def migriere_setting(setting: dict, protokoll: list[str]) -> bool:
    geaendert = False
    if isinstance(setting.get("handicaps"), dict):
        geaendert |= _dict(setting["handicaps"], protokoll, "handicaps")

    for volk_name, volk in (setting.get("voelker") or {}).items():
        if not isinstance(volk, dict):
            continue
        effekte = volk.get("effects")
        if isinstance(effekte, dict):
            wo = f"voelker.{volk_name}"
            if isinstance(effekte.get("auto_handicaps"), list):
                effekte["auto_handicaps"], g = _liste(
                    effekte["auto_handicaps"], protokoll, f"{wo}.auto_handicaps"
                )
                geaendert |= g
            if NEU in (effekte.get("auto_handicaps") or []) and effekte.get("groesse_modifikator") == -1:
                effekte["groesse_modifikator"] = 0
                protokoll.append(f"{wo}: groesse_modifikator -1 -> 0")
                geaendert = True
        # rein beschreibende Liste im Volk
        if isinstance(volk.get("handicaps"), list):
            volk["handicaps"], g = _liste(
                volk["handicaps"], protokoll, f"voelker.{volk_name}.handicaps"
            )
            geaendert |= g
    return geaendert


def _db_pfad() -> Path:
    url = settings.database_url
    if not url.startswith("sqlite"):
        raise SystemExit(f"Nur SQLite unterstützt, nicht: {url}")
    return Path(url.split("///", 1)[1]) if "///" in url else Path("data/chargen.db")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Änderungen schreiben (sonst Probelauf)")
    parser.add_argument("--db", type=Path, help="Pfad zur SQLite-DB (Standard: aus der Config)")
    args = parser.parse_args()

    db = args.db or _db_pfad()
    if not db.is_absolute():
        db = BACKEND / db
    modus = "SCHREIBE" if args.apply else "PROBELAUF (nichts wird geschrieben)"
    print(f"== {modus} ==\nDatenbank: {db}")

    charaktere = 0
    if db.exists():
        if args.apply:
            sicherung = db.with_suffix(f".{datetime.now():%Y%m%d-%H%M%S}.bak")
            shutil.copy2(db, sicherung)
            print(f"Sicherung: {sicherung}")

        conn = sqlite3.connect(db)
        try:
            zeilen = conn.execute("select id, char_name, charakter_daten from charaktere").fetchall()
            for char_id, name, rohdaten in zeilen:
                if not any(alt in rohdaten for alt in ALT_NAMEN):
                    continue
                daten = json.loads(rohdaten)
                protokoll: list[str] = []
                if not migriere_charakter(daten, protokoll):
                    continue
                charaktere += 1
                print(f"\nCharakter {char_id} ({name}):")
                for zeile in protokoll:
                    print(f"  - {zeile}")
                if args.apply:
                    conn.execute(
                        "update charaktere set charakter_daten = ? where id = ?",
                        (json.dumps(daten, ensure_ascii=False), char_id),
                    )
            if args.apply:
                conn.commit()
        finally:
            conn.close()
    else:
        print("Datenbank nicht gefunden - überspringe Charaktere.")

    eigene = 0
    verzeichnis = BACKEND / "data" / "settings"
    for pfad in sorted(verzeichnis.glob("*.json")) if verzeichnis.exists() else []:
        rohdaten = pfad.read_text(encoding="utf-8")
        if not any(alt in rohdaten for alt in ALT_NAMEN):
            continue
        setting = json.loads(rohdaten)
        protokoll: list[str] = []
        if not migriere_setting(setting, protokoll):
            continue
        eigene += 1
        print(f"\nEigenes Setting {pfad.name}:")
        for zeile in protokoll:
            print(f"  - {zeile}")
        if args.apply:
            shutil.copy2(pfad, pfad.with_suffix(f".{datetime.now():%Y%m%d-%H%M%S}.bak"))
            pfad.write_text(json.dumps(setting, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"\n{charaktere} Charakter(e), {eigene} eigene(s) Setting(s) betroffen.")
    if not args.apply and (charaktere or eigene):
        print("Zum Schreiben erneut mit --apply aufrufen.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
