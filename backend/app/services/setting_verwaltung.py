"""Setting-Verwaltung: eigene Settings anlegen, zusammenführen, aus einem
Charakter ableiten oder aus Einzelelementen zusammenstellen (Original:
CustomElementManager in setting_funktionen.py + setting_merge.py).

Die Kivy-App speichert Nutzer-Settings als custom_*.json in einem eigenen
Verzeichnis neben den mitgelieferten Settings. Die Web-App macht dasselbe:
native Settings liegen read-only unter gamelogic/settings (Teil des Repos),
eigene Settings unter data/settings (Docker-Volume, überlebt Updates).
load_setting() in charakter_init löst Namen erst nativ, dann custom auf —
damit funktionieren Charakter-Anlage, Setting-Wechsel und alle
Spiellogik-Endpoints unverändert auch mit eigenen Settings.
"""

import copy
import json
from pathlib import Path

from app.config import settings
from app.services.charakter_init import load_setting
from app.services.setting_elemente import wende_setting_overrides_an

# Kollektionen, die pro Element (Name -> Daten) zusammengeführt und in der
# Elementauswahl einzeln gewählt werden können
ELEMENT_KOLLEKTIONEN = (
    "voelker",
    "attribute",
    "fertigkeiten_daten",
    "talente",
    "handicaps",
    "maechte",
    "ausruestung",
    "krafte",
)

# In der Elementauswahl wählbare Typen (Attribute kommen aus dem Basis-Setting)
WAEHLBARE_TYPEN = (
    "voelker",
    "fertigkeiten_daten",
    "talente",
    "handicaps",
    "maechte",
    "ausruestung",
    "krafte",
)

# Beim Übernehmen von Superkräften ("krafte") werden die zugehörigen
# Regel-Tabellen des Quell-Settings mitkopiert
_KRAFT_ZUSATZ = (
    "kraft_modifikatoren",
    "krafttypen",
    "kraftsets",
    "machtstufen",
    "super_stile",
    "gegenstaende_der_macht",
    "superstaerke_belastung",
)

# Nicht-Element-Schlüssel, die die Elementauswahl aus dem Basis-Setting nimmt
_BASIS_KEYS = ("attribute", "settingregeln", "startgeld", "waehrung", "cyberware_nebenwirkungen")

_VERBOTENE_ZEICHEN = set('/\\:*?"<>|')


# --- Verzeichnisse & Laden -------------------------------------------------


def _native_dir() -> Path:
    return settings.gamelogic_path / "settings"


def custom_dir() -> Path:
    pfad = settings.custom_settings_path
    pfad.mkdir(parents=True, exist_ok=True)
    return pfad


def ist_natives_setting(name: str) -> bool:
    return (_native_dir() / f"{name}.json").exists()


def ist_custom_setting(name: str) -> bool:
    return (settings.custom_settings_path / f"{name}.json").exists()


def liste_settings() -> list[dict]:
    """Alle Settings (native + eigene) mit Beschreibung und Element-Statistik."""
    ergebnis = []
    for verzeichnis, custom in ((_native_dir(), False), (settings.custom_settings_path, True)):
        if not verzeichnis.exists():
            continue
        for path in sorted(verzeichnis.glob("*.json")):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    setting = json.load(f)
            except (OSError, json.JSONDecodeError):
                continue
            ergebnis.append(
                {
                    "name": path.stem,
                    "datei": path.name,
                    "custom": custom,
                    "beschreibung": setting.get("description", ""),
                    "statistik": statistik(setting),
                }
            )
    return ergebnis


def statistik(setting: dict) -> dict:
    """Element-Anzahl je Kollektion (Original: calculate_setting_statistics)."""
    return {typ: len(setting.get(typ) or {}) for typ in ELEMENT_KOLLEKTIONEN}


# --- Speichern & Löschen ---------------------------------------------------


def pruefe_neuer_name(name: str) -> tuple[str | None, str]:
    """Validiert den Namen eines neuen Settings (wird auch Dateiname)."""
    name = (name or "").strip()
    if not name:
        return None, "Der Name darf nicht leer sein"
    if name.startswith(".") or any(z in _VERBOTENE_ZEICHEN for z in name):
        return None, "Der Name enthält ungültige Zeichen"
    if ist_natives_setting(name):
        return None, f"'{name}' ist ein mitgeliefertes Setting — bitte anderen Namen wählen"
    if ist_custom_setting(name):
        return None, f"Setting '{name}' existiert bereits"
    return name, ""


def speichere_custom_setting(name: str, setting: dict) -> None:
    setting["name"] = name
    # voelker_selected konsistent zum Völker-Bestand halten (Kivy-Altlast,
    # steht so auch in den nativen Setting-Dateien)
    setting["voelker_selected"] = {volk: False for volk in setting.get("voelker") or {}}
    with open(custom_dir() / f"{name}.json", "w", encoding="utf-8") as f:
        json.dump(setting, f, ensure_ascii=False, indent=2)


