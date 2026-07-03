"""Anwenden und Zurücknehmen von Volk-Effekten auf charakter_daten.

Die Setting-JSONs liefern pro Volk ein strukturiertes "effects"-Objekt
(attribute_bonuses, fertigkeits_startboni, auto_talente, auto_handicaps, ...).
Angewendete Effekte werden als Snapshot in daten["volk_effekte"] festgehalten,
damit ein Volk-Wechsel sie exakt zurücknehmen kann, ohne manuelle Steigerungen
des Spielers zu verlieren. Bewegungsweite-/Robustheit-/Größen-Boni werden nicht
in die Attribute geschrieben, sondern zur Laufzeit in /spiellogik/berechne aus
voelker_selected gelesen.
"""

from app.services.volk_wahlen import entferne_alle_spezialwahlen

MAX_WUERFEL = 12
MIN_WUERFEL = 4


def verfuegbare_volk_wahl(volk_data: dict) -> dict | None:
    """Offene Wahlmöglichkeit eines Volkes: {"optionen": [...], "attribute": [...]|None}.

    "talent" = +1 Talent-Slot, "fertigkeitspunkte" = +2 Fertigkeitssteigerungen,
    "attribut" = ein Attribut um einen Würfeltyp erhöhen ("attribute" schränkt
    die wählbaren Attribute ein, None = alle). freies_talent wird weiterhin
    automatisch beim Volk-Anwenden vergeben, nicht hier.
    """
    wm = (volk_data.get("effects") or {}).get("wahlmoeglichkeiten") or {}
    if wm.get("freies_talent_oder_attribut"):
        return {"optionen": ["talent", "attribut"], "attribute": None}
    if wm.get("freies_talent_oder_fertigkeitspunkte"):
        return {"optionen": ["talent", "fertigkeitspunkte"], "attribute": None}
    if wm.get("freies_attribut"):
        return {"optionen": ["attribut"], "attribute": None}
    if wm.get("attribut_staerke_oder_konstitution"):
        return {"optionen": ["attribut"], "attribute": ["Stärke", "Konstitution"]}
    return None


def _entferne_volk_wahl(daten: dict) -> None:
    wahl = daten.get("volk_effekte", {}).pop("wahl", None)
    if not wahl:
        return
    typ = wahl.get("typ")
    if typ == "talent":
        daten["verbleibende_talente"] = max(0, daten.get("verbleibende_talente", 0) - 1)
    elif typ == "fertigkeitspunkte":
        daten["verbleibende_fertigkeitssteigerungen"] = max(
            0, daten.get("verbleibende_fertigkeitssteigerungen", 0) - 2
        )
        daten["maximale_fertigkeitssteigerungen"] = max(
            0, daten.get("maximale_fertigkeitssteigerungen", 0) - 2
        )
    elif typ == "attribut":
        attr = daten.get("attribute", {}).get(wahl.get("ziel", ""))
        if attr:
            if wahl.get("feld") == "modifier":
                attr["modifier"] = attr.get("modifier", 0) - 1
            else:
                attr["wert"] = max(MIN_WUERFEL, attr.get("wert", MIN_WUERFEL) - 2)


def wende_volk_wahl_an(daten: dict, element: str) -> tuple[bool, str]:
    """Löst die Wahlmöglichkeit des gewählten Volkes ein.

    element ist "talent", "fertigkeitspunkte" oder ein Attributname.
    Eine bestehende Wahl wird ersetzt (Wechsel ist erlaubt).
    """
    voelker = daten.get("voelker_selected") or {}
    if not voelker:
        return False, "Kein Volk gewählt"
    volk_name, volk_data = next(iter(voelker.items()))

    wahl_def = verfuegbare_volk_wahl(volk_data)
    if not wahl_def:
        return False, f"'{volk_name}' bietet keine Wahlmöglichkeit"

    typ = element if element in ("talent", "fertigkeitspunkte") else "attribut"
    if typ not in wahl_def["optionen"]:
        gueltig = ", ".join(wahl_def["optionen"])
        return False, f"'{element}' ist keine gültige Wahl für '{volk_name}' (möglich: {gueltig})"

    if typ == "attribut":
        if element not in daten.get("attribute", {}):
            return False, f"Attribut '{element}' nicht gefunden"
        erlaubt = wahl_def["attribute"]
        if erlaubt and element not in erlaubt:
            return False, f"'{volk_name}' erlaubt nur: {', '.join(erlaubt)}"

    _entferne_volk_wahl(daten)

    if typ == "talent":
        daten["verbleibende_talente"] = daten.get("verbleibende_talente", 0) + 1
        wahl = {"typ": "talent"}
    elif typ == "fertigkeitspunkte":
        daten["verbleibende_fertigkeitssteigerungen"] = (
            daten.get("verbleibende_fertigkeitssteigerungen", 0) + 2
        )
        daten["maximale_fertigkeitssteigerungen"] = daten.get("maximale_fertigkeitssteigerungen", 0) + 2
        wahl = {"typ": "fertigkeitspunkte"}
    else:
        attr = daten["attribute"][element]
        if attr.get("wert", MIN_WUERFEL) < MAX_WUERFEL:
            attr["wert"] = attr.get("wert", MIN_WUERFEL) + 2
            wahl = {"typ": "attribut", "ziel": element, "feld": "wert"}
        else:
            attr["modifier"] = attr.get("modifier", 0) + 1
            wahl = {"typ": "attribut", "ziel": element, "feld": "modifier"}

    daten.setdefault("volk_effekte", {})["wahl"] = wahl
    return True, ""


