from typing import Any

from pydantic import BaseModel


class SpiellogikRequest(BaseModel):
    charakter_daten: dict[str, Any]
    element_name: str | None = None
    # "Trotzdem auswählen": überspringt Rang- und Voraussetzungs-Prüfung
    # (Original: ignore_rang_check / ignore_voraussetzungen)
    ignoriere_pruefungen: bool = False
    # Ausrüstung kaufen/verkaufen: Menge und abweichender Stückpreis (wie im
    # Original anpassbar). preis=None -> Katalogpreis des Settings.
    menge: int = 1
    preis: float | None = None


class CharakterbogenRequest(SpiellogikRequest):
    # Druckerfreundliche Version ohne Hintergrundfarben (wie im Original)
    printer_friendly: bool = False


class SettingElementRequest(SpiellogikRequest):
    # Bearbeitung von Setting-Elementen (talente, handicaps, maechte, ausruestung)
    element_typ: str
    element_daten: dict[str, Any] | None = None
    # gesetzt beim Bearbeiten; weicht er von element_name ab, ist es eine Umbenennung
    alter_name: str | None = None


class SpiellogikResponse(BaseModel):
    success: bool
    message: str = ""
    charakter_daten: dict[str, Any] | None = None
    # True, wenn die Ablehnung per ignoriere_pruefungen übersprungen werden kann
    bestaetigung_moeglich: bool = False


class BerechneResponse(BaseModel):
    parade: int
    robustheit: int
    bewegungsweite: int
    verbleibende_attributsteigerungen: int
    verbleibende_fertigkeitssteigerungen: int
    verbleibende_handicap_punkte: int
