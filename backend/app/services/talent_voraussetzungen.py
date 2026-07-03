"""Prüfung von Talent-Voraussetzungen und Mächte-Kapazität.

Voraussetzungs-Strings in den Setting-JSONs (Beispiele aus SWAE):
  "WIL W8"                     Attribut-Kürzel + Mindestwürfel
  "Kämpfen W6"                 Fertigkeit + Mindestwürfel (optional mit "+")
  "Athletik oder Schießen W8"  Oder-Alternativen
  "AH"                         beliebiger arkaner Hintergrund
  "Anführer"                   anderes Talent

Unbekannte Formate blockieren nicht (lenient), damit exotische Settings
nutzbar bleiben.
"""

import re

ATTRIBUT_KUERZEL = {
    "STÄ": "Stärke",
    "GES": "Geschicklichkeit",
    "KON": "Konstitution",
    "VER": "Verstand",
    "WIL": "Willenskraft",
}

RANG_NAMEN = {"A": "Anfänger", "F": "Fortgeschritten", "V": "Veteran", "H": "Heroisch", "L": "Legendär"}

_EIGENSCHAFT_RE = re.compile(r"^(?P<namen>.+?)\s+W(?P<wert>\d+)\+?$")


def hat_arkanen_hintergrund(daten: dict, setting_talente: dict) -> bool:
    for name in daten.get("selected_talente", []):
        talent = setting_talente.get(name, {})
        if talent.get("neue_maechte", 0) > 0 or name.startswith("AH"):
            return True
    return False


def macht_kapazitaet(daten: dict, setting_talente: dict) -> tuple[int, int]:
    """(Mächte-Slots, Machtpunkte) aus den gewählten Talenten (AH, Neue Mächte, ...)."""
    slots = punkte = 0
    for name in daten.get("selected_talente", []):
        talent = setting_talente.get(name, {})
        slots += talent.get("neue_maechte", 0)
        punkte += talent.get("machtpunkte", 0)
    return slots, punkte


def _eigenschaft_erfuellt(name: str, wert: int, daten: dict) -> bool:
    name = ATTRIBUT_KUERZEL.get(name, name)
    attr = daten.get("attribute", {}).get(name)
    if attr is not None:
        return attr.get("wert", 4) >= wert
    fert = daten.get("fertigkeiten", {}).get(name)
    if fert is not None:
        wuerfel = fert.get("wuerfel", {})
        if wuerfel.get("modifier", 0) == -2:  # ungelernt
            return False
        return wuerfel.get("value", 4) >= wert
    return True  # unbekannte Eigenschaft: nicht blockieren


def _einzelne_erfuellt(voraussetzung: str, daten: dict, setting_talente: dict) -> bool:
    v = voraussetzung.strip()
    if v == "AH" or v.startswith(("AH ", "AH(", "AH:")):
        return hat_arkanen_hintergrund(daten, setting_talente)

    m = _EIGENSCHAFT_RE.match(v)
    if m:
        wert = int(m.group("wert"))
        namen = re.split(r"\s+oder\s+|,\s*", m.group("namen"))
        return any(_eigenschaft_erfuellt(n.strip(), wert, daten) for n in namen)

    if v in setting_talente:
        return v in daten.get("selected_talente", [])

    return True  # unbekanntes Format: nicht blockieren


def pruefe_voraussetzungen(talent_data: dict, daten: dict, setting_talente: dict) -> list[str]:
    """Gibt die Liste der NICHT erfüllten Voraussetzungen zurück."""
    return [
        v
        for v in talent_data.get("voraussetzungen", [])
        if not _einzelne_erfuellt(v, daten, setting_talente)
    ]
