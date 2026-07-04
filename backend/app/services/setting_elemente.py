"""Bearbeitung von Setting-Elementen (Original: CustomElementManager +
talent_popup/handicap_popup/... in views/).

Die Kivy-App hält pro Charakter eine eigene Kopie aller Setting-Elemente und
schreibt Custom-Elemente in custom_*.json-Dateien. Die Web-App lädt Settings
stateless von der Platte — Änderungen des Nutzers (Hinzufügen, Bearbeiten,
Löschen) leben deshalb im Charakter selbst, in
charakter_daten["setting_overrides"]:

    {
        "talente": {name: element_daten, ...},      # neue + bearbeitete
        "handicaps": {...}, "maechte": {...}, "ausruestung": {...},
        "geloescht": {"talente": [name, ...], ...}  # entfernte native Elemente
    }

wende_setting_overrides_an() mischt die Overrides über das geladene Setting;
alle Spiellogik-Endpoints nutzen das, damit eigene Elemente wählbar sind und
gelöschte verschwinden. Die Overrides wandern mit Export/Import mit.
"""

ELEMENT_TYPEN = ("talente", "handicaps", "maechte", "ausruestung")

# Anzeige-Name pro Typ für Meldungen
_TYP_LABEL = {
    "talente": "Talent",
    "handicaps": "Handicap",
    "maechte": "Macht",
    "ausruestung": "Ausrüstung",
}

# Pflicht-Defaults je Typ (angelehnt an die Original-Modelle)
_DEFAULTS: dict[str, dict] = {
    "talente": {
        "kategorie": "",
        "rang": "A",
        "beschreibung": "",
        "voraussetzungen": [],
        "neue_maechte": 0,
        "machtpunkte": 0,
        "ausgewaehlt": False,
        "aktiv": True,
    },
    "handicaps": {
        "stufe": "leicht",
        "punkte": 1,
        "beschreibung": "",
        "ausgewaehlt": False,
        "aktiv": True,
    },
    "maechte": {
        "rang": "A",
        "machtpunkte": 1,
        "reichweite": "",
        "dauer": "",
        "effekt": "",
        "beschreibung": "",
        "voraussetzungen": [],
        "ausgewaehlt": False,
        "aktiv": True,
    },
    "ausruestung": {
        "kategorie": "Allgemein",
        "gewicht": 0,
        "kosten": 0,
        "setting": "",
        "beschreibung": "",
        "aktiv": True,
    },
}

_HANDICAP_STUFEN = ("leicht", "schwer")
_AUSRUESTUNG_KATEGORIEN = ("Allgemein", "Waffe", "Rüstung", "Schild")


def wende_setting_overrides_an(setting: dict, daten: dict) -> dict:
    """Mischt die Charakter-Overrides über das geladene Setting (ohne Mutation)."""
    overrides = daten.get("setting_overrides") or {}
    geloescht = overrides.get("geloescht") or {}
    if not any(overrides.get(t) for t in ELEMENT_TYPEN) and not any(
        geloescht.get(t) for t in ELEMENT_TYPEN
    ):
        return setting

    neu = dict(setting)
    for typ in ELEMENT_TYPEN:
        eintraege = overrides.get(typ) or {}
        entfernt = geloescht.get(typ) or []
        if not eintraege and not entfernt:
            continue
        tabelle = dict(neu.get(typ) or {})
        tabelle.update(eintraege)
        for name in entfernt:
            tabelle.pop(name, None)
        neu[typ] = tabelle
    return neu


def _ist_gewaehlt(daten: dict, typ: str, name: str) -> bool:
    if typ == "talente":
        return name in daten.get("selected_talente", [])
    if typ == "maechte":
        return name in daten.get("selected_maechte", [])
    if typ == "handicaps":
        gewaehlt = daten.get("selected_handicaps", [])
        return name in gewaehlt or f"{name}_leicht" in gewaehlt or f"{name}_schwer" in gewaehlt
    if typ == "ausruestung":
        eintrag = daten.get("ausruestung_selected", {}).get(name)
        return bool(eintrag and eintrag.get("anzahl", 0) > 0)
    return False


