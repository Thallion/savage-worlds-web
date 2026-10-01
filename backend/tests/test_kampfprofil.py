"""Kampfprofil eines Charakters — insbesondere die Macht-Felder.

Der Kampfsimulator braucht die arkane Fertigkeit als reinen
Fertigkeitsnamen ("Zaubern"), damit sie den Fertigkeitsschlüssel des
Charakters trifft — die AH-Beschreibung liefert sie als
"Zaubern (Verstand)".
"""

import pytest
from fastapi.testclient import TestClient

from main import app
from app.services.charakter_init import initialisiere_charakter_daten, load_setting
from app.services.kampfprofil import _arkane_fertigkeit

client = TestClient(app)

IMPLEMENTIERTE_MAECHTE = [
    "Geschoss",
    "Schutz",
    "Abwehren",
    "Waffe verbessern",
    "Heilung",
    "Betäuben",
    "Verwirrung",
    "Linderung",
    "Blenden",
    "Eigenschaft erhöhen/senken",
    "Verstricken",
    "Flächenschlag",
    "Strahl",
    "Arkaner Schutz",
    "Schlummer",
]


@pytest.fixture
def setting():
    return load_setting("SWAE")


@pytest.fixture
def daten():
    return initialisiere_charakter_daten("Testmagier", "SWAE")


def kampfprofil(daten: dict) -> dict:
    resp = client.post("/api/spiellogik/kampfprofil", json={"charakter_daten": daten})
    assert resp.status_code == 200
    return resp.json()


def test_ohne_arkanen_hintergrund_keine_maechte(daten):
    profil = kampfprofil(daten)
    assert profil["arkane_fertigkeit"] == ""
    assert profil["maechte"] == []


def test_arkane_fertigkeit_ohne_klammerzusatz(daten, setting):
    daten["selected_talente"] = ["AH (Magie)"]
    assert _arkane_fertigkeit(daten, setting) == "Zaubern"


@pytest.mark.parametrize(
    "talent,fertigkeit",
    [
        ("AH (Magie)", "Zaubern"),
        ("AH (Wunder)", "Glaube"),
        ("AH (Psionik)", "Psionik"),
        ("AH (Begabt)", "Fokus"),
    ],
)
def test_arkane_fertigkeit_je_hintergrund(daten, setting, talent, fertigkeit):
    daten["selected_talente"] = [talent]
    assert _arkane_fertigkeit(daten, setting) == fertigkeit


def test_maechte_landen_im_profil(daten):
    daten["selected_talente"] = ["AH (Magie)"]
    daten["selected_maechte"] = ["Geschoss", "Schutz"]
    profil = kampfprofil(daten)
    assert profil["arkane_fertigkeit"] == "Zaubern"
    assert profil["maechte"] == ["Geschoss", "Schutz"]
    assert profil["machtpunkte"] >= 0


def test_implementierte_maechte_existieren_im_setting(setting):
    """Die Namen im Simulator-Katalog müssen zum Setting passen, sonst
    kann ein Charakter die Macht nie wirken."""
    katalog = set(setting.get("maechte", {}))
    assert set(IMPLEMENTIERTE_MAECHTE) <= katalog


def test_handicaps_behalten_ihre_stufe(daten):
    """Der Simulator wertet z. B. Dünnhäutig (schwer) mit –4 statt –2 aus."""
    daten["selected_handicaps"] = ["Dünnhäutig_schwer", "Langsam (leicht: -1 Bewegung)", "Feige"]
    handicaps = kampfprofil(daten)["handicaps"]
    assert "Dünnhäutig (schwer)" in handicaps
    assert "Langsam (leicht)" in handicaps
    assert "Feige" in handicaps


def test_talente_ohne_klammerzusatz(daten):
    daten["selected_talente"] = ["Block"]
    assert "Block" in kampfprofil(daten)["talente"]


def test_groesse_im_profil(daten):
    assert kampfprofil(daten)["groesse"] == 0
