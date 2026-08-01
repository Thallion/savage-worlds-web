"""Automatische Effekte von Talenten (Original: talent_funktionen.py).

Talente können beim Wählen weitere Elemente mitbringen (auto_handicaps /
auto_talente / auto_maechte aus dem Setting-JSON, z. B. AH (Verdorbener) →
Handicap "Verderbnis") oder Eigenschaften verändern (effekt.attribut_bonus in
Deadlands, Rohling → Athletik an Stärke gekoppelt). Auto-Elemente kosten keine
Handicap-Punkte/Slots.

Nur dauerhafte Effekte gehören hierher: Berserker etwa gibt +1 Würfeltyp Stärke
ausschließlich während des Berserkerrauschs, die Basiswerte bleiben unverändert.

Wie bei den Volk-Effekten wird ein Snapshot pro gewählter Kopie in
daten["talent_effekte"][talent_name] abgelegt (Liste, bei Mehrfachauswahl
ein Eintrag je Kopie; Altbestand: einzelnes dict), damit das Abwählen einer
Kopie genau deren Effekte zurücknimmt.
"""

MAX_WUERFEL = 12
MIN_WUERFEL = 4

# Statische Spezialfälle aus dem Original (stehen nicht im Setting-JSON)
TALENT_FERTIGKEITS_LINKS = {
    "Rohling": [("Athletik", "Stärke")],
    "Naturgespür": [("Überleben", "Willenskraft")],
}

# Talente, deren Attribut-Erhöhung früher dauerhaft gebucht wurde, inzwischen
# aber als temporär erkannt ist — bei Bestandscharakteren nimmt
# migriere_temporaere_attribut_effekte() sie beim Laden zurück
TEMPORAERE_ATTRIBUT_EFFEKTE = ("Berserker",)


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


def _nimm_attribut_stufen_zurueck(daten: dict, stufen: list) -> None:
    """Macht gebuchte Würfeltyp-Erhöhungen rückgängig (letzte zuerst)."""
    for attr_name, feld in reversed(stufen):
        attr = daten.get("attribute", {}).get(attr_name)
        if not attr:
            continue
        if feld == "modifier":
            attr["modifier"] = attr.get("modifier", 0) - 1
        else:
            attr["wert"] = max(MIN_WUERFEL, attr.get("wert", MIN_WUERFEL) - 2)


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

    # Attribut-Würfeltyp-Effekte aus effekt.attribut_bonus des Setting-JSONs
    stufen: list[tuple[str, str]] = []  # (attribut, verändertes Feld)
    boni: list[tuple[str, int]] = []
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

    _nimm_attribut_stufen_zurueck(daten, angewendet.get("attribut_stufen", []))

    for fert_name, altes_attr in angewendet.get("fertigkeit_links", {}).items():
        fert = daten.get("fertigkeiten", {}).get(fert_name)
        if fert:
            fert["attribut"] = altes_attr

    if not daten.get("talent_effekte"):
        daten.pop("talent_effekte", None)


def migriere_temporaere_attribut_effekte(daten: dict) -> bool:
    """Nimmt bei Bestandscharakteren dauerhaft gebuchte Attribut-Erhöhungen
    zurück, die nach heutiger Auslegung nur temporär gelten (Berserker: +1
    Würfeltyp Stärke nur im Berserkerrausch). Gibt zurück, ob etwas geändert
    wurde; das Talent selbst bleibt gewählt."""
    effekte = daten.get("talent_effekte") or {}
    geaendert = False

    for talent_name in TEMPORAERE_ATTRIBUT_EFFEKTE:
        if talent_name not in effekte:
            continue
        rest = []
        for snapshot in _snapshots(effekte[talent_name]):
            stufen = snapshot.get("attribut_stufen")
            if stufen:
                _nimm_attribut_stufen_zurueck(daten, stufen)
                snapshot = {k: v for k, v in snapshot.items() if k != "attribut_stufen"}
                geaendert = True
            rest.append(snapshot)
        # nur leere Snapshots übrig: Eintrag entfernen, wie bei einem heute
        # frisch gewählten Talent ohne dauerhafte Effekte
        if any(rest):
            effekte[talent_name] = rest
        else:
            effekte.pop(talent_name)
            geaendert = True

    if geaendert and not effekte:
        daten.pop("talent_effekte", None)
    return geaendert


def ist_auto_element(daten: dict, art: str, name: str) -> bool:
    """True, wenn name als Auto-Element (art: "handicaps"/"talente"/"maechte")
    von einem gewählten Talent stammt und nicht manuell entfernbar ist."""
    return any(
        name in snapshot.get(art, [])
        for eintrag in daten.get("talent_effekte", {}).values()
        for snapshot in _snapshots(eintrag)
    )