def _normalisiere(typ: str, name: str, element_daten: dict, custom: bool) -> tuple[dict | None, str]:
    """Defaults auffüllen und typspezifisch validieren."""
    element = {**_DEFAULTS[typ], **(element_daten or {}), "name": name, "custom": custom}

    if typ == "handicaps":
        stufe = str(element.get("stufe", "leicht")).lower()
        if stufe not in _HANDICAP_STUFEN:
            return None, f"Stufe muss {' oder '.join(_HANDICAP_STUFEN)} sein"
        element["stufe"] = stufe
        element["punkte"] = 2 if stufe == "schwer" else 1

    if typ == "ausruestung":
        kategorie = element.get("kategorie") or "Allgemein"
        if kategorie not in _AUSRUESTUNG_KATEGORIEN:
            return None, f"Kategorie muss eine von {', '.join(_AUSRUESTUNG_KATEGORIEN)} sein"
        element["kategorie"] = kategorie
        if kategorie == "Waffe":
            element.setdefault("typ", "Nahkampf")
            eigenschaften = element.get("eigenschaften") or {}
            element["eigenschaften"] = {
                "Schaden": eigenschaften.get("Schaden", "-"),
                "Reichweite": eigenschaften.get("Reichweite", "-"),
                "FR": eigenschaften.get("FR", "-"),
                "Schuss": eigenschaften.get("Schuss", "-"),
                "PB": eigenschaften.get("PB", "-"),
            }
        elif kategorie == "Rüstung":
            for teil in ("torso", "arme", "beine", "kopf"):
                element[teil] = int(element.get(teil) or 0)
        elif kategorie == "Schild":
            element["parade"] = int(element.get("parade") or 0)
            element["deckung"] = int(element.get("deckung") or 0)

    if typ in ("talente", "maechte") and isinstance(element.get("voraussetzungen"), str):
        element["voraussetzungen"] = [
            v.strip() for v in element["voraussetzungen"].split(",") if v.strip()
        ]

    return element, ""


def _entferne_aus_auswahl(daten: dict, typ: str, alter_name: str, neuer_name: str) -> None:
    """Bei Umbenennung: Auswahl-Schlüssel des Charakters mitziehen."""
    if typ == "talente":
        liste = daten.get("selected_talente", [])
        if alter_name in liste:
            liste[liste.index(alter_name)] = neuer_name
    elif typ == "maechte":
        liste = daten.get("selected_maechte", [])
        if alter_name in liste:
            liste[liste.index(alter_name)] = neuer_name
    elif typ == "handicaps":
        liste = daten.get("selected_handicaps", [])
        for i, eintrag in enumerate(liste):
            if eintrag == alter_name:
                liste[i] = neuer_name
            elif eintrag in (f"{alter_name}_leicht", f"{alter_name}_schwer"):
                liste[i] = f"{neuer_name}{eintrag[len(alter_name):]}"
    elif typ == "ausruestung":
        auswahl = daten.get("ausruestung_selected", {})
        if alter_name in auswahl:
            auswahl[neuer_name] = auswahl.pop(alter_name)


def speichere_element(
    daten: dict,
    setting: dict,
    typ: str,
    name: str,
    element_daten: dict,
    alter_name: str | None = None,
) -> tuple[bool, str]:
    """Legt ein Setting-Element an oder aktualisiert es (alter_name = Edit)."""
    if typ not in ELEMENT_TYPEN:
        return False, f"Unbekannter Element-Typ '{typ}'"
    name = (name or "").strip()
    if not name:
        return False, "Der Name darf nicht leer sein"

    label = _TYP_LABEL[typ]
    merged = wende_setting_overrides_an(setting, daten).get(typ, {})
    ist_neu = not alter_name

    if ist_neu and name in merged:
        return False, f"{label} '{name}' existiert bereits"
    if alter_name:
        if alter_name not in merged:
            return False, f"{label} '{alter_name}' nicht gefunden"
        if name != alter_name and name in merged:
            return False, f"{label} '{name}' existiert bereits"

    vorlage = merged.get(alter_name) if alter_name else None
    custom = True if ist_neu else bool((vorlage or {}).get("custom", False))
    element, fehler = _normalisiere(typ, name, {**(vorlage or {}), **(element_daten or {})}, custom)
    if element is None:
        return False, fehler

    overrides = daten.setdefault("setting_overrides", {})
    tabelle = overrides.setdefault(typ, {})

    if alter_name and alter_name != name:
        # Umbenennung: alten Eintrag entfernen bzw. natives Original ausblenden
        if alter_name in tabelle:
            del tabelle[alter_name]
        if alter_name in (setting.get(typ) or {}):
            geloescht = overrides.setdefault("geloescht", {}).setdefault(typ, [])
            if alter_name not in geloescht:
                geloescht.append(alter_name)
        _entferne_aus_auswahl(daten, typ, alter_name, name)

    tabelle[name] = element
    # Ein zuvor gelöschter Name wird durch Neuanlage wieder sichtbar
    geloescht = (overrides.get("geloescht") or {}).get(typ)
    if geloescht and name in geloescht:
        geloescht.remove(name)

    return True, ""


def loesche_element(daten: dict, setting: dict, typ: str, name: str) -> tuple[bool, str]:
    if typ not in ELEMENT_TYPEN:
        return False, f"Unbekannter Element-Typ '{typ}'"

    label = _TYP_LABEL[typ]
    merged = wende_setting_overrides_an(setting, daten).get(typ, {})
    if name not in merged:
        return False, f"{label} '{name}' nicht gefunden"
    if _ist_gewaehlt(daten, typ, name):
        return False, f"{label} '{name}' ist aktuell gewählt — bitte zuerst abwählen"

    overrides = daten.setdefault("setting_overrides", {})
    overrides.get(typ, {}).pop(name, None)
    if name in (setting.get(typ) or {}):
        geloescht = overrides.setdefault("geloescht", {}).setdefault(typ, [])
        if name not in geloescht:
            geloescht.append(name)

    return True, ""