# Schlüssel, an denen ein Setting-JSON erkennbar ist (Element-Kataloge). Ein
# Charakter-Export hat stattdessen fertigkeiten/voelker_selected/profil_daten
# und passt hier bewusst nicht.
_SETTING_MARKER = ("voelker", "fertigkeiten_daten", "talente", "handicaps", "maechte", "ausruestung")


def _freier_name(basis: str) -> str:
    """Findet einen freien Setting-Namen; nummeriert bei Kollision (nativ/custom)."""
    basis = "".join("_" if z in _VERBOTENE_ZEICHEN else z for z in (basis or "")).strip().lstrip(".")
    if not basis:
        basis = "Importiertes Setting"
    name = basis
    n = 2
    while ist_natives_setting(name) or ist_custom_setting(name):
        name = f"{basis} ({n})"
        n += 1
    return name


def importiere_setting(setting: dict, wunschname: str | None = None) -> tuple[dict, str]:
    """Speichert ein importiertes Setting-JSON (eigener Export oder Kivy
    custom_*.json) als neues eigenes Setting. Kollidierende Namen werden
    nummeriert. Gibt (setting, name) zurück; ValueError bei ungültigem JSON."""
    if not isinstance(setting, dict) or not setting:
        raise ValueError("Kein gültiges Setting-JSON")
    if not any(schluessel in setting for schluessel in _SETTING_MARKER):
        raise ValueError(
            "Die Datei sieht nicht wie ein Setting aus "
            "(keine Völker/Fertigkeiten/Talente/Handicaps/Mächte enthalten)"
        )
    setting = copy.deepcopy(setting)
    # Marker aus get_setting gehört nicht in die gespeicherte Datei
    setting.pop("custom", None)
    name = _freier_name(str(wunschname or setting.get("name") or "Importiertes Setting"))
    speichere_custom_setting(name, setting)
    return setting, name


def loesche_custom_setting(name: str) -> tuple[bool, str]:
    if not ist_custom_setting(name):
        if ist_natives_setting(name):
            return False, f"'{name}' ist ein mitgeliefertes Setting und kann nicht gelöscht werden"
        return False, f"Setting '{name}' nicht gefunden"
    (settings.custom_settings_path / f"{name}.json").unlink()
    return True, ""


# --- Erstellung ------------------------------------------------------------


def leeres_setting(beschreibung: str = "") -> dict:
    """Skelett ohne Elemente; Attribute kommen dann aus der Standard-Config."""
    return {
        "description": beschreibung,
        "voelker": {},
        "fertigkeiten_daten": {},
        "talente": {},
        "handicaps": {},
        "maechte": {},
        "ausruestung": {},
        "settingregeln": {},
    }


def fuehre_zusammen(quellen: list[str]) -> tuple[dict, list[dict]]:
    """Führt mehrere Settings zusammen (Original: merge_settings).

    Element-Kollektionen werden pro Name gemischt; bei gleichem Namen mit
    abweichenden Daten gewinnt die spätere Quelle, der Konflikt wird
    protokolliert ({typ, name, quellen}). Skalare Schlüssel (startgeld,
    settingregeln, ...) ebenso: letzte Quelle gewinnt.
    """
    ergebnis: dict = {}
    konflikte: list[dict] = []
    herkunft: dict = {}

    for quelle in quellen:
        setting = load_setting(quelle)
        for key, wert in setting.items():
            if key in ("name", "description", "voelker_selected"):
                continue
            if key in ELEMENT_KOLLEKTIONEN and isinstance(wert, dict):
                ziel = ergebnis.setdefault(key, {})
                for elem_name, elem in wert.items():
                    if elem_name in ziel and ziel[elem_name] != elem:
                        konflikte.append(
                            {
                                "typ": key,
                                "name": elem_name,
                                "quellen": [herkunft[(key, elem_name)], quelle],
                            }
                        )
                    ziel[elem_name] = copy.deepcopy(elem)
                    herkunft[(key, elem_name)] = quelle
            else:
                if key in ergebnis and ergebnis[key] != wert:
                    konflikte.append(
                        {"typ": key, "name": key, "quellen": [herkunft[key], quelle]}
                    )
                ergebnis[key] = copy.deepcopy(wert)
                herkunft[key] = quelle

    return ergebnis, konflikte


def aus_charakter(charakter_daten: dict) -> dict:
    """Setting-Schnappschuss eines Charakters (Original: create_default_setting).

    Nimmt das aktive Setting des Charakters und mischt seine
    setting_overrides (eigene, bearbeitete und gelöschte Elemente) fest ein —
    das Ergebnis ist ein eigenständiges Setting mit dem Regelstand, den der
    Charakter tatsächlich benutzt.
    """
    setting = load_setting(charakter_daten.get("active_setting_name", "SWAE"))
    return copy.deepcopy(wende_setting_overrides_an(setting, charakter_daten))


