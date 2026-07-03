"""Punkte-Effekte spezieller Handicaps aus handicap_config.json.

"Alt" (schwer) gibt +5 Fertigkeitssteigerungen, "Jung" reduziert die
Start-Steigerungen. Die Config nennt für "Jung" absolute Zielwerte; hier
werden sie als Delta zum Standard (5/12) angewendet, damit bereits
ausgegebene Punkte und eingelöste Handicap-Punkte erhalten bleiben.
Bewegungsweiten-Mali stehen in abgeleitete_effekte.json und fließen erst
in /spiellogik/berechne ein; vermoegen_modifikator ("Arm") wartet auf das
Ausrüstungs-/Startgeld-System.
"""

from app.services.charakter_init import (
    START_ATTRIBUTSTEIGERUNGEN,
    START_FERTIGKEITSSTEIGERUNGEN,
    load_config,
)


def _punkte_deltas(handicap_name: str, stufe: str) -> tuple[int, int]:
    """(Attribut-Delta, Fertigkeits-Delta) des Handicaps, 0/0 wenn keins."""
    cfg = load_config("handicap_config.json")
    basis = handicap_name
    if basis.endswith(("_leicht", "_schwer")):
        basis = basis[:-7]
    effekte = cfg.get("handicap_effects", {}).get(basis, {}).get(stufe) or {}
    standard = cfg.get("standard_werte", {})

    attr_delta = 0
    fert_delta = effekte.get("fertigkeitssteigerungen_bonus", 0)
    if "attributsteigerungen" in effekte:
        attr_delta += effekte["attributsteigerungen"] - standard.get(
            "standard_attributsteigerungen", START_ATTRIBUTSTEIGERUNGEN
        )
    if "fertigkeitssteigerungen" in effekte:
        fert_delta += effekte["fertigkeitssteigerungen"] - standard.get(
            "standard_fertigkeitssteigerungen", START_FERTIGKEITSSTEIGERUNGEN
        )
    return attr_delta, fert_delta


def wende_handicap_punkte_effekte_an(daten: dict, handicap_name: str, stufe: str, vorzeichen: int = 1) -> None:
    """Wendet die Punkte-Effekte an (vorzeichen=1) oder nimmt sie zurück (-1)."""
    attr_delta, fert_delta = _punkte_deltas(handicap_name, stufe)
    for feld, delta in (("attributsteigerungen", attr_delta), ("fertigkeitssteigerungen", fert_delta)):
        if not delta:
            continue
        delta *= vorzeichen
        daten[f"verbleibende_{feld}"] = max(0, daten.get(f"verbleibende_{feld}", 0) + delta)
        daten[f"maximale_{feld}"] = max(0, daten.get(f"maximale_{feld}", 0) + delta)
