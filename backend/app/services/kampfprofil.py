"""Kampfprofil für den Kampfsimulator (Frontend: src/kampf).

Liefert die kampfrelevanten Werte eines Charakters in kompakter Form:

    {
        "name": "Amiri",
        "attribute": {"Stärke": "W10", ...},
        "fertigkeiten": {"Kämpfen": "W8", ...},       # nur gelernte
        "parade": 6,
        "robustheit": 7,                              # ohne Panzerung
        "panzerung": 1,
        "bennys": 3,
        "waffen": [{"name": ..., "fertigkeit": ..., "schaden": ..., "pb": ...,
                    "mindeststaerke": ..., "reichweite": ...}],
        "talente": [...],                             # inkl. Abstammungs-Talente
        "handicaps": [...],                           # ohne Stufen-Suffix
    }

Parade, Robustheit, Panzerung und Bennys stammen aus /spiellogik/berechne,
damit Talent-, Handicap-, Volks- und Cyberware-Boni identisch zum
Charakterbogen einfließen. Die Robustheit wird ohne Panzerung geliefert,
weil der Simulator Panzerbrechend (PB) gegen die Panzerung verrechnet.
"""

from app.services.statblock import _basisname
from app.services.volk_effekte import gewaehltes_volk
from app.services.volk_wahlen import arkane_fertigkeit_aus_ah

UNGELERNT_MODIFIKATOR = -2
WAFFEN_KATEGORIE = "Waffe"
WAFFENTYP_FERNKAMPF = "Fernkampf"
FERTIGKEIT_NAHKAMPF = "Kämpfen"
FERTIGKEIT_FERNKAMPF = "Schießen"


def _wuerfel(wert: int, modifier: int = 0) -> str:
    if modifier:
        return f"W{wert}{modifier:+d}"
    return f"W{wert}"


def _zahl(wert) -> int:
    """Wandelt Katalogangaben wie "2", 2 oder "-" in eine Ganzzahl."""
    try:
        return int(str(wert).replace("–", "-").replace("−", "-"))
    except (TypeError, ValueError):
        return 0


def _seiten(wuerfel) -> int:
    """Seitenzahl aus einer Angabe wie "W8"; 0 bei "-" oder fehlender Angabe."""
    text = str(wuerfel or "").strip().upper().lstrip("WD")
    return _zahl(text.split("+")[0].split("-")[0]) if text else 0


def _attribute(daten: dict) -> dict[str, str]:
    return {
        name: _wuerfel(attr.get("wert", 4), attr.get("modifier", 0))
        for name, attr in daten.get("attribute", {}).items()
    }


def _fertigkeiten(daten: dict) -> dict[str, str]:
    gelernt = {}
    for name, fert in daten.get("fertigkeiten", {}).items():
        wuerfel = fert.get("wuerfel", {})
        if wuerfel.get("modifier", 0) == UNGELERNT_MODIFIKATOR:
            continue
        gelernt[name] = _wuerfel(wuerfel.get("value", 4), wuerfel.get("modifier", 0))
    return gelernt


def _merkmale(daten: dict, setting: dict, feld: str) -> list[str]:
    """Gewählte Talente bzw. Handicaps plus die der Abstammung, normalisiert."""
    auswahl_feld = "selected_talente" if feld == "talente" else "selected_handicaps"
    namen = [_basisname(e) for e in daten.get(auswahl_feld, [])]
    _, volk_data = gewaehltes_volk(daten, setting)
    if volk_data:
        namen += [_basisname(e) for e in volk_data.get(feld) or []]
    return list(dict.fromkeys(n for n in namen if n))


def _waffen(daten: dict, setting: dict) -> list[dict]:
    katalog = setting.get("ausruestung", {})
    waffen = []
    for name, eintrag in sorted(daten.get("ausruestung_selected", {}).items()):
        if eintrag.get("anzahl", 0) <= 0:
            continue
        item = katalog.get(name) or {}
        if item.get("kategorie") != WAFFEN_KATEGORIE:
            continue
        eigenschaften = item.get("eigenschaften") or {}
        schaden = str(eigenschaften.get("Schaden") or "").strip()
        if not schaden or schaden == "-":
            continue
        fernkampf = item.get("typ") == WAFFENTYP_FERNKAMPF
        waffen.append(
            {
                "name": name,
                "fertigkeit": FERTIGKEIT_FERNKAMPF if fernkampf else FERTIGKEIT_NAHKAMPF,
                "schaden": schaden,
                "pb": _zahl(eigenschaften.get("PB")),
                "mindeststaerke": _seiten(item.get("mindeststaerke")),
                "reichweite": str(eigenschaften.get("Reichweite") or "") if fernkampf else "",
            }
        )
    return waffen


def _arkane_fertigkeit(daten: dict, setting: dict) -> str:
    """Fertigkeitsname des Arkanen Hintergrunds, z. B. "Zaubern".

    Der Klammerzusatz aus der AH-Beschreibung ("Zaubern (Verstand)") wird
    entfernt, damit der Name zum Fertigkeitsschlüssel des Charakters passt.
    """
    talente = setting.get("talente", {})
    for eintrag in daten.get("selected_talente", []):
        if not eintrag.startswith("AH"):
            continue
        # Der Klammerzusatz gehört bei AH-Talenten zum Namen ("AH (Magie)"),
        # deshalb hier nicht über _basisname kürzen.
        talent = talente.get(eintrag) or talente.get(_basisname(eintrag)) or {}
        fertigkeit = arkane_fertigkeit_aus_ah(talent)
        if fertigkeit:
            # "Zaubern (Verstand)" -> "Zaubern"
            return _basisname(fertigkeit)
    return ""


def generiere_kampfprofil(daten: dict, setting: dict, werte: dict) -> dict:
    """werte: das Ergebnis von /spiellogik/berechne für dieselben daten."""
    panzerung = werte.get("panzerung", 0)
    return {
        "name": daten.get("profil_daten", {}).get("Name") or "Unbenannter Charakter",
        "attribute": _attribute(daten),
        "fertigkeiten": _fertigkeiten(daten),
        "parade": werte.get("parade", 2),
        "robustheit": werte.get("robustheit", 4) - panzerung,
        "panzerung": panzerung,
        "bennys": werte.get("bennys", 3),
        "waffen": _waffen(daten, setting),
        "talente": _merkmale(daten, setting, "talente"),
        "handicaps": _merkmale(daten, setting, "handicaps"),
        # Mächte: der Simulator wertet nur die in kampf/maechte.ts
        # hinterlegten Namen aus, liefert aber alle gewählten mit.
        "arkane_fertigkeit": _arkane_fertigkeit(daten, setting),
        "machtpunkte": werte.get("machtpunkte", 0),
        "maechte": [_basisname(m) for m in daten.get("selected_maechte", [])],
    }
