"""Spezial-Wahlmöglichkeiten von Völkern (über die Kern-Wahl hinaus).

Die Kern-Wahl (freies Talent / Fertigkeitspunkte / Attribut) lebt in
volk_effekte.py. Hier stehen die im Original (volk_wahlmoeglichkeiten.py)
verbliebenen Spezialfälle, alle datengetrieben aus dem effects-Objekt des
gewählten Volkes:

- Fertigkeits-Wahlen: "heimlich" (Engro: Heimlichkeit ODER Diebeskunst W6),
  "freie_verstandsfertigkeit" (Gnom), "handwerks_wissen" (Zwerg, Sundered
  Skies), "spezialisierung" (Androiden) — eine Fertigkeit startet auf W6.
- "magieaffin": Wahl eines AH-Talents; das Talent wird als Volks-Talent
  gesetzt (kein Slot, nicht manuell entfernbar) und seine Arkane Fertigkeit
  von ungelernt (W4-2) auf W4 gehoben — wie im Original.
- "attribut_schwaeche": Wahl eines Attributs, das den Malus aus
  effects["attribut_malus_wert"] (Standard -2) als Modifier erhält.
- "outsider_statt_trennungsangst" (Insektoide): Verzicht auf das
  Auto-Handicap "Trennungsangst" zugunsten des reinen Außenseiter-Daseins.
- "pflanzenerbe_auswahl"/"tierart_auswahl" (Sundered Skies): beschreibende
  Wahl ohne Regel-Effekt; Optionen aus config/volk_wahl_config.json,
  Tierart als Freitext.

Jede angewendete Wahl wird als Snapshot in
daten["volk_effekte"]["wahlen"][wahl_id] festgehalten, damit erneutes Wählen
und Volk-Wechsel sie exakt zurücknehmen können.
"""

import re

from app.services.charakter_init import load_config

MAX_WUERFEL = 12
MIN_WUERFEL = 4

# "Arkaner Hintergrund, Arkane Fertigkeit: Zaubern (Verstand)" -> "Zaubern"
_ARKANE_FERTIGKEIT_RE = re.compile(r"Arkane Fertigkeit:\s*([^(,]+?)\s*(?:\(|,|$)")

_FERTIGKEIT_WAHLEN = {
    # wahl_id -> (filter, Beschreibung); Optionen kommen ggf. aus der Wahl-Definition
    "freie_verstandsfertigkeit": ("verstand", "Eine Verstand-Fertigkeit beginnt auf W6"),
    "handwerks_wissen": ("wissen", "Ein Wissen nach Wahl beginnt auf W6"),
    "spezialisierung": (None, "Eine Fertigkeit als Spezialisierung beginnt auf W6"),
}

_BESCHREIBENDE_WAHLEN = ("pflanzenerbe_auswahl", "tierart_auswahl")


