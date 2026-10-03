"""Migration: DSA-Ausprägungen der Mächte strukturieren (Savage Aventurien).

Bisher standen alle potentiellen DSA-Zauber/Liturgien einer Macht als
"Name: Text"-Zeilen in der Beschreibung, dazu die Namensliste dsa_trappings.
Danach trägt jede betroffene Macht

    "auspraegungen": [{"name": ..., "beschreibung": ...}, ...]

und die Beschreibung enthält nur noch Regeltext und Modifikatoren. Welche
Ausprägungen ein Charakter beherrscht, steht in
charakter_daten["macht_auspraegungen"].

Sammelzeilen wie "Faxius (Elementarstrahl)" beschreiben eine ganze Familie;
ihr Text wird an die konkreten Varianten (Ignifaxius, Frigifaxius, …)
vergeben, die sonst ohne Beschreibung blieben.

Aufruf aus backend/:
    python scripts/migriere_macht_auspraegungen.py            # Probelauf
    python scripts/migriere_macht_auspraegungen.py --apply    # schreibt
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from app.config import settings  # noqa: E402

NATIVE_SETTINGS = settings.gamelogic_path / "settings"

# Sammelzeile -> Muster der Varianten, die ihren Text übernehmen
FAMILIEN = {
    "Elementarwand": r"^(Eis|Stein|Sturm|Wellen|Flammen)wand$|^Feuerwall$",
    "Attributo (Eigenschaft steigern)": r"^Attributo \(",
    "Mal (Schwächung)": r"^Mal der ",
    "Sphaero (Elementarball)": r"sphaero$",
    "Bannfluch": r"^Bannfluch \(",
    "Invocatio (Dämonenbeschwörung)": r"^Invocatio ",
    "Pfeil des Elements": r"pfeil$",
    "Leib-Zauber (Elementarpanzer)": r"leib$",
    "Faxius (Elementarstrahl)": r"faxius$",
    "Gramma (Bannkreis)": r"gramma$",
    "Diener der Elemente": r"^Diener de[rs] ",
    "Diener des Rattenkindes beschwören": r"Diener des Rattenkindes$",
    "Tierruf": r"ruf$",
    "Heerscharen herbeirufen": r"^Herbeirufung ",
}

_ZEILE = re.compile(r"^([^\s:][^:]{0,80}): (.*)$")


def _basis(name: str) -> str:
    """'Angriffslust (Kampfrausch)' -> 'Angriffslust'."""
    return re.sub(r"\s*\([^)]*\)$", "", name)


def migriere_macht(macht: dict) -> bool:
    """Beschreibung einer Macht in Kerntext + auspraegungen zerlegen."""
    dsa = macht.get("dsa_trappings")
    if dsa is None or "auspraegungen" in macht:
        return False

    zeilen = (macht.get("beschreibung") or "").split("\n")

    def kandidat(i: int, zeile: str) -> re.Match | None:
        # "Name: Text"-Zeilen ab der zweiten Zeile (die erste ist immer der
        # Regeltext), nicht eingerückt (Modifikatoren sind es)
        treffer = _ZEILE.match(zeile) if i > 0 else None
        return treffer if treffer and treffer.group(1) != "Modifikatoren" else None

    def bekannt(name: str) -> bool:
        return name in dsa or name in FAMILIEN or any(_basis(n) == _basis(name) for n in dsa)

    # Ein Absatz mit mindestens einer bekannten Ausprägung ist ein
    # Ausprägungsblock — dort zählen auch Zeilen ohne DSA-Namen ("Merkmalsbann")
    absatz_von: list[int] = []
    absatz = 0
    for zeile in zeilen:
        if not zeile.strip():
            absatz += 1
        absatz_von.append(absatz)
    bloecke = {
        absatz_von[i] for i, z in enumerate(zeilen)
        if (t := kandidat(i, z)) and bekannt(t.group(1))
    }

    text: dict[str, str] = {}
    reihenfolge: list[str] = []
    kern: list[str] = []
    for i, zeile in enumerate(zeilen):
        treffer = kandidat(i, zeile)
        if treffer and absatz_von[i] in bloecke:
            name = treffer.group(1)
            text[name] = treffer.group(2).strip()
            reihenfolge.append(name)
        else:
            kern.append(zeile)

    eintraege: dict[str, str] = {}

    def neu(name: str, beschreibung: str) -> None:
        if name not in eintraege:
            eintraege[name] = beschreibung

    offen = [n for n in dsa if n not in text]
    for name in reihenfolge:
        # Textzeile mit Zusatz zu einem DSA-Namen: "Angriffslust (Kampfrausch)"
        # ist dieselbe Ausprägung wie "Angriffslust" -> Textname gewinnt
        gleiche = [n for n in offen if n == _basis(name) and n != name]
        for n in gleiche:
            offen.remove(n)
        muster = FAMILIEN.get(name)
        varianten = [n for n in offen if muster and re.search(muster, n)]
        if varianten and name not in dsa:
            for n in varianten:
                neu(n, text[name])
                offen.remove(n)
        else:
            neu(name, text[name])
            for n in varianten:
                neu(n, text[name])
                offen.remove(n)

    for name in offen:
        # "Schleichende Fäulnis (Pflanzen)" erbt den Text von "Schleichende Fäulnis"
        neu(name, text.get(_basis(name), ""))

    beschreibung = re.sub(r"\n{3,}", "\n\n", "\n".join(kern)).strip()
    macht["beschreibung"] = beschreibung
    macht["auspraegungen"] = [{"name": n, "beschreibung": b} for n, b in eintraege.items()]
    del macht["dsa_trappings"]
    return True


def migriere_setting(pfad: Path, apply: bool, sichern: bool) -> None:
    daten = json.loads(pfad.read_text(encoding="utf-8"))
    geaendert = [name for name, m in (daten.get("maechte") or {}).items()
                 if isinstance(m, dict) and migriere_macht(m)]
    if not geaendert:
        return
    anzahl = sum(len(daten["maechte"][n]["auspraegungen"]) for n in geaendert)
    print(f"{pfad.name}: {len(geaendert)} Mächte, {anzahl} Ausprägungen")
    if apply:
        # mitgelieferte Settings sind versioniert, eigene nicht
        if sichern:
            shutil.copy2(pfad, pfad.with_suffix(f".json.bak-{datetime.now():%Y%m%d%H%M%S}"))
        pfad.write_text(json.dumps(daten, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--apply", action="store_true", help="Änderungen schreiben")
    args = parser.parse_args()

    for verzeichnis, sichern in ((NATIVE_SETTINGS, False), (settings.custom_settings_path, True)):
        if verzeichnis.is_dir():
            for pfad in sorted(verzeichnis.glob("*.json")):
                migriere_setting(pfad, args.apply, sichern)
    if not args.apply:
        print("Probelauf — mit --apply schreiben.")


if __name__ == "__main__":
    main()