def entferne_volk_effekte(daten: dict) -> dict:
    angewendet = daten.get("volk_effekte")
    if not angewendet:
        daten["voelker_selected"] = {}
        return daten

    entferne_alle_spezialwahlen(daten)
    _entferne_volk_wahl(daten)

    for attr_name, delta in angewendet.get("attribute", {}).items():
        attr = daten.get("attribute", {}).get(attr_name)
        if attr:
            attr["wert"] = max(MIN_WUERFEL, attr.get("wert", MIN_WUERFEL) - delta)

    for fert_name, info in angewendet.get("fertigkeiten", {}).items():
        fert = daten.get("fertigkeiten", {}).get(fert_name)
        if not fert:
            continue
        wuerfel = fert.get("wuerfel", {})
        if info.get("war_untrainiert"):
            wuerfel["value"] = MIN_WUERFEL
            wuerfel["modifier"] = -2
            fert["ausgewaehlt"] = False
        else:
            wuerfel["value"] = max(MIN_WUERFEL, wuerfel.get("value", MIN_WUERFEL) - info.get("delta", 0))
        fert["wuerfel"] = wuerfel

    for talent in angewendet.get("talente", []):
        if talent in daten.get("selected_talente", []):
            daten["selected_talente"].remove(talent)

    for handicap in angewendet.get("handicaps", []):
        if handicap in daten.get("selected_handicaps", []):
            daten["selected_handicaps"].remove(handicap)

    talent_slots = angewendet.get("talent_slots", 0)
    if talent_slots:
        daten["verbleibende_talente"] = max(0, daten.get("verbleibende_talente", 0) - talent_slots)

    daten.pop("volk_effekte", None)
    daten["voelker_selected"] = {}
    return daten


def wende_volk_an(daten: dict, volk_name: str, volk_data: dict) -> dict:
    entferne_volk_effekte(daten)

    effekte = volk_data.get("effects") or {}
    angewendet: dict = {"attribute": {}, "fertigkeiten": {}, "talente": [], "handicaps": []}

    for attr_name, bonus in (effekte.get("attribute_bonuses") or {}).items():
        attr = daten.get("attribute", {}).get(attr_name)
        if not attr:
            continue
        alt = attr.get("wert", MIN_WUERFEL)
        neu = min(MAX_WUERFEL, max(MIN_WUERFEL, alt + bonus))
        attr["wert"] = neu
        angewendet["attribute"][attr_name] = neu - alt

    for fert_name, bonus in (effekte.get("fertigkeits_startboni") or {}).items():
        fert = daten.get("fertigkeiten", {}).get(fert_name)
        if not fert:
            continue
        wuerfel = fert.get("wuerfel", {"value": MIN_WUERFEL, "modifier": -2, "typ": "fertigkeit"})
        war_untrainiert = wuerfel.get("modifier", 0) == -2
        if war_untrainiert:
            # Volk startet die Fertigkeit bei W(4+bonus), z. B. Bonus 2 -> W6
            wuerfel["modifier"] = 0
            wuerfel["value"] = min(MAX_WUERFEL, MIN_WUERFEL + bonus)
            fert["ausgewaehlt"] = True
            angewendet["fertigkeiten"][fert_name] = {"war_untrainiert": True, "delta": bonus}
        else:
            alt = wuerfel.get("value", MIN_WUERFEL)
            neu = min(MAX_WUERFEL, alt + bonus)
            wuerfel["value"] = neu
            angewendet["fertigkeiten"][fert_name] = {"war_untrainiert": False, "delta": neu - alt}
        fert["wuerfel"] = wuerfel

    for talent in effekte.get("auto_talente") or []:
        if talent not in daten.setdefault("selected_talente", []):
            daten["selected_talente"].append(talent)
            angewendet["talente"].append(talent)

    # Volks-Handicaps zählen nicht zur 4-Punkte-Ökonomie und geben keine Punkte
    for handicap in effekte.get("auto_handicaps") or []:
        if handicap not in daten.setdefault("selected_handicaps", []):
            daten["selected_handicaps"].append(handicap)
            angewendet["handicaps"].append(handicap)

    # Freies Anfängertalent (z. B. Mensch "Anpassungsfähig") als Talent-Slot
    wm = effekte.get("wahlmoeglichkeiten") or {}
    if wm.get("freies_talent") or wm.get("freies_anfaenger_talent"):
        daten["verbleibende_talente"] = daten.get("verbleibende_talente", 0) + 1
        angewendet["talent_slots"] = 1

    daten["volk_effekte"] = angewendet
    daten["voelker_selected"] = {volk_name: volk_data}
    return daten
