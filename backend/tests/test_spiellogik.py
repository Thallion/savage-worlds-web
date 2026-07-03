import pytest
from fastapi.testclient import TestClient

from main import app
from app.services.charakter_init import initialisiere_charakter_daten

client = TestClient(app)


@pytest.fixture
def daten():
    return initialisiere_charakter_daten("Testheld", "SWAE")


def aktion(pfad: str, daten: dict, element: str | None = None) -> dict:
    resp = client.post(f"/api/spiellogik/{pfad}", json={"charakter_daten": daten, "element_name": element})
    assert resp.status_code == 200
    return resp.json()


# --- Attribute ---

def test_attribut_steigern_und_senken(daten):
    r = aktion("attribut/steigern", daten, "Stärke")
    assert r["success"]
    d = r["charakter_daten"]
    assert d["attribute"]["Stärke"]["wert"] == 6
    assert d["verbleibende_attributsteigerungen"] == 4

    r = aktion("attribut/senken", d, "Stärke")
    d = r["charakter_daten"]
    assert d["attribute"]["Stärke"]["wert"] == 4
    assert d["verbleibende_attributsteigerungen"] == 5


def test_attribut_maximum_w12_plus_2(daten):
    daten["attribute"]["Stärke"] = {"attribut_name": "Stärke", "wert": 12, "modifier": 2}
    r = aktion("attribut/steigern", daten, "Stärke")
    assert not r["success"]


def test_attribut_senken_unter_minimum_abgelehnt(daten):
    r = aktion("attribut/senken", daten, "Stärke")
    assert not r["success"]


def test_attribut_steigern_ohne_punkte_abgelehnt(daten):
    daten["verbleibende_attributsteigerungen"] = 0
    r = aktion("attribut/steigern", daten, "Stärke")
    assert not r["success"]


# --- Fertigkeiten ---

def test_fertigkeit_erster_kauf_ungelernt_zu_w4(daten):
    r = aktion("fertigkeit/steigern", daten, "Kämpfen")
    d = r["charakter_daten"]
    assert d["fertigkeiten"]["Kämpfen"]["wuerfel"] == {"value": 4, "modifier": 0, "typ": "fertigkeit"}
    assert d["fertigkeiten"]["Kämpfen"]["ausgewaehlt"]
    assert d["verbleibende_fertigkeitssteigerungen"] == 11


def test_fertigkeit_ueber_attribut_kostet_zwei_punkte(daten):
    # Kämpfen (Geschicklichkeit W4) auf W4 -> W6 kostet 2 Punkte
    d = aktion("fertigkeit/steigern", daten, "Kämpfen")["charakter_daten"]
    d = aktion("fertigkeit/steigern", d, "Kämpfen")["charakter_daten"]
    assert d["fertigkeiten"]["Kämpfen"]["wuerfel"]["value"] == 6
    assert d["verbleibende_fertigkeitssteigerungen"] == 9  # 12 - 1 - 2


def test_grundfertigkeit_nicht_unter_w4_senkbar(daten):
    r = aktion("fertigkeit/senken", daten, "Athletik")
    assert not r["success"]


# --- Handicaps: Punkte-Ökonomie ---

def test_handicap_punkte_addieren_sich(daten):
    d = aktion("handicap/waehlen", daten, "Arm")["charakter_daten"]  # leicht = 1
    assert d["verbleibende_handicap_punkte"] == 1
    d = aktion("handicap/waehlen", d, "Alt")["charakter_daten"]  # schwer = 2
    assert d["gesamt_handicap_punkte"] == 3
    assert d["verbleibende_handicap_punkte"] == 3


def test_handicap_limit_vier_punkte(daten):
    d = aktion("handicap/waehlen", daten, "Alt")["charakter_daten"]
    d = aktion("handicap/waehlen", d, "Arrogant")["charakter_daten"]
    r = aktion("handicap/waehlen", d, "Arm")
    assert not r["success"]