def verfuegbare_spezialwahlen(volk_data: dict) -> list[dict]:
    """Liste der Spezial-Wahlmöglichkeiten eines Volkes (ohne Kern-Wahl).

    Jeder Eintrag: {"id", "typ", ...typspezifische Felder}. Die Fertigkeits-
    Optionen mit "filter" werden erst gegen daten["fertigkeiten"] aufgelöst.
    """
    effekte = volk_data.get("effects") or {}
    wm = effekte.get("wahlmoeglichkeiten") or {}
    se = effekte.get("spezielle_effekte") or {}
    wahlen: list[dict] = []

    heimlich = wm.get("heimlich")
    if isinstance(heimlich, dict) and heimlich.get("optionen"):
        wahlen.append(
            {
                "id": "heimlich",
                "typ": "fertigkeit",
                "optionen": list(heimlich["optionen"]),
                "bonus": int(heimlich.get("bonus", 2)),
                "beschreibung": heimlich.get("beschreibung", ""),
            }
        )

    for wahl_id, (filter_name, beschreibung) in _FERTIGKEIT_WAHLEN.items():
        if wm.get(wahl_id):
            wahlen.append(
                {
                    "id": wahl_id,
                    "typ": "fertigkeit",
                    "filter": filter_name,
                    "bonus": 2,
                    "beschreibung": beschreibung,
                }
            )

    if wm.get("magieaffin") or se.get("magieaffin"):
        wahlen.append(
            {
                "id": "magieaffin",
                "typ": "magieaffin",
                "beschreibung": "Arkaner Hintergrund nach Wahl; die Arkane Fertigkeit beginnt auf W4",
            }
        )

    if wm.get("attribut_schwaeche") or effekte.get("attribut_malus"):
        wahlen.append(
            {
                "id": "attribut_schwaeche",
                "typ": "attribut_malus",
                "malus": int(effekte.get("attribut_malus_wert", -2)),
                "beschreibung": "Ein Attribut nach Wahl erhält den Volks-Malus",
            }
        )

    if wm.get("outsider_statt_trennungsangst"):
        wahlen.append(
            {
                "id": "outsider_statt_trennungsangst",
                "typ": "handicap_verzicht",
                "handicap": "Trennungsangst",
                "beschreibung": "Außenseiter statt Trennungsangst",
            }
        )

    cfg = load_config("volk_wahl_config.json")
    for wahl_id in _BESCHREIBENDE_WAHLEN:
        if wm.get(wahl_id):
            eintrag = cfg.get(wahl_id) or {}
            wahlen.append(
                {
                    "id": wahl_id,
                    "typ": "beschreibung",
                    "label": eintrag.get("label", wahl_id),
                    # leere Optionsliste = Freitext (z. B. Tierart)
                    "optionen": eintrag.get("optionen") or [],
                    "beschreibung": eintrag.get("beschreibung", ""),
                }
            )

    return wahlen


def _fertigkeit_optionen(wahl: dict, daten: dict) -> list[str]:
    ferts = daten.get("fertigkeiten", {})
    if wahl.get("optionen"):
        return [n for n in wahl["optionen"] if n in ferts]
    filter_name = wahl.get("filter")
    if filter_name == "verstand":
        return sorted(n for n, f in ferts.items() if f.get("attribut") == "Verstand")
    if filter_name == "wissen":
        return sorted(n for n in ferts if n.startswith("Wissen"))
    return sorted(ferts)


def _wende_fertigkeit_bonus_an(daten: dict, fert_name: str, bonus: int) -> dict:
    """Startbonus wie bei fertigkeits_startboni; gibt den Rücknahme-Snapshot zurück."""
    fert = daten["fertigkeiten"][fert_name]
    wuerfel = fert.get("wuerfel", {"value": MIN_WUERFEL, "modifier": -2, "typ": "fertigkeit"})
    war_untrainiert = wuerfel.get("modifier", 0) == -2
    if war_untrainiert:
        wuerfel["modifier"] = 0
        wuerfel["value"] = min(MAX_WUERFEL, MIN_WUERFEL + bonus)
        fert["ausgewaehlt"] = True
        delta = bonus
    else:
        alt = wuerfel.get("value", MIN_WUERFEL)
        wuerfel["value"] = min(MAX_WUERFEL, alt + bonus)
        delta = wuerfel["value"] - alt
    fert["wuerfel"] = wuerfel
    return {"typ": "fertigkeit", "ziel": fert_name, "war_untrainiert": war_untrainiert, "delta": delta}


def _entferne_fertigkeit_bonus(daten: dict, snapshot: dict) -> None:
    fert = daten.get("fertigkeiten", {}).get(snapshot.get("ziel", ""))
    if not fert:
        return
    wuerfel = fert.get("wuerfel", {})
    if snapshot.get("war_untrainiert"):
        wuerfel["value"] = MIN_WUERFEL
        wuerfel["modifier"] = -2
        fert["ausgewaehlt"] = False
    else:
        wuerfel["value"] = max(MIN_WUERFEL, wuerfel.get("value", MIN_WUERFEL) - snapshot.get("delta", 0))
    fert["wuerfel"] = wuerfel


