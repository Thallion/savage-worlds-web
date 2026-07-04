"""Automatische Effekte von Talenten (Original: talent_funktionen.py).

Talente können beim Wählen weitere Elemente mitbringen (auto_handicaps /
auto_talente / auto_maechte aus dem Setting-JSON, z. B. AH (Verdorbener) →
Handicap "Verderbnis") oder Eigenschaften verändern (Berserker → Stärke
+1 Würfeltyp, effekt.attribut_bonus in Deadlands, Rohling → Athletik an
Stärke gekoppelt). Auto-Elemente kosten keine Handicap-Punkte/Slots.

Wie bei den Volk-Effekten wird ein Snapshot pro gewählter Kopie in
daten["talent_effekte"][talent_name] abgelegt (Liste, bei Mehrfachauswahl
ein Eintrag je Kopie; Altbestand: einzelnes dict), damit das Abwählen einer
Kopie genau deren Effekte zurücknimmt.
"""

MAX_WUERFEL = 12
MIN_WUERFEL = 4

# Statische Spezialfälle aus dem Original (stehen nicht im Setting-JSON)
TALENT_ATTRIBUT_WUERFEL_EFFEKTE = {"Berserker": "Stärke"}
TALENT_FERTIGKEITS_LINKS = {
    "Rohling": [("Athletik", "Stärke")],
    "Naturgespür": [("Überleben", "Willenskraft")],
}


def _snapshots(eintrag) -> list[dict]:
    """Gespeicherte Effekt-Snapshots eines Talents (Altbestand: einzelnes dict)."""
    if isinstance(eintrag, list):
        return eintrag
    return [eintrag] if eintrag else []


def _attribut_stufe_erhoehen(attr: dict) -> str:
    """Erhöht um einen Würfeltyp; gibt das veränderte Feld zurück."""
    if attr.get("wert", MIN_WUERFEL) < MAX_WUERFEL:
        attr["wert"] = attr.get("wert", MIN_WUERFEL) + 2
        return "wert"
    attr["modifier"] = attr.get("modifier", 0) + 1
    return "modifier"


def wende_talent_effekte_an(daten: dict, talent_name: str, talent_data: dict) -> None:
    angewendet: dict = {}

    handicaps = [
        h for h in talent_data.get("auto_handicaps") or []
        if h not in daten.setdefault("selected_handicaps", [])
    ]
    if handicaps:
        daten["selected_handicaps"].extend(handicaps)
        angewendet["handicaps"] = handicaps

    talente = [
        t for t in talent_data.get("auto_talente") or []
        if t not in daten.setdefault("selected_talente", [])
    ]
    if talente:
        daten["selected_talente"].extend(talente)
        angewendet["talente"] = talente

    maechte = [
        m for m in talent_data.get("auto_maechte") or []
        if m not in daten.setdefault("selected_maechte", [])
    ]
    if maechte:
        daten["selected_maechte"].extend(maechte)
        angewendet["maechte"] = maechte

    # Attribut-Würfeltyp-Effekte: statisch (Berserker) + effekt.attribut_bonus
    stufen: list[tuple[str, str]] = []  # (attribut, verändertes Feld)
    statisch = TALENT_ATTRIBUT_WUERFEL_EFFEKTE.get(talent_name)
    boni: list[tuple[str, int]] = [(statisch, 1)] if statisch else []
    effekt = talent_data.get("effekt")
    if isinstance(effekt, dict):
        boni.extend((name, anzahl) for name, anzahl in (effekt.get("attribut_bonus") or {}).items())
    for attr_name, anzahl in boni:
        attr = daten.get("attribute", {}).get(attr_name)
        if not attr:
            continue
        for _ in range(anzahl):
            stufen.append((attr_name, _attribut_stufe_erhoehen(attr)))
    if stufen:
        angewendet["attribut_stufen"] = stufen

    links: dict[str, str] = {}
    for fert_name, neues_attr in TALENT_FERTIGKEITS_LINKS.get(talent_name, []):
        fert = daten.get("fertigkeiten", {}).get(fert_name)
        if fert and neues_attr in daten.get("attribute", {}):
            links[fert_name] = fert.get("attribut")
            fert["attribut"] = neues_attr
    if links:
        angewendet["fertigkeit_links"] = links

    # Leere Snapshots nur ablegen, wenn eine frühere Kopie Effekte hinterlegt
    # hat — dann nimmt das Entfernen der letzten Kopie genau diese zurück
    vorhanden = _snapshots(daten.get("talent_effekte", {}).get(talent_name))
    if angewendet or vorhanden:
        daten.setdefault("talent_effekte", {})[talent_name] = vorhanden + [angewendet]


def entferne_talent_effekte(daten: dict, talent_name: str) -> None:
    effekte = daten.get("talent_effekte", {})
    snapshots = _snapshots(effekte.get(talent_name))
    if not snapshots:
        return
    angewendet = snapshots.pop()
    if snapshots:
        effekte[talent_name] = snapshots
    else:
        effekte.pop(talent_name, None)

    for h in angewendet.get("handicaps", []):
        if h in daten.get("selected_handicaps", []):
            daten["selected_handicaps"].remove(h)
    for t in angewendet.get("talente", []):
        if t in daten.get("selected_talente", []):
            daten["selected_talente"].remove(t)
    for m in angewendet.get("maechte", []):
        if m in daten.get("selected_maechte", []):
            daten["selected_maechte"].remove(m)

    for attr_name, feld in reversed(angewendet.get("attribut_stufen", [])):
        attr = daten.get("attribute", {}).get(attr_name)
        if not attr:
            continue
        if feld == "modifier":
            attr["modifier"] = attr.get("modifier", 0) - 1
        else:
            attr["wert"] = max(MIN_WUERFEL, attr.get("wert", MIN_WUERFEL) - 2)

    for fert_name, altes_attr in angewendet.get("fertigkeit_links", {}).items():
        fert = daten.get("fertigkeiten", {}).get(fert_name)
        if fert:
            fert["attribut"] = altes_attr

    if not daten.get("talent_effekte"):
        daten.pop("talent_effekte", None)


def ist_auto_element(daten: dict, art: str, name: str) -> bool:
    """True, wenn name als Auto-Element (art: "handicaps"/"talente"/"maechte")
    von einem gewählten Talent stammt und nicht manuell entfernbar ist."""
    return any(
        name in snapshot.get(art, [])
        for eintrag in daten.get("talent_effekte", {}).values()
        for snapshot in _snapshots(eintrag)
    )