def test_handicap_entfernen_gibt_punkte_zurueck(daten):
    d = aktion("handicap/waehlen", daten, "Arm")["charakter_daten"]
    d = aktion("handicap/entfernen", d, "Arm")["charakter_daten"]
    assert d["gesamt_handicap_punkte"] == 0
    assert d["verbleibende_handicap_punkte"] == 0


def test_handicap_entfernen_nach_ausgeben_abgelehnt(daten):
    d = aktion("handicap/waehlen", daten, "Arm")["charakter_daten"]
    d = aktion("handicap-punkte/einloesen", d, "fertigkeit")["charakter_daten"]
    r = aktion("handicap/entfernen", d, "Arm")
    assert not r["success"]


def test_einloesen_attribut_und_fertigkeit(daten):
    d = aktion("handicap/waehlen", daten, "Alt")["charakter_daten"]  # 2 Punkte
    d = aktion("handicap-punkte/einloesen", d, "attribut")["charakter_daten"]
    assert d["verbleibende_handicap_punkte"] == 0
    assert d["verbleibende_attributsteigerungen"] == 6
    assert d["maximale_attributsteigerungen"] == 6

    r = aktion("handicap-punkte/einloesen", d, "fertigkeit")
    assert not r["success"]  # keine Punkte mehr


def test_einloesen_unbekannte_option(daten):
    r = aktion("handicap-punkte/einloesen", daten, "startgeld")
    assert not r["success"]


# --- Volk-Effekte ---

def test_volk_zwerg_effekte(daten):
    d = aktion("volk/waehlen", daten, "Zwerg")["charakter_daten"]
    assert d["attribute"]["Konstitution"]["wert"] == 6
    assert "Nachtsicht" in d["selected_talente"]
    assert list(d["voelker_selected"].keys()) == ["Zwerg"]


def test_volk_wechsel_nimmt_effekte_zurueck(daten):
    d = aktion("volk/waehlen", daten, "Zwerg")["charakter_daten"]
    d = aktion("volk/waehlen", d, "Mensch")["charakter_daten"]
    assert d["attribute"]["Konstitution"]["wert"] == 4
    assert "Nachtsicht" not in d["selected_talente"]
    assert list(d["voelker_selected"].keys()) == ["Mensch"]


def test_volk_wechsel_erhaelt_manuelle_steigerung(daten):
    d = aktion("volk/waehlen", daten, "Zwerg")["charakter_daten"]  # Kon 4 -> 6
    d = aktion("attribut/steigern", d, "Konstitution")["charakter_daten"]  # 6 -> 8
    d = aktion("volk/waehlen", d, "Mensch")["charakter_daten"]  # -2 Volk-Bonus
    assert d["attribute"]["Konstitution"]["wert"] == 6
    assert d["verbleibende_attributsteigerungen"] == 4


def test_volk_talent_nicht_entfernbar(daten):
    d = aktion("volk/waehlen", daten, "Zwerg")["charakter_daten"]
    r = aktion("talent/entfernen", d, "Nachtsicht")
    assert not r["success"]


def test_volk_fertigkeits_startbonus(daten):
    # Avionen: Wahrnehmung +2 (Grundfertigkeit, bereits W4/0) -> W6
    d = aktion("volk/waehlen", daten, "Avionen")["charakter_daten"]
    assert d["fertigkeiten"]["Wahrnehmung"]["wuerfel"]["value"] == 6
    d = aktion("volk/waehlen", d, "Mensch")["charakter_daten"]
    assert d["fertigkeiten"]["Wahrnehmung"]["wuerfel"]["value"] == 4


# --- Talente: Ökonomie + Voraussetzungen ---

def mit_talent_slot(daten: dict, anzahl: int = 1) -> dict:
    daten["verbleibende_talente"] = anzahl
    return daten


def test_talent_ohne_slot_abgelehnt(daten):
    r = aktion("talent/waehlen", daten, "Aristokrat")
    assert not r["success"]
    assert "Slot" in r["message"]