def arkane_fertigkeit_aus_ah(talent_data: dict) -> str | None:
    m = _ARKANE_FERTIGKEIT_RE.search(talent_data.get("beschreibung", "") or "")
    return m.group(1).strip() if m else None


def magieaffin_optionen(setting_talente: dict) -> list[str]:
    """AH-Talente des Settings, deren Arkane Fertigkeit erkennbar ist."""
    return sorted(
        name
        for name, talent in setting_talente.items()
        if name.startswith("AH") and arkane_fertigkeit_aus_ah(talent)
    )


def _wende_magieaffin_an(daten: dict, setting_talente: dict, ah_name: str) -> tuple[dict | None, str]:
    talent_data = setting_talente.get(ah_name)
    if not talent_data or not ah_name.startswith("AH"):
        return None, f"'{ah_name}' ist kein AH-Talent dieses Settings"
    fert_name = arkane_fertigkeit_aus_ah(talent_data)

    snapshot: dict = {"typ": "magieaffin", "ah_talent": ah_name}
    if ah_name not in daten.setdefault("selected_talente", []):
        daten["selected_talente"].append(ah_name)
        # Als Volks-Talent registrieren: kein Slot, nicht manuell entfernbar,
        # Volk-Wechsel räumt es über den volk_effekte-Snapshot ab
        daten.setdefault("volk_effekte", {}).setdefault("talente", []).append(ah_name)
        snapshot["talent_hinzugefuegt"] = True

    fert = daten.get("fertigkeiten", {}).get(fert_name or "")
    if fert is not None:
        wuerfel = fert.get("wuerfel", {})
        if wuerfel.get("modifier", 0) == -2:
            # wie im Original: W4-2 -> W4+0
            wuerfel["modifier"] = 0
            fert["ausgewaehlt"] = True
            fert["wuerfel"] = wuerfel
            snapshot["fertigkeit"] = fert_name
    return snapshot, ""


def _entferne_magieaffin(daten: dict, snapshot: dict) -> None:
    ah_name = snapshot.get("ah_talent", "")
    if snapshot.get("talent_hinzugefuegt"):
        if ah_name in daten.get("selected_talente", []):
            daten["selected_talente"].remove(ah_name)
        volk_talente = daten.get("volk_effekte", {}).get("talente", [])
        if ah_name in volk_talente:
            volk_talente.remove(ah_name)
    fert_name = snapshot.get("fertigkeit")
    fert = daten.get("fertigkeiten", {}).get(fert_name or "")
    if fert:
        wuerfel = fert.get("wuerfel", {})
        # Nur zurücksetzen, wenn der Spieler nicht weiter investiert hat
        if wuerfel.get("value", MIN_WUERFEL) == MIN_WUERFEL and wuerfel.get("modifier", 0) == 0:
            wuerfel["modifier"] = -2
            fert["ausgewaehlt"] = False
            fert["wuerfel"] = wuerfel