def aus_elementauswahl(
    basis_name: str, auswahl: dict[str, dict[str, list[str]]]
) -> tuple[dict, list[dict], list[str]]:
    """Stellt ein Setting aus einzeln gewählten Elementen zusammen.

    auswahl: {quell_setting: {typ: [element_namen]}}. Attribute, Settingregeln
    und Startgeld kommen aus dem Basis-Setting; ohne gewählte Fertigkeiten
    werden dessen Fertigkeiten komplett übernommen (ein Setting ohne
    Fertigkeiten wäre nicht spielbar). Rückgabe: (setting, konflikte,
    fehlende_elemente).
    """
    basis = load_setting(basis_name)
    ergebnis: dict = {typ: {} for typ in WAEHLBARE_TYPEN if typ != "krafte"}
    for key in _BASIS_KEYS:
        if key in basis:
            ergebnis[key] = copy.deepcopy(basis[key])

    konflikte: list[dict] = []
    fehlend: list[str] = []
    herkunft: dict = {}

    for quelle, elemente in auswahl.items():
        setting = load_setting(quelle)
        for typ, namen in (elemente or {}).items():
            if typ not in WAEHLBARE_TYPEN:
                raise ValueError(f"Unbekannter Element-Typ '{typ}'")
            katalog = setting.get(typ) or {}
            ziel = ergebnis.setdefault(typ, {})
            for name in namen:
                if name not in katalog:
                    fehlend.append(f"{quelle}: {typ}/{name}")
                    continue
                if name in ziel and ziel[name] != katalog[name]:
                    konflikte.append(
                        {"typ": typ, "name": name, "quellen": [herkunft[(typ, name)], quelle]}
                    )
                ziel[name] = copy.deepcopy(katalog[name])
                herkunft[(typ, name)] = quelle
            if typ == "krafte" and namen:
                for zusatz in _KRAFT_ZUSATZ:
                    if zusatz in setting and zusatz not in ergebnis:
                        ergebnis[zusatz] = copy.deepcopy(setting[zusatz])

    if not ergebnis.get("fertigkeiten_daten"):
        ergebnis["fertigkeiten_daten"] = copy.deepcopy(basis.get("fertigkeiten_daten") or {})

    return ergebnis, konflikte, fehlend


# --- Bearbeitung gespeicherter Custom-Settings -----------------------------


def _lade_custom(name: str) -> tuple[dict | None, str]:
    if not ist_custom_setting(name):
        if ist_natives_setting(name):
            return None, f"'{name}' ist ein mitgeliefertes Setting und kann nicht bearbeitet werden"
        return None, f"Setting '{name}' nicht gefunden"
    with open(settings.custom_settings_path / f"{name}.json", "r", encoding="utf-8") as f:
        return json.load(f), ""


def elemente_hinzufuegen(
    name: str, quelle: str, elemente: dict[str, list[str]]
) -> tuple[dict | None, str, list[str]]:
    """Kopiert Elemente aus einem Quell-Setting in ein eigenes Setting."""
    setting, fehler = _lade_custom(name)
    if setting is None:
        return None, fehler, []
    try:
        quell_setting = load_setting(quelle)
    except FileNotFoundError:
        return None, f"Quell-Setting '{quelle}' nicht gefunden", []

    fehlend: list[str] = []
    for typ, namen in (elemente or {}).items():
        if typ not in WAEHLBARE_TYPEN:
            return None, f"Unbekannter Element-Typ '{typ}'", []
        katalog = quell_setting.get(typ) or {}
        ziel = setting.setdefault(typ, {})
        for elem_name in namen:
            if elem_name not in katalog:
                fehlend.append(f"{typ}/{elem_name}")
                continue
            ziel[elem_name] = copy.deepcopy(katalog[elem_name])
        if typ == "krafte" and namen:
            for zusatz in _KRAFT_ZUSATZ:
                if zusatz in quell_setting and zusatz not in setting:
                    setting[zusatz] = copy.deepcopy(quell_setting[zusatz])

    speichere_custom_setting(name, setting)
    return setting, "", fehlend


def element_entfernen(name: str, typ: str, element_name: str) -> tuple[dict | None, str]:
    setting, fehler = _lade_custom(name)
    if setting is None:
        return None, fehler
    if typ not in WAEHLBARE_TYPEN:
        return None, f"Unbekannter Element-Typ '{typ}'"
    if element_name not in (setting.get(typ) or {}):
        return None, f"'{element_name}' nicht in '{typ}' von '{name}' gefunden"
    del setting[typ][element_name]
    speichere_custom_setting(name, setting)
    return setting, ""


def aktualisiere_metadaten(
    name: str, beschreibung: str | None, neuer_name: str | None
) -> tuple[dict | None, str, str]:
    """Beschreibung ändern und/oder umbenennen. Gibt (setting, name, fehler) zurück."""
    setting, fehler = _lade_custom(name)
    if setting is None:
        return None, name, fehler

    if beschreibung is not None:
        setting["description"] = beschreibung

    ziel_name = name
    if neuer_name is not None and neuer_name.strip() != name:
        geprueft, fehler = pruefe_neuer_name(neuer_name)
        if geprueft is None:
            return None, name, fehler
        ziel_name = geprueft

    speichere_custom_setting(ziel_name, setting)
    if ziel_name != name:
        (settings.custom_settings_path / f"{name}.json").unlink()
    return setting, ziel_name, ""