def test_talent_mit_slot_waehlbar(daten):
    d = aktion("talent/waehlen", mit_talent_slot(daten), "Aristokrat")["charakter_daten"]
    assert "Aristokrat" in d["selected_talente"]
    assert d["verbleibende_talente"] == 0


def test_talent_voraussetzung_attribut_kuerzel(daten):
    # Arkane Resistenz erfordert WIL W8
    r = aktion("talent/waehlen", mit_talent_slot(daten), "Arkane Resistenz")
    assert not r["success"]
    assert "WIL W8" in r["message"]

    daten["attribute"]["Willenskraft"]["wert"] = 8
    r = aktion("talent/waehlen", mit_talent_slot(daten), "Arkane Resistenz")
    assert r["success"]


def test_talent_voraussetzung_anderes_talent(daten):
    # "Glück" ist Voraussetzung für "Großes Glück"
    r = aktion("talent/waehlen", mit_talent_slot(daten), "Großes Glück")
    assert not r["success"]

    daten["selected_talente"] = ["Glück"]
    r = aktion("talent/waehlen", mit_talent_slot(daten), "Großes Glück")
    assert r["success"]


def test_talent_hoeherer_rang_bei_erschaffung_abgelehnt(daten):
    r = aktion("talent/waehlen", mit_talent_slot(daten), "Ausweichen")  # Rang F
    assert not r["success"]
    assert "Fortgeschritten" in r["message"]


def test_talent_entfernen_gibt_slot_zurueck(daten):
    d = aktion("talent/waehlen", mit_talent_slot(daten), "Aristokrat")["charakter_daten"]
    d = aktion("talent/entfernen", d, "Aristokrat")["charakter_daten"]
    assert d["verbleibende_talente"] == 1


def test_einloesen_talent_slot(daten):
    d = aktion("handicap/waehlen", daten, "Alt")["charakter_daten"]  # 2 Punkte
    d = aktion("handicap-punkte/einloesen", d, "talent")["charakter_daten"]
    assert d["verbleibende_talente"] == 1
    assert d["verbleibende_handicap_punkte"] == 0


def test_mensch_freies_talent_gibt_slot(daten):
    d = aktion("volk/waehlen", daten, "Mensch")["charakter_daten"]
    assert d["verbleibende_talente"] == 1
    d = aktion("volk/waehlen", d, "Zwerg")["charakter_daten"]
    assert d["verbleibende_talente"] == 0


# --- Mächte ---

def mit_arkanem_hintergrund(daten: dict) -> dict:
    """AH (Magie) regulär über einen Talent-Slot wählen."""
    return aktion("talent/waehlen", mit_talent_slot(daten), "AH (Magie)")["charakter_daten"]


def test_macht_ohne_ah_abgelehnt(daten):
    r = aktion("macht/waehlen", daten, "Abwehren")
    assert not r["success"]
    assert "arkaner Hintergrund" in r["message"]


def test_macht_mit_ah_waehlbar(daten):
    d = mit_arkanem_hintergrund(daten)
    d = aktion("macht/waehlen", d, "Abwehren")["charakter_daten"]
    assert d["selected_maechte"] == ["Abwehren"]

    w = berechne(d)
    assert w["machtpunkte"] == 10  # AH (Magie)
    assert w["verbleibende_maechte"] == 2  # 3 Slots - 1 gewählt


def test_macht_slots_begrenzt(daten):
    # AH (Begabt) hat nur 1 Mächte-Slot
    d = aktion("talent/waehlen", mit_talent_slot(daten), "AH (Begabt)")["charakter_daten"]
    d = aktion("macht/waehlen", d, "Abwehren")["charakter_daten"]
    r = aktion("macht/waehlen", d, "Blenden")
    assert not r["success"]
    assert "Slots belegt" in r["message"]