def _wende_spezialwahl_an(
    daten: dict, setting: dict, wahl: dict, auswahl: str
) -> tuple[dict | None, str]:
    """Wendet eine Wahl an und liefert (Snapshot, Fehlermeldung)."""
    typ = wahl["typ"]

    if typ == "fertigkeit":
        optionen = _fertigkeit_optionen(wahl, daten)
        if auswahl not in optionen:
            return None, f"'{auswahl}' ist keine gültige Fertigkeit für diese Wahl"
        return _wende_fertigkeit_bonus_an(daten, auswahl, wahl.get("bonus", 2)), ""

    if typ == "magieaffin":
        return _wende_magieaffin_an(daten, setting.get("talente", {}), auswahl)

    if typ == "attribut_malus":
        attr = daten.get("attribute", {}).get(auswahl)
        if not attr:
            return None, f"Attribut '{auswahl}' nicht gefunden"
        malus = wahl.get("malus", -2)
        attr["modifier"] = attr.get("modifier", 0) + malus
        return {"typ": "attribut_malus", "ziel": auswahl, "malus": malus}, ""

    if typ == "handicap_verzicht":
        handicap = wahl["handicap"]
        if auswahl not in (handicap, "Außenseiter"):
            return None, f"Gültige Wahl: '{handicap}' behalten oder 'Außenseiter'"
        if auswahl == handicap:
            # explizit "behalten" gewählt: nichts zu tun, keine Wahl gespeichert
            return {}, ""
        entfernt = False
        if handicap in daten.get("selected_handicaps", []):
            daten["selected_handicaps"].remove(handicap)
            entfernt = True
        volk_handicaps = daten.get("volk_effekte", {}).get("handicaps", [])
        if handicap in volk_handicaps:
            volk_handicaps.remove(handicap)
        return {"typ": "handicap_verzicht", "handicap": handicap, "entfernt": entfernt}, ""

    if typ == "beschreibung":
        optionen = wahl.get("optionen") or []
        if optionen and auswahl not in optionen:
            return None, f"Gültige Optionen: {', '.join(optionen)}"
        if not auswahl.strip():
            return None, "Keine Auswahl angegeben"
        return {"typ": "beschreibung", "ziel": auswahl.strip(), "label": wahl.get("label", wahl["id"])}, ""

    return None, f"Unbekannter Wahl-Typ '{typ}'"


def _entferne_spezialwahl(daten: dict, snapshot: dict) -> None:
    typ = snapshot.get("typ")
    if typ == "fertigkeit":
        _entferne_fertigkeit_bonus(daten, snapshot)
    elif typ == "magieaffin":
        _entferne_magieaffin(daten, snapshot)
    elif typ == "attribut_malus":
        attr = daten.get("attribute", {}).get(snapshot.get("ziel", ""))
        if attr:
            attr["modifier"] = attr.get("modifier", 0) - snapshot.get("malus", -2)
    elif typ == "handicap_verzicht":
        handicap = snapshot.get("handicap", "")
        if snapshot.get("entfernt") and handicap:
            if handicap not in daten.setdefault("selected_handicaps", []):
                daten["selected_handicaps"].append(handicap)
            volk_handicaps = daten.setdefault("volk_effekte", {}).setdefault("handicaps", [])
            if handicap not in volk_handicaps:
                volk_handicaps.append(handicap)
    # typ "beschreibung": nichts zurückzunehmen


def entferne_alle_spezialwahlen(daten: dict) -> None:
    """Nimmt alle Spezial-Wahlen zurück (vor dem Volk-Wechsel-Teardown)."""
    wahlen = daten.get("volk_effekte", {}).pop("wahlen", None) or {}
    for snapshot in wahlen.values():
        _entferne_spezialwahl(daten, snapshot)


def wende_volk_spezialwahl_an(daten: dict, setting: dict, wahl_id: str, auswahl: str) -> tuple[bool, str]:
    """Löst eine Spezial-Wahl des gewählten Volkes ein (ersetzt eine bestehende)."""
    voelker = daten.get("voelker_selected") or {}
    if not voelker:
        return False, "Kein Volk gewählt"
    volk_name, volk_data = next(iter(voelker.items()))

    wahl = next((w for w in verfuegbare_spezialwahlen(volk_data) if w["id"] == wahl_id), None)
    if not wahl:
        return False, f"'{volk_name}' bietet keine Wahl '{wahl_id}'"

    # bestehende Wahl derselben Art zurücknehmen (Wechsel ist erlaubt)
    wahlen = daten.setdefault("volk_effekte", {}).setdefault("wahlen", {})
    vorherige = wahlen.pop(wahl_id, None)
    if vorherige:
        _entferne_spezialwahl(daten, vorherige)

    snapshot, fehler = _wende_spezialwahl_an(daten, setting, wahl, auswahl)
    if snapshot is None:
        return False, fehler
    if snapshot:  # leerer Snapshot = "behalten"-Wahl ohne Effekt
        wahlen[wahl_id] = snapshot
    return True, ""
