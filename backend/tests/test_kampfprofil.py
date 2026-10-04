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
    # Ohne Suffix kommt die Stufe aus dem Setting-Katalog
    assert "Feige (schwer)" in handicaps


def test_talente_ohne_klammerzusatz(daten):
    daten["selected_talente"] = ["Block"]
    assert "Block" in kampfprofil(daten)["talente"]


def test_groesse_im_profil(daten):
    assert kampfprofil(daten)["groesse"] == 0


def test_setting_handicap_mit_anzeigenamen():
    daten = initialisiere_charakter_daten("Geode", "Savage Aventurien")
    daten["selected_handicaps"] = ["Behindernde_Rüstung_schwer"]
    assert kampfprofil(daten)["handicaps"] == ["Behindernde Rüstung (schwer)"]


def test_talent_behaelt_klammerzusatz_aus_dem_setting():
    daten = initialisiere_charakter_daten("Geode", "Savage Aventurien")
    daten["selected_talente"] = ["AH (Geode)", "Bevorzugte Mächte (Druide)"]
    talente = kampfprofil(daten)["talente"]
    assert "AH (Geode)" in talente
    assert "Bevorzugte Mächte (Druide)" in talente


def test_volks_handicaps_nicht_doppelt():
    """Die Freitext-Handicaps des Zwergs stehen schon als Auto-Handicaps
    in der Auswahl und dürfen nicht ein zweites Mal auftauchen."""
    daten = initialisiere_charakter_daten("Zwerg", "Savage Aventurien")
    resp = client.post(
        "/api/spiellogik/volk/waehlen", json={"charakter_daten": daten, "element_name": "Zwerg"}
    )
    handicaps = kampfprofil(resp.json()["charakter_daten"])["handicaps"]
    assert handicaps == ["Langsam (leicht)", "Phobie (schwer)", "Stur (leicht)"]


@pytest.mark.parametrize(
    "beschreibung,parade",
    [
        ("Stä+W4, Parade +1, Reichweite 1, Zweihändig.", 1),
        ("Stä+W10, Parade -1.", -1),
        ("Stä+W8, Parade –1, Reichweite 1", -1),
        ("Stä+W6, Parade +1 wenn zweihändig.", 0),  # bedingt: zählt nicht
        ("Stä+W4.", 0),
    ],
)
def test_waffen_parade_aus_beschreibung(beschreibung, parade):
    from app.services.ausruestung import waffen_parade

    assert waffen_parade({"beschreibung": beschreibung}) == parade


def test_waffe_mit_parade_im_profil():
    daten = initialisiere_charakter_daten("Geode", "Savage Aventurien")
    daten["ausruestung_selected"] = {
        "Kampfstab": {"anzahl": 1, "angelegt": False},
        "Dolch": {"anzahl": 1, "angelegt": False},
    }
    waffen = {w["name"]: w for w in kampfprofil(daten)["waffen"]}
    assert waffen["Kampfstab"]["parade"] == 1
    assert waffen["Dolch"]["parade"] == 0


def _geode_mit_kampfstab():
    daten = initialisiere_charakter_daten("Geode", "Savage Aventurien")
    r = client.post(
        "/api/spiellogik/ausruestung/kaufen",
        json={"charakter_daten": daten, "element_name": "Kampfstab"},
    )
    return r.json()["charakter_daten"]


def _parade(daten: dict) -> int:
    return client.post("/api/spiellogik/berechne", json={"charakter_daten": daten}).json()["parade"]


def test_angelegte_waffe_erhoeht_parade():
    daten = _geode_mit_kampfstab()
    ohne = _parade(daten)
    r = client.post(
        "/api/spiellogik/ausruestung/anlegen",
        json={"charakter_daten": daten, "element_name": "Kampfstab"},
    ).json()
    assert r["success"]
    assert _parade(r["charakter_daten"]) == ohne + 1


def test_kampfprofil_parade_ohne_angelegte_waffe():
    """Der Simulator rechnet den Bonus der geführten Waffe selbst an."""
    daten = _geode_mit_kampfstab()
    daten["ausruestung_selected"]["Kampfstab"]["angelegt"] = True
    profil = kampfprofil(daten)
    assert profil["parade"] == _parade(daten) - 1
    assert profil["waffen"][0]["angelegt"] is True
