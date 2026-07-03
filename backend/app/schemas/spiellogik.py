from typing import Any

from pydantic import BaseModel


class SpiellogikRequest(BaseModel):
    charakter_daten: dict[str, Any]
    element_name: str | None = None
    # "Trotzdem auswählen": überspringt Rang- und Voraussetzungs-Prüfung
    # (Original: ignore_rang_check / ignore_voraussetzungen)
    ignoriere_pruefungen: bool = False


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
