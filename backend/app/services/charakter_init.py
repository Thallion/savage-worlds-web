"""Initialisierung von charakter_daten aus Setting- und Basis-Konfiguration."""

import copy
import json

from app.config import settings

START_ATTRIBUTSTEIGERUNGEN = 5
START_FERTIGKEITSSTEIGERUNGEN = 12


def load_setting(setting_name: str) -> dict:
    path = settings.gamelogic_path / "settings" / f"{setting_name}.json"
    if not path.exists():
        raise FileNotFoundError(setting_name)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_config(name: str) -> dict:
    path = settings.gamelogic_path / "config" / name
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def baue_attribute(setting: dict, config: dict) -> dict:
    attribute = setting.get("attribute")
    if attribute:
        return copy.deepcopy(attribute)
    # Settings ohne eigene Attribut-Definition (z. B. 50 Fathoms) nutzen den Standard
    return {
        name: {"attribut_name": name, "wert": werte.get("wert", 4), "modifier": werte.get("modifier", 0)}
        for name, werte in config.get("standard_attribute", {}).items()
    }


def baue_fertigkeiten(setting: dict, config: dict) -> dict:
    grundfertigkeiten = set(config.get("grundfertigkeiten", []))
    fertigkeiten = {}
    for name, attribut_liste in setting.get("fertigkeiten_daten", {}).items():
        grund = name in grundfertigkeiten
        fertigkeiten[name] = {
            "fertigkeit_name": name,
            "grundfertigkeit": grund,
            "ausgewaehlt": grund,
            "aktiv": True,
            "wuerfel": {"value": 4, "modifier": 0 if grund else -2, "typ": "fertigkeit"},
            "attribut": attribut_liste[0] if attribut_liste else None,
        }
    return fertigkeiten


def initialisiere_charakter_daten(char_name: str, setting_name: str) -> dict:
    setting = load_setting(setting_name)
    config = load_config("eigenschaften_config.json")

    start_attr = config.get("start_attributsteigerungen", START_ATTRIBUTSTEIGERUNGEN)
    start_fert = config.get("start_fertigkeitssteigerungen", START_FERTIGKEITSSTEIGERUNGEN)

    return {
        "profil_daten": {"Name": char_name},
        "active_setting_name": setting_name,
        "char_gen_completed": False,
        "attribute": baue_attribute(setting, config),
        "fertigkeiten": baue_fertigkeiten(setting, config),
        "selected_handicaps": [],
        "selected_talente": [],
        "selected_maechte": [],
        "voelker_selected": {},
        "verbleibende_attributsteigerungen": start_attr,
        "maximale_attributsteigerungen": start_attr,
        "verbleibende_fertigkeitssteigerungen": start_fert,
        "maximale_fertigkeitssteigerungen": start_fert,
        "gesamt_handicap_punkte": 0,
        "verbleibende_handicap_punkte": 0,
        "verbleibende_talente": 0,
        "aufstiege_gesamt": 0,
        "verbleibende_aufstiege": 0,
    }


def ergaenze_fehlende_eigenschaften(daten: dict) -> tuple[dict, bool]:
    """Füllt bei Bestandscharakteren leere attribute/fertigkeiten und fehlende
    Punkte-Felder nach. Gibt (neues Dict, wurde_geaendert) zurück."""
    config = load_config("eigenschaften_config.json")
    try:
        setting = load_setting(daten.get("active_setting_name", ""))
    except FileNotFoundError:
        setting = {}

    neu = copy.deepcopy(daten)
    geaendert = False

    if not neu.get("attribute"):
        neu["attribute"] = baue_attribute(setting, config)
        geaendert = True
    if not neu.get("fertigkeiten"):
        neu["fertigkeiten"] = baue_fertigkeiten(setting, config)
        geaendert = True

    start_attr = config.get("start_attributsteigerungen", START_ATTRIBUTSTEIGERUNGEN)
    start_fert = config.get("start_fertigkeitssteigerungen", START_FERTIGKEITSSTEIGERUNGEN)
    defaults = {
        "verbleibende_attributsteigerungen": start_attr,
        "maximale_attributsteigerungen": start_attr,
        "verbleibende_fertigkeitssteigerungen": start_fert,
        "maximale_fertigkeitssteigerungen": start_fert,
        "gesamt_handicap_punkte": 0,
        "verbleibende_handicap_punkte": 0,
        "verbleibende_talente": 0,
        "aufstiege_gesamt": 0,
        "verbleibende_aufstiege": 0,
    }
    for feld, wert in defaults.items():
        if feld not in neu:
            neu[feld] = wert
            geaendert = True

    return neu, geaendert