def test_macht_entfernen(daten):
    d = mit_arkanem_hintergrund(daten)
    d = aktion("macht/waehlen", d, "Abwehren")["charakter_daten"]
    d = aktion("macht/entfernen", d, "Abwehren")["charakter_daten"]
    assert d["selected_maechte"] == []


# --- Abgeleitete Werte ---

def berechne(daten: dict) -> dict:
    resp = client.post("/api/spiellogik/berechne", json={"charakter_daten": daten})
    assert resp.status_code == 200
    return resp.json()


def test_berechne_basiswerte(daten):
    w = berechne(daten)
    # Kämpfen ungelernt -> Parade 2; Konstitution W4 -> Robustheit 4
    assert w == {
        "parade": 2, "robustheit": 4, "bewegungsweite": 6, "groesse": 0, "bennys": 3,
        "machtpunkte": 0,
        "verbleibende_maechte": 0,
        "verbleibende_attributsteigerungen": 5,
        "verbleibende_fertigkeitssteigerungen": 12,
        "verbleibende_handicap_punkte": 0,
        "verbleibende_talente": 0,
    }


def test_berechne_parade_mit_kaempfen_und_block(daten):
    d = aktion("fertigkeit/steigern", daten, "Kämpfen")["charakter_daten"]  # W4
    d["selected_talente"] = ["Block"]
    w = berechne(d)
    assert w["parade"] == 5  # 2 + 4//2 + 1


def test_berechne_nicht_kumulative_gruppe(daten):
    daten["selected_talente"] = ["Lieblingswaffe", "Absolute Lieblingswaffe"]
    w = berechne(daten)
    assert w["parade"] == 4  # 2 + max(1, 2), nicht 2+1+2


def test_berechne_handicap_mit_stufen_suffix(daten):
    d = aktion("handicap/waehlen", daten, "Langsam_schwer")["charakter_daten"]
    w = berechne(d)
    assert w["bewegungsweite"] == 4  # 6 - 2


def test_berechne_volk_boni(daten):
    d = aktion("volk/waehlen", daten, "Zwerg")["charakter_daten"]
    w = berechne(d)
    assert w["bewegungsweite"] == 5  # 6 - 1 (Zwerg)
    assert w["robustheit"] == 5  # Konstitution W6 durch Volk


def test_berechne_bennys_durch_glueck(daten):
    daten["selected_talente"] = ["Glück", "Großes Glück"]
    w = berechne(daten)
    assert w["bennys"] == 5


# --- Setting-Wechsel ---

def test_setting_wechseln_setzt_eigenschaften_zurueck(daten):
    daten["profil_daten"] = {"Name": "Testheld", "Konzept": "Söldner"}
    d = aktion("attribut/steigern", daten, "Stärke")["charakter_daten"]
    d = aktion("handicap/waehlen", d, "Arm")["charakter_daten"]

    r = aktion("setting/wechseln", d, "Hellfrost")
    assert r["success"]
    neu = r["charakter_daten"]
    assert neu["active_setting_name"] == "Hellfrost"
    assert neu["profil_daten"] == {"Name": "Testheld", "Konzept": "Söldner"}
    assert neu["attribute"]["Stärke"]["wert"] == 4
    assert len(neu["fertigkeiten"]) == 41  # Hellfrost hat mehr Fertigkeiten als SWAE
    assert neu["selected_handicaps"] == []
    assert neu["verbleibende_attributsteigerungen"] == 5
    assert neu["gesamt_handicap_punkte"] == 0


def test_setting_wechseln_gleiches_setting_abgelehnt(daten):
    r = aktion("setting/wechseln", daten, "SWAE")
    assert not r["success"]
    assert "bereits aktiv" in r["message"]


def test_setting_wechseln_unbekanntes_setting_abgelehnt(daten):
    r = aktion("setting/wechseln", daten, "Gibt Es Nicht")
    assert not r["success"]
    assert "nicht gefunden" in r["message"]
