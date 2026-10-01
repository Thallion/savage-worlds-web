"""Prüfung von Talent-Voraussetzungen und Mächte-Kapazität.

Voraussetzungs-Strings in den Setting-JSONs (Beispiele aus SWAE):
  "WIL W8"                     Attribut-Kürzel + Mindestwürfel
  "Kämpfen W6"                 Fertigkeit + Mindestwürfel (optional mit "+")
  "Athletik oder Schießen W8"  Oder-Alternativen
  "AH"                         beliebiger arkaner Hintergrund
  "Anführer"                   anderes Talent
  "Blutrünstig oder Fies"      Oder-Alternativen aus Talenten/Handicaps

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


def _handicap_basis(eintrag: str) -> str:
    """"Hässlich_schwer" / "Hässlich (schwer: ...)" → "Hässlich"."""
    if eintrag.endswith(("_leicht", "_schwer")):
        eintrag = eintrag[:-7]
    return eintrag.split(" (", 1)[0].strip()


def _alternative(teil: str, daten: dict, setting_talente: dict, handicap_namen: set[str]) -> bool | None:
    """Ein Teil einer Oder-Liste: True/False, wenn er als Talent oder Handicap
    bekannt ist, None bei unbekanntem Format."""
    if teil in setting_talente:
        return teil in daten.get("selected_talente", [])
    gewaehlt = {_handicap_basis(h) for h in daten.get("selected_handicaps", [])}
    # "Keine Rüstungsbeschränkung": erfüllt, solange das Handicap fehlt
    for praefix in ("Keine ", "Kein "):
        if teil.startswith(praefix):
            return teil[len(praefix):] not in gewaehlt
    if teil in gewaehlt:
        return True
    if teil in handicap_namen:
        return False
    return None


def _als_text(voraussetzung: str | dict) -> str:
    """Horror Kompendium speichert Alternativen als {"oder": [...]}."""
    if isinstance(voraussetzung, dict):
        return " oder ".join(str(a) for a in voraussetzung.get("oder", []))
    return str(voraussetzung)


def _einzelne_erfuellt(
    voraussetzung: str | dict, daten: dict, setting_talente: dict, handicap_namen: set[str] | None = None
) -> bool:
    v = _als_text(voraussetzung).strip()
    handicap_namen = handicap_namen or set()
    if v == "AH" or v.startswith(("AH ", "AH(", "AH:")):
        return hat_arkanen_hintergrund(daten, setting_talente)

    m = _EIGENSCHAFT_RE.match(v)
    if m:
        wert = int(m.group("wert"))
        namen = re.split(r"\s+oder\s+|,\s*", m.group("namen"))
        return any(_eigenschaft_erfuellt(n.strip(), wert, daten) for n in namen)

    if v in setting_talente:
        return v in daten.get("selected_talente", [])

    # "Blutrünstig oder Fies oder Skrupellos oder Hässlich" (Bedrohlich):
    # erfüllt, wenn eine bekannte Alternative gewählt ist. Ist keine
    # Alternative bekannt, wird nicht blockiert; existiert ein Handicap im
    # Setting nicht, kann der Charakter es auch nicht haben.
    if " oder " in v:
        ergebnisse = [
            _alternative(teil.strip(), daten, setting_talente, handicap_namen) for teil in v.split(" oder ")
        ]
        if any(ergebnisse):
            return True
        return all(e is None for e in ergebnisse)

    if v in handicap_namen:
        return v in {_handicap_basis(h) for h in daten.get("selected_handicaps", [])}

    return True  # unbekanntes Format: nicht blockieren


def pruefe_voraussetzungen(
    talent_data: dict, daten: dict, setting_talente: dict, setting_handicaps: dict | None = None
) -> list[str]:
    """Gibt die Liste der NICHT erfüllten Voraussetzungen zurück."""
    handicap_namen = {_handicap_basis(h) for h in (setting_handicaps or {})}
    return [
        _als_text(v)
        for v in talent_data.get("voraussetzungen", [])
        if not _einzelne_erfuellt(v, daten, setting_talente, handicap_namen)
    ]
