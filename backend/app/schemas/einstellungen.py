from typing import Literal

from pydantic import BaseModel


class SettingErstellenRequest(BaseModel):
    name: str
    beschreibung: str = ""
    modus: Literal["leer", "kopie", "zusammenfuehrung", "aus_charakter", "elementauswahl"]
    # kopie: genau eine Quelle; zusammenfuehrung: zwei oder mehr (Reihenfolge
    # entscheidet — bei Konflikten gewinnt die spätere Quelle)
    quellen: list[str] = []
    # aus_charakter
    charakter_id: int | None = None
    # elementauswahl: Basis liefert Attribute/Settingregeln/Startgeld,
    # elemente = {quell_setting: {typ: [element_namen]}}
    basis: str | None = None
    elemente: dict[str, dict[str, list[str]]] = {}


class SettingUpdateRequest(BaseModel):
    neuer_name: str | None = None
    beschreibung: str | None = None


class ElementeHinzufuegenRequest(BaseModel):
    quelle: str
    elemente: dict[str, list[str]]


class ElementEntfernenRequest(BaseModel):
    typ: str
    element_name: str


class SettingVerwaltungResponse(BaseModel):
    """Antwort der Verwaltungs-Endpoints: Kennzahlen statt komplettem Setting."""

    name: str
    custom: bool = True
    beschreibung: str = ""
    statistik: dict[str, int] = {}
    konflikte: list[dict] = []
    warnungen: list[str] = []
