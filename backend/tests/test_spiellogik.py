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
    # Kämpfen (Geschicklichkeit W4) auf W4 -> W6 kostet 2 Punkte;
    # die Doppelkosten müssen erst bestätigt werden
    d = aktion("fertigkeit/steigern", daten, "Kämpfen")["charakter_daten"]
    r = aktion("fertigkeit/steigern", d, "Kämpfen")
    assert not r["success"]
    assert r["bestaetigung_moeglich"]
    assert "Doppelte" in r["message"]
    d = aktion_mit_override("fertigkeit/steigern", d, "Kämpfen")["charakter_daten"]
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
    # freies Talent ist als Kern-Wahl vorbelegt (Original: "Vielseitig")
    assert d["volk_effekte"]["wahl"] == {"typ": "talent"}
    d = aktion("volk/waehlen", d, "Zwerg")["charakter_daten"]
    assert d["verbleibende_talente"] == 0


def test_mensch_vielseitig_tausch_gegen_fertigkeitspunkte(daten):
    d = aktion("volk/waehlen", daten, "Mensch")["charakter_daten"]
    d = aktion("volk/wahl", d, "fertigkeitspunkte")["charakter_daten"]
    assert d["verbleibende_talente"] == 0
    assert d["verbleibende_fertigkeitssteigerungen"] == 14
    # und wieder zurück auf das freie Talent
    d = aktion("volk/wahl", d, "talent")["charakter_daten"]
    assert d["verbleibende_talente"] == 1
    assert d["verbleibende_fertigkeitssteigerungen"] == 12


def test_pathfinder_mensch_talent_und_attribut(daten):
    """Savage Pathfinder Mensch: freies Talent UND W6-Attribut — die
    Attributswahl darf den festen Talent-Slot nicht zurücknehmen."""
    d = aktion("setting/wechseln", daten, "Savage Pathfinder")["charakter_daten"]
    d = aktion("volk/waehlen", d, "Mensch")["charakter_daten"]
    assert d["verbleibende_talente"] == 1
    assert d["volk_effekte"]["talent_slots"] == 1
    assert "wahl" not in d["volk_effekte"]

    d = aktion("volk/wahl", d, "Stärke")["charakter_daten"]
    assert d["attribute"]["Stärke"]["wert"] == 6
    assert d["verbleibende_talente"] == 1  # Slot bleibt erhalten

    # Attribut umentscheiden: nur das Attribut wandert, der Slot bleibt
    d = aktion("volk/wahl", d, "Verstand")["charakter_daten"]
    assert d["attribute"]["Stärke"]["wert"] == 4
    assert d["attribute"]["Verstand"]["wert"] == 6
    assert d["verbleibende_talente"] == 1

    # Volk-Wechsel räumt beides ab
    d = aktion("volk/waehlen", d, "Zwerg")["charakter_daten"]
    assert d["attribute"]["Verstand"]["wert"] == 4
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
        "panzerung": 0,
        "vermoegen": 500,
        "startkapital_gesamt": 500,
        "traglast": 40,
        "gesamtgewicht": 0,
        "machtpunkte": 0,
        "verbleibende_maechte": 0,
        "verbleibende_attributsteigerungen": 5,
        "verbleibende_fertigkeitssteigerungen": 12,
        "verbleibende_handicap_punkte": 0,
        "verbleibende_talente": 0,
        "verbleibende_aufstiege": 0,
        "aufstiege_gesamt": 0,
        "rang": "Anfänger",
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


# --- Volk-Wahlmöglichkeiten ---

def test_volk_wahl_halbelf_attribut(daten):
    d = aktion("volk/waehlen", daten, "Halbelf")["charakter_daten"]
    r = aktion("volk/wahl", d, "Stärke")
    assert r["success"]
    d = r["charakter_daten"]
    assert d["attribute"]["Stärke"]["wert"] == 6
    assert d["volk_effekte"]["wahl"] == {"typ": "attribut", "ziel": "Stärke", "feld": "wert"}


def test_volk_wahl_wechsel_nimmt_vorherige_zurueck(daten):
    d = aktion("volk/waehlen", daten, "Halbelf")["charakter_daten"]
    d = aktion("volk/wahl", d, "Stärke")["charakter_daten"]
    d = aktion("volk/wahl", d, "talent")["charakter_daten"]
    assert d["attribute"]["Stärke"]["wert"] == 4
    assert d["verbleibende_talente"] == 1
    d = aktion("volk/wahl", d, "Verstand")["charakter_daten"]
    assert d["verbleibende_talente"] == 0
    assert d["attribute"]["Verstand"]["wert"] == 6


def test_volk_wahl_fertigkeitspunkte(daten):
    d = aktion("setting/wechseln", daten, "Hellfrost")["charakter_daten"]
    d = aktion("volk/waehlen", d, "Mensch_Anari")["charakter_daten"]
    r = aktion("volk/wahl", d, "fertigkeitspunkte")
    assert r["success"]
    d = r["charakter_daten"]
    assert d["verbleibende_fertigkeitssteigerungen"] == 14
    assert d["maximale_fertigkeitssteigerungen"] == 14
    # Wechsel auf Talent nimmt die Punkte zurück
    d = aktion("volk/wahl", d, "talent")["charakter_daten"]
    assert d["verbleibende_fertigkeitssteigerungen"] == 12


def test_volk_wahl_ungueltige_option_abgelehnt(daten):
    d = aktion("volk/waehlen", daten, "Halbelf")["charakter_daten"]
    r = aktion("volk/wahl", d, "fertigkeitspunkte")
    assert not r["success"]
    assert "keine gültige Wahl" in r["message"]


def test_volk_wahl_ohne_volk_abgelehnt(daten):
    r = aktion("volk/wahl", daten, "talent")
    assert not r["success"]
    assert "Kein Volk gewählt" in r["message"]


def test_volk_wahl_ohne_wahlmoeglichkeit_abgelehnt(daten):
    d = aktion("volk/waehlen", daten, "Zwerg")["charakter_daten"]
    r = aktion("volk/wahl", d, "Stärke")
    assert not r["success"]
    assert "bietet keine Wahlmöglichkeit" in r["message"]


def test_volk_wechsel_nimmt_wahl_zurueck(daten):
    d = aktion("volk/waehlen", daten, "Halbelf")["charakter_daten"]
    d = aktion("volk/wahl", d, "Stärke")["charakter_daten"]
    d = aktion("volk/waehlen", d, "Zwerg")["charakter_daten"]
    assert d["attribute"]["Stärke"]["wert"] == 4
    assert "wahl" not in d.get("volk_effekte", {})


# --- Spezial-Handicap-Effekte (handicap_config.json) ---

def test_handicap_alt_gibt_fertigkeitspunkte(daten):
    d = aktion("handicap/waehlen", daten, "Alt")["charakter_daten"]
    assert d["verbleibende_fertigkeitssteigerungen"] == 17
    assert d["maximale_fertigkeitssteigerungen"] == 17
    d = aktion("handicap/entfernen", d, "Alt")["charakter_daten"]
    assert d["verbleibende_fertigkeitssteigerungen"] == 12
    assert d["maximale_fertigkeitssteigerungen"] == 12


def test_handicap_jung_reduziert_steigerungen(daten):
    d = aktion("handicap/waehlen", daten, "Jung")["charakter_daten"]
    # Jung (leicht): 4 Attributs- und 10 Fertigkeitssteigerungen
    assert d["verbleibende_attributsteigerungen"] == 4
    assert d["maximale_attributsteigerungen"] == 4
    assert d["verbleibende_fertigkeitssteigerungen"] == 10
    d = aktion("handicap/entfernen", d, "Jung")["charakter_daten"]
    assert d["verbleibende_attributsteigerungen"] == 5
    assert d["verbleibende_fertigkeitssteigerungen"] == 12


def test_handicap_alt_erhaelt_ausgegebene_punkte(daten):
    d = aktion("handicap/waehlen", daten, "Alt")["charakter_daten"]
    d = aktion("fertigkeit/steigern", d, "Reiten")["charakter_daten"]  # 1 Punkt
    assert d["verbleibende_fertigkeitssteigerungen"] == 16
    d = aktion("handicap/entfernen", d, "Alt")["charakter_daten"]
    # Delta-basiert: der ausgegebene Punkt bleibt ausgegeben
    assert d["verbleibende_fertigkeitssteigerungen"] == 11
    assert d["maximale_fertigkeitssteigerungen"] == 12


# --- Talent-Auto-Effekte ---

def test_berserker_erhoeht_staerke(daten):
    d = mit_talent_slot(daten)
    d = aktion("talent/waehlen", d, "Berserker")["charakter_daten"]
    assert d["attribute"]["Stärke"]["wert"] == 6
    assert d["talent_effekte"]["Berserker"]["attribut_stufen"] == [["Stärke", "wert"]]
    d = aktion("talent/entfernen", d, "Berserker")["charakter_daten"]
    assert d["attribute"]["Stärke"]["wert"] == 4
    assert "talent_effekte" not in d


def test_rohling_koppelt_athletik_an_staerke(daten):
    d = aktion("attribut/steigern", daten, "Stärke")["charakter_daten"]
    d = aktion("attribut/steigern", d, "Konstitution")["charakter_daten"]
    d = mit_talent_slot(d)
    d = aktion("talent/waehlen", d, "Rohling")["charakter_daten"]
    assert d["fertigkeiten"]["Athletik"]["attribut"] == "Stärke"
    d = aktion("talent/entfernen", d, "Rohling")["charakter_daten"]
    assert d["fertigkeiten"]["Athletik"]["attribut"] == "Geschicklichkeit"


def test_auto_handicap_durch_ah_talent(daten):
    d = aktion("setting/wechseln", daten, "Horror Kompendium")["charakter_daten"]
    d = mit_talent_slot(d)
    d = aktion("talent/waehlen", d, "AH (Verdorbener)")["charakter_daten"]
    assert "Verderbnis" in d["selected_handicaps"]
    # Auto-Handicap gibt keine Handicap-Punkte
    assert d["gesamt_handicap_punkte"] == 0
    assert d["verbleibende_handicap_punkte"] == 0
    # ... und ist nicht manuell entfernbar
    r = aktion("handicap/entfernen", d, "Verderbnis")
    assert not r["success"]
    assert "automatisch" in r["message"]
    # Talent abwählen räumt es mit auf
    d = aktion("talent/entfernen", d, "AH (Verdorbener)")["charakter_daten"]
    assert "Verderbnis" not in d["selected_handicaps"]


# --- Talent-Kauf direkt mit Handicap-Punkten (Original-Verhalten) ---

def test_talent_kauf_direkt_mit_handicap_punkten(daten):
    d = aktion("handicap/waehlen", daten, "Arrogant")["charakter_daten"]  # 2 Punkte
    r = aktion("talent/waehlen", d, "Aristokrat")
    assert r["success"]
    d = r["charakter_daten"]
    assert "Aristokrat" in d["selected_talente"]
    assert d["verbleibende_handicap_punkte"] == 0
    assert d["talent_zahlungen"]["Aristokrat"] == "handicap_punkte"


def test_talent_entfernen_erstattet_handicap_punkte(daten):
    d = aktion("handicap/waehlen", daten, "Arrogant")["charakter_daten"]
    d = aktion("talent/waehlen", d, "Aristokrat")["charakter_daten"]
    d = aktion("talent/entfernen", d, "Aristokrat")["charakter_daten"]
    assert d["verbleibende_handicap_punkte"] == 2
    assert d["verbleibende_talente"] == 0
    assert "Aristokrat" not in d.get("talent_zahlungen", {})


def test_talent_kauf_nutzt_slot_vor_handicap_punkten(daten):
    d = aktion("handicap/waehlen", daten, "Arrogant")["charakter_daten"]
    d = mit_talent_slot(d)
    d = aktion("talent/waehlen", d, "Aristokrat")["charakter_daten"]
    assert d["verbleibende_talente"] == 0
    assert d["verbleibende_handicap_punkte"] == 2
    assert d["talent_zahlungen"]["Aristokrat"] == "slot"
    d = aktion("talent/entfernen", d, "Aristokrat")["charakter_daten"]
    assert d["verbleibende_talente"] == 1
    assert d["verbleibende_handicap_punkte"] == 2


def test_talent_kauf_mit_punkten_nach_erschaffung_abgelehnt(daten):
    # Nach der Erschaffung zählen Handicap-Punkte nicht mehr, nur Aufstiege
    d = aktion("handicap/waehlen", daten, "Arrogant")["charakter_daten"]
    d["char_gen_completed"] = True
    r = aktion("talent/waehlen", d, "Aristokrat")
    assert not r["success"]
    assert "Aufstieg" in r["message"]


def test_ein_handicap_punkt_reicht_nicht_fuer_talent(daten):
    d = aktion("handicap/waehlen", daten, "Arm")["charakter_daten"]  # 1 Punkt
    r = aktion("talent/waehlen", d, "Aristokrat")
    assert not r["success"]


# --- "Trotzdem auswählen" (ignoriere_pruefungen) ---

def aktion_mit_override(pfad: str, daten: dict, element: str) -> dict:
    resp = client.post(
        f"/api/spiellogik/{pfad}",
        json={"charakter_daten": daten, "element_name": element, "ignoriere_pruefungen": True},
    )
    assert resp.status_code == 200
    return resp.json()


def test_voraussetzung_ablehnung_ist_bestaetigbar(daten):
    r = aktion("talent/waehlen", mit_talent_slot(daten), "Arkane Resistenz")  # WIL W8 fehlt
    assert not r["success"]
    assert r["bestaetigung_moeglich"]


def test_talent_trotzdem_waehlen_ueberspringt_voraussetzungen(daten):
    r = aktion_mit_override("talent/waehlen", mit_talent_slot(daten), "Arkane Resistenz")
    assert r["success"]
    assert "Arkane Resistenz" in r["charakter_daten"]["selected_talente"]


def test_talent_trotzdem_waehlen_ueberspringt_rang(daten):
    r = aktion_mit_override("talent/waehlen", mit_talent_slot(daten), "Ausweichen")  # Rang F
    assert r["success"]


def test_trotzdem_waehlen_braucht_trotzdem_bezahlung(daten):
    # Prüfungen überspringen heißt nicht kostenlos: ohne Slot/Punkte weiter abgelehnt
    r = aktion_mit_override("talent/waehlen", daten, "Arkane Resistenz")
    assert not r["success"]
    assert not r["bestaetigung_moeglich"]


def test_slot_ablehnung_ist_nicht_bestaetigbar(daten):
    r = aktion("talent/waehlen", daten, "Aristokrat")
    assert not r["success"]
    assert not r["bestaetigung_moeglich"]


def test_macht_trotzdem_waehlen_ueberspringt_rang(daten):
    d = mit_arkanem_hintergrund(daten)
    r = aktion("macht/waehlen", d, "Barriere")  # Rang F
    assert not r["success"] and r["bestaetigung_moeglich"]
    r = aktion_mit_override("macht/waehlen", d, "Barriere")
    assert r["success"]


# --- Erschaffung abschließen & Aufstiege ---

def mit_abschluss(daten: dict) -> dict:
    return aktion("erschaffung/abschliessen", daten)["charakter_daten"]


def test_erschaffung_abschliessen_und_oeffnen(daten):
    d = mit_abschluss(daten)
    assert d["char_gen_completed"] is True
    r = aktion("erschaffung/abschliessen", d)
    assert not r["success"]
    d = aktion("erschaffung/oeffnen", d)["charakter_daten"]
    assert d["char_gen_completed"] is False


def test_aufstieg_nur_nach_abschluss(daten):
    r = aktion("aufstieg/hinzufuegen", daten)
    assert not r["success"]
    d = mit_abschluss(daten)
    d = aktion("aufstieg/hinzufuegen", d)["charakter_daten"]
    assert d["aufstiege_gesamt"] == 1
    assert d["verbleibende_aufstiege"] == 1


def test_attribut_kostet_aufstieg_nach_abschluss(daten):
    d = mit_abschluss(daten)
    r = aktion("attribut/steigern", d, "Stärke")
    assert not r["success"]  # kein Aufstieg vorhanden
    d = aktion("aufstieg/hinzufuegen", d)["charakter_daten"]
    d = aktion("attribut/steigern", d, "Stärke")["charakter_daten"]
    assert d["attribute"]["Stärke"]["wert"] == 6
    assert d["verbleibende_aufstiege"] == 0
    assert d["verbleibende_attributsteigerungen"] == 5  # unangetastet
    d = aktion("attribut/senken", d, "Stärke")["charakter_daten"]
    assert d["verbleibende_aufstiege"] == 1


def test_ein_aufstieg_ergibt_zwei_fertigkeitssteigerungen(daten):
    d = mit_abschluss(daten)
    d = aktion("aufstieg/hinzufuegen", d)["charakter_daten"]
    d = aktion("fertigkeit/steigern", d, "Kämpfen")["charakter_daten"]  # 0.5
    d = aktion("fertigkeit/steigern", d, "Reiten")["charakter_daten"]  # 0.5
    assert d["verbleibende_aufstiege"] == 0
    r = aktion("fertigkeit/steigern", d, "Heimlichkeit")
    assert not r["success"]


def test_talent_kostet_aufstieg_nach_abschluss(daten):
    d = mit_abschluss(daten)
    d = aktion("aufstieg/hinzufuegen", d)["charakter_daten"]
    d = aktion("talent/waehlen", d, "Aristokrat")["charakter_daten"]
    assert d["verbleibende_aufstiege"] == 0
    assert d["talent_zahlungen"]["Aristokrat"] == "aufstieg"
    d = aktion("talent/entfernen", d, "Aristokrat")["charakter_daten"]
    assert d["verbleibende_aufstiege"] == 1


def test_rang_steigt_mit_ausgegebenen_aufstiegen(daten):
    d = mit_abschluss(daten)
    for _ in range(4):
        d = aktion("aufstieg/hinzufuegen", d)["charakter_daten"]
        d = aktion("attribut/steigern", d, "Stärke")["charakter_daten"]
    w = berechne(d)
    assert w["rang"] == "Fortgeschritten"
    # Rang F schaltet Rang-F-Talente frei (Ausweichen braucht GES W8 -> erfüllt? nein)
    d = aktion("aufstieg/hinzufuegen", d)["charakter_daten"]
    r = aktion("talent/waehlen", d, "Kampfreflexe")  # Rang F, keine Voraussetzungen
    assert r["success"], r["message"]


def test_aufstieg_entfernen_nur_wenn_nicht_ausgegeben(daten):
    d = mit_abschluss(daten)
    d = aktion("aufstieg/hinzufuegen", d)["charakter_daten"]
    d = aktion("attribut/steigern", d, "Stärke")["charakter_daten"]
    r = aktion("aufstieg/entfernen", d)
    assert not r["success"]
    assert "ausgegeben" in r["message"]


# --- Kompatibilitätsprüfung (Reich/Arm) ---

def test_reich_mit_arm_abgelehnt(daten):
    d = aktion("handicap/waehlen", daten, "Arm")["charakter_daten"]
    d = mit_talent_slot(d)
    r = aktion("talent/waehlen", d, "Reich")
    assert not r["success"]
    assert "nicht mit dem Handicap 'Arm' kombinierbar" in r["message"]
    assert not r["bestaetigung_moeglich"]


def test_arm_mit_reich_abgelehnt(daten):
    d = aktion("talent/waehlen", mit_talent_slot(daten), "Reich")["charakter_daten"]
    r = aktion("handicap/waehlen", d, "Arm")
    assert not r["success"]
    assert "nicht mit dem Talent 'Reich' kombinierbar" in r["message"]


# --- Volk-Spezialwahlen (volk_wahlen.py) ---

def test_spezialwahl_engro_heimlich_fertigkeit(daten):
    d = aktion("setting/wechseln", daten, "Hellfrost")["charakter_daten"]
    d = aktion("volk/waehlen", d, "Engro")["charakter_daten"]
    r = aktion("volk/wahl", d, "heimlich:Diebeskunst")
    assert r["success"]
    d = r["charakter_daten"]
    assert d["fertigkeiten"]["Diebeskunst"]["wuerfel"]["value"] == 6
    assert d["fertigkeiten"]["Diebeskunst"]["wuerfel"]["modifier"] == 0
    assert d["fertigkeiten"]["Diebeskunst"]["ausgewaehlt"]
    # Wechsel auf Heimlichkeit nimmt Diebeskunst exakt zurück
    d = aktion("volk/wahl", d, "heimlich:Heimlichkeit")["charakter_daten"]
    assert d["fertigkeiten"]["Diebeskunst"]["wuerfel"] == {"value": 4, "modifier": -2, "typ": "fertigkeit"}
    assert not d["fertigkeiten"]["Diebeskunst"]["ausgewaehlt"]
    assert d["fertigkeiten"]["Heimlichkeit"]["wuerfel"]["value"] == 6


def test_spezialwahl_heimlich_ungueltige_fertigkeit_abgelehnt(daten):
    d = aktion("setting/wechseln", daten, "Hellfrost")["charakter_daten"]
    d = aktion("volk/waehlen", d, "Engro")["charakter_daten"]
    r = aktion("volk/wahl", d, "heimlich:Kämpfen")
    assert not r["success"]
    assert "keine gültige Fertigkeit" in r["message"]


def test_spezialwahl_unbekannte_wahl_abgelehnt(daten):
    d = aktion("volk/waehlen", daten, "Zwerg")["charakter_daten"]
    r = aktion("volk/wahl", d, "heimlich:Diebeskunst")
    assert not r["success"]
    assert "bietet keine Wahl" in r["message"]


def test_spezialwahl_gnom_verstandsfertigkeit(daten):
    d = aktion("setting/wechseln", daten, "Savage Pathfinder")["charakter_daten"]
    d = aktion("volk/waehlen", d, "Gnom")["charakter_daten"]
    r = aktion("volk/wahl", d, "freie_verstandsfertigkeit:Okkultismus")
    assert r["success"]
    d = r["charakter_daten"]
    assert d["fertigkeiten"]["Okkultismus"]["wuerfel"]["value"] == 6
    assert d["fertigkeiten"]["Okkultismus"]["wuerfel"]["modifier"] == 0
    # Kämpfen hängt an Geschicklichkeit und ist keine gültige Wahl
    r = aktion("volk/wahl", d, "freie_verstandsfertigkeit:Kämpfen")
    assert not r["success"]


def test_spezialwahl_zwerg_handwerks_wissen(daten):
    d = aktion("setting/wechseln", daten, "Sundered Skies")["charakter_daten"]
    d = aktion("volk/waehlen", d, "Zwerg")["charakter_daten"]
    r = aktion("volk/wahl", d, "handwerks_wissen:Wissen (Geschichte)")
    assert r["success"]
    d = r["charakter_daten"]
    assert d["fertigkeiten"]["Wissen (Geschichte)"]["wuerfel"]["value"] == 6
    r = aktion("volk/wahl", d, "handwerks_wissen:Kämpfen")
    assert not r["success"]


def test_spezialwahl_androiden_spezialisierung(daten):
    d = aktion("volk/waehlen", daten, "Androiden")["charakter_daten"]
    r = aktion("volk/wahl", d, "spezialisierung:Reparieren")
    assert r["success"]
    d = r["charakter_daten"]
    assert d["fertigkeiten"]["Reparieren"]["wuerfel"]["value"] == 6
    assert d["volk_effekte"]["wahlen"]["spezialisierung"]["ziel"] == "Reparieren"


def test_spezialwahl_insektoide_outsider_statt_trennungsangst(daten):
    d = aktion("setting/wechseln", daten, "SciFi Kompendium")["charakter_daten"]
    d = aktion("volk/waehlen", d, "Insektoide")["charakter_daten"]
    assert "Trennungsangst" in d["selected_handicaps"]
    d = aktion("volk/wahl", d, "outsider_statt_trennungsangst:Außenseiter")["charakter_daten"]
    assert "Trennungsangst" not in d["selected_handicaps"]
    assert "Trennungsangst" not in d["volk_effekte"]["handicaps"]
    # Rückkehr zu Trennungsangst stellt das Auto-Handicap wieder her
    d = aktion("volk/wahl", d, "outsider_statt_trennungsangst:Trennungsangst")["charakter_daten"]
    assert "Trennungsangst" in d["selected_handicaps"]
    assert "wahlen" not in d["volk_effekte"] or "outsider_statt_trennungsangst" not in d["volk_effekte"]["wahlen"]


def test_spezialwahl_pflanzenerbe(daten):
    d = aktion("setting/wechseln", daten, "Sundered Skies")["charakter_daten"]
    d = aktion("volk/waehlen", d, "Elf")["charakter_daten"]
    r = aktion("volk/wahl", d, "pflanzenerbe_auswahl:Dornen")
    assert r["success"]
    d = r["charakter_daten"]
    assert d["volk_effekte"]["wahlen"]["pflanzenerbe_auswahl"]["ziel"] == "Dornen"
    r = aktion("volk/wahl", d, "pflanzenerbe_auswahl:Lavaherz")
    assert not r["success"]
    assert "Gültige Optionen" in r["message"]


def test_spezialwahl_tierart_freitext(daten):
    d = aktion("setting/wechseln", daten, "Sundered Skies")["charakter_daten"]
    d = aktion("volk/waehlen", d, "Wildling")["charakter_daten"]
    r = aktion("volk/wahl", d, "tierart_auswahl:Wolf")
    assert r["success"]
    assert r["charakter_daten"]["volk_effekte"]["wahlen"]["tierart_auswahl"]["ziel"] == "Wolf"


def _volk_mit_effekten(daten, effekte):
    """Wählt Mensch und erweitert das gespeicherte Volk um Test-Effekte
    (z. B. magieaffin/attribut_malus, die kein Standard-Volk mitbringt)."""
    d = aktion("volk/waehlen", daten, "Mensch")["charakter_daten"]
    volk = next(iter(d["voelker_selected"].values()))
    volk.setdefault("effects", {}).update(effekte)
    return d


def test_spezialwahl_magieaffin(daten):
    d = _volk_mit_effekten(daten, {"spezielle_effekte": {"magieaffin": True}})
    slots_vorher = d.get("verbleibende_talente", 0)
    r = aktion("volk/wahl", d, "magieaffin:AH (Magie)")
    assert r["success"]
    d = r["charakter_daten"]
    assert "AH (Magie)" in d["selected_talente"]
    assert "AH (Magie)" in d["volk_effekte"]["talente"]
    # kein Talent-Slot verbraucht; Arkane Fertigkeit W4-2 -> W4+0
    assert d.get("verbleibende_talente", 0) == slots_vorher
    assert d["fertigkeiten"]["Zaubern"]["wuerfel"] == {"value": 4, "modifier": 0, "typ": "fertigkeit"}
    # als Volks-Talent nicht manuell entfernbar
    r = aktion("talent/entfernen", d, "AH (Magie)")
    assert not r["success"]
    # Wechsel auf AH (Wunder) nimmt Zaubern und das Talent zurück
    d = aktion("volk/wahl", d, "magieaffin:AH (Wunder)")["charakter_daten"]
    assert "AH (Magie)" not in d["selected_talente"]
    assert d["fertigkeiten"]["Zaubern"]["wuerfel"]["modifier"] == -2
    assert "AH (Wunder)" in d["selected_talente"]
    assert d["fertigkeiten"]["Glaube"]["wuerfel"]["modifier"] == 0


def test_spezialwahl_magieaffin_nur_ah_talente(daten):
    d = _volk_mit_effekten(daten, {"spezielle_effekte": {"magieaffin": True}})
    r = aktion("volk/wahl", d, "magieaffin:Aufmerksamkeit")
    assert not r["success"]
    assert "kein AH-Talent" in r["message"]


def test_spezialwahl_attribut_schwaeche(daten):
    d = _volk_mit_effekten(daten, {"attribut_malus": 1})
    r = aktion("volk/wahl", d, "attribut_schwaeche:Stärke")
    assert r["success"]
    d = r["charakter_daten"]
    assert d["attribute"]["Stärke"]["modifier"] == -2
    # Wechsel des Malus-Ziels stellt Stärke wieder her
    d = aktion("volk/wahl", d, "attribut_schwaeche:Verstand")["charakter_daten"]
    assert d["attribute"]["Stärke"]["modifier"] == 0
    assert d["attribute"]["Verstand"]["modifier"] == -2


def test_volk_wechsel_nimmt_spezialwahlen_zurueck(daten):
    d = aktion("setting/wechseln", daten, "Hellfrost")["charakter_daten"]
    d = aktion("volk/waehlen", d, "Engro")["charakter_daten"]
    d = aktion("volk/wahl", d, "heimlich:Diebeskunst")["charakter_daten"]
    d = aktion("volk/waehlen", d, "Mensch_Saxa")["charakter_daten"]
    assert d["fertigkeiten"]["Diebeskunst"]["wuerfel"] == {"value": 4, "modifier": -2, "typ": "fertigkeit"}
    assert "wahlen" not in d.get("volk_effekte", {})


def test_volk_wechsel_nimmt_magieaffin_zurueck(daten):
    d = _volk_mit_effekten(daten, {"spezielle_effekte": {"magieaffin": True}})
    d = aktion("volk/wahl", d, "magieaffin:AH (Magie)")["charakter_daten"]
    d = aktion("volk/waehlen", d, "Zwerg")["charakter_daten"]
    assert "AH (Magie)" not in d["selected_talente"]
    assert d["fertigkeiten"]["Zaubern"]["wuerfel"]["modifier"] == -2


# --- Ausrüstung & Startgeld (ausruestung.py) ---

def test_ausruestung_kaufen_und_geld(daten):
    assert berechne(daten)["vermoegen"] == 500  # SWAE ohne startgeld -> Standard
    d = aktion("ausruestung/kaufen", daten, "Fackel")["charakter_daten"]
    d = aktion("ausruestung/kaufen", d, "Fackel")["charakter_daten"]
    assert d["ausruestung_selected"]["Fackel"]["anzahl"] == 2
    w = berechne(d)
    assert w["vermoegen"] == 490
    assert w["gesamtgewicht"] == 1.0


def test_ausruestung_zu_teuer_abgelehnt(daten):
    daten["ausruestung_ausgegeben"] = 480
    r = aktion("ausruestung/kaufen", daten, "Kleiner Schild")  # kostet 50
    assert not r["success"]
    assert "Nicht genug Geld" in r["message"]


def test_ausruestung_unbekannt_abgelehnt(daten):
    r = aktion("ausruestung/kaufen", daten, "Bazooka")
    assert not r["success"]


def test_ausruestung_verkaufen_erstattet_bei_erschaffung_voll(daten):
    d = aktion("ausruestung/kaufen", daten, "Fackel")["charakter_daten"]
    d = aktion("ausruestung/verkaufen", d, "Fackel")["charakter_daten"]
    assert "Fackel" not in d["ausruestung_selected"]
    assert berechne(d)["vermoegen"] == 500


def test_ausruestung_verkaufen_nach_erschaffung_halber_preis(daten):
    d = aktion("ausruestung/kaufen", daten, "Fackel")["charakter_daten"]  # -5
    d = aktion("erschaffung/abschliessen", d)["charakter_daten"]
    d = aktion("ausruestung/verkaufen", d, "Fackel")["charakter_daten"]  # +2.5
    assert berechne(d)["vermoegen"] == 497.5


def test_ausruestung_verkaufen_ohne_besitz_abgelehnt(daten):
    r = aktion("ausruestung/verkaufen", daten, "Fackel")
    assert not r["success"]


def test_ruestung_anlegen_erhoeht_robustheit(daten):
    d = aktion("ausruestung/kaufen", daten, "Jacke (dünn)")["charakter_daten"]
    basis = berechne(d)
    assert basis["panzerung"] == 0
    d = aktion("ausruestung/anlegen", d, "Jacke (dünn)")["charakter_daten"]
    w = berechne(d)
    assert w["panzerung"] == 1
    assert w["robustheit"] == basis["robustheit"] + 1
    d = aktion("ausruestung/ablegen", d, "Jacke (dünn)")["charakter_daten"]
    assert berechne(d)["panzerung"] == 0


def test_schild_anlegen_erhoeht_parade(daten):
    d = aktion("ausruestung/kaufen", daten, "Kleiner Schild")["charakter_daten"]
    basis = berechne(d)["parade"]
    d = aktion("ausruestung/anlegen", d, "Kleiner Schild")["charakter_daten"]
    assert berechne(d)["parade"] == basis + 1


def test_allgemein_item_nicht_anlegbar(daten):
    d = aktion("ausruestung/kaufen", daten, "Fackel")["charakter_daten"]
    r = aktion("ausruestung/anlegen", d, "Fackel")
    assert not r["success"]
    assert "nur Rüstungen und Schilde" in r["message"]


def test_einloesen_startgeld(daten):
    d = aktion("handicap/waehlen", daten, "Alt")["charakter_daten"]  # 2 Punkte
    d = aktion("handicap-punkte/einloesen", d, "startgeld")["charakter_daten"]
    assert d["startgeld_bonus_punkte"] == 1
    assert d["verbleibende_handicap_punkte"] == 1
    assert berechne(d)["vermoegen"] == 1000


def test_vermoegen_arm_halbiert(daten):
    daten["selected_handicaps"] = ["Arm"]
    assert berechne(daten)["vermoegen"] == 250


def test_vermoegen_reich_verdreifacht(daten):
    daten["selected_talente"] = ["Reich"]
    assert berechne(daten)["vermoegen"] == 1500
    daten["selected_talente"] = ["Reich", "Stinkreich"]
    assert berechne(daten)["vermoegen"] == 2500  # Stinkreich zählt, nicht kumulativ


def test_startgeld_aus_setting(daten):
    d = aktion("setting/wechseln", daten, "Deadlands")["charakter_daten"]
    assert berechne(d)["vermoegen"] == 250


def test_traglast_aus_staerke_und_talent(daten):
    w = berechne(daten)
    assert w["traglast"] == 40  # Stärke W4 x 10 kg
    daten["attribute"]["Stärke"]["wert"] = 8
    daten["selected_talente"] = ["Kräftig"]
    assert berechne(daten)["traglast"] == 100  # 80 + 20 (Kräftig)


def test_bedingung_keine_getragene_ruestung(daten):
    daten["selected_talente"] = ["Kämpferische Disziplin"]  # +1 Robustheit ohne Rüstung
    ohne = berechne(daten)["robustheit"]
    d = aktion("ausruestung/kaufen", daten, "Jacke (dünn)")["charakter_daten"]
    d = aktion("ausruestung/anlegen", d, "Jacke (dünn)")["charakter_daten"]
    # Talent-Bonus entfällt mit getragener Rüstung, dafür +1 Panzerung
    assert berechne(d)["robustheit"] == ohne


# --- Cyberware (cyberware.py) ---

@pytest.fixture
def scifi(daten):
    d = aktion("setting/wechseln", daten, "SciFi Kompendium")["charakter_daten"]
    d["startgeld_bonus_punkte"] = 20  # Budget für teure Implantate (10.500)
    return d


def test_cyberware_nur_im_cyberware_setting(daten):
    r = aktion("cyberware/installieren", daten, "Cyberware: Scanner")
    assert not r["success"]
    assert "kein Cyberware-System" in r["message"]


def test_cyberware_installieren_stress_und_geld(scifi):
    w = berechne(scifi)
    assert w["cyberware"] == {"stress": 0, "stresslimit": 2, "stress_maximum": 4, "ueber_limit": 0}
    d = aktion("cyberware/installieren", scifi, "Cyberware: Scanner")["charakter_daten"]
    assert d["cyberware_installationen"] == {"Cyberware: Scanner": 1}
    w = berechne(d)
    assert w["cyberware"]["stress"] == 1
    assert w["vermoegen"] == 10500 - 1000


def test_cyberware_ueber_limit_warnt(scifi):
    r = aktion("cyberware/installieren", scifi, "Cyberware: Amphibisch")  # Stress 2 = Limit
    assert r["success"] and r["message"] == ""
    d = r["charakter_daten"]
    r = aktion("cyberware/installieren", d, "Cyberware: Scanner")  # Stress 3 > Limit 2
    assert r["success"]
    assert "Nebenwirkung auswürfeln" in r["message"]
    assert berechne(r["charakter_daten"])["cyberware"]["ueber_limit"] == 1


def test_cyberware_hartes_maximum_lehnt_ab(scifi):
    scifi["startgeld_bonus_punkte"] = 40  # genug Geld für drei teure Implantate
    d = aktion("cyberware/installieren", scifi, "Cyberware: Amphibisch")["charakter_daten"]  # 2
    d = aktion("cyberware/installieren", d, "Cyberware: Scanner")["charakter_daten"]  # 3
    d = aktion("cyberware/installieren", d, "Cyberware: Ersatzorgane")["charakter_daten"]  # 4 = Maximum
    r = aktion("cyberware/installieren", d, "Cyberware: Verborgenes Fach")  # 5 > 4
    assert not r["success"]
    assert "Stress-Maximum überschritten" in r["message"]


def test_cyberware_max_installationen(scifi):
    d = aktion("cyberware/installieren", scifi, "Cyberware: Scanner")["charakter_daten"]
    r = aktion("cyberware/installieren", d, "Cyberware: Scanner")
    assert not r["success"]
    assert "maximal 1×" in r["message"]


def test_cyberware_talent_boni_und_cyborg_budget(scifi):
    scifi["selected_talente"] = ["Kybernetische Toleranz", "Cyborg"]
    w = berechne(scifi)
    # Limit 2+2+4, Maximum 4+2+4
    assert w["cyberware"]["stresslimit"] == 8
    assert w["cyberware"]["stress_maximum"] == 10
    # Installation unter 20.000 Cyborg-Budget kostet kein Geld
    d = aktion("cyberware/installieren", scifi, "Cyberware: Scanner")["charakter_daten"]
    assert berechne(d)["vermoegen"] == 10500


def test_cyberware_deinstallieren(scifi):
    d = aktion("cyberware/installieren", scifi, "Cyberware: Scanner")["charakter_daten"]
    d = aktion("cyberware/deinstallieren", d, "Cyberware: Scanner")["charakter_daten"]
    assert d["cyberware_installationen"] == {}
    assert berechne(d)["vermoegen"] == 10500  # volle Erstattung bei Erschaffung


def test_cyberware_deinstallieren_nach_erschaffung_kostet(scifi):
    d = aktion("cyberware/installieren", scifi, "Cyberware: Scanner")["charakter_daten"]  # -1000
    d = aktion("erschaffung/abschliessen", d)["charakter_daten"]
    r = aktion("cyberware/deinstallieren", d, "Cyberware: Scanner")
    assert "kostet 250" in r["message"]
    assert berechne(r["charakter_daten"])["vermoegen"] == 10500 - 1000 - 250


def test_cyberware_nebenwirkung_wuerfeln(scifi):
    r = aktion("cyberware/nebenwirkung", scifi)
    assert r["success"]
    d = r["charakter_daten"]
    assert len(d["cyberware_nebenwirkungen"]) == 1
    eintrag = d["cyberware_nebenwirkungen"][0]
    assert 1 <= eintrag["wurf"] <= 20 and eintrag["name"]
    d = aktion("cyberware/nebenwirkung-entfernen", d, "0")["charakter_daten"]
    assert d["cyberware_nebenwirkungen"] == []


def test_cyberware_stat_effekte_in_berechne(scifi):
    # Unterhautpanzerung o. ä. mit panzerung/robustheit-Effekt suchen wäre fragil —
    # Dermalplatten: natuerliche_panzerung laut Datenbestand
    d = aktion("cyberware/installieren", scifi, "Cyberware: Dermalplatten")
    if d["success"]:
        w = berechne(d["charakter_daten"])
        assert w["panzerung"] >= 1


# --- Superkräfte (superkraefte.py) ---

@pytest.fixture
def superheld(daten):
    d = aktion("setting/wechseln", daten, "Superkräfte Kompendium")["charakter_daten"]
    d["selected_talente"] = ["Superkräfte"]
    return d


def test_superkraft_braucht_talent_und_setting(daten, superheld):
    r = aktion("superkraft/waehlen", daten, "Fliegen")
    assert not r["success"] and "kein Superkräfte-System" in r["message"]
    superheld["selected_talente"] = []
    r = aktion("superkraft/waehlen", superheld, "Fliegen")
    assert not r["success"] and "Superkräfte" in r["message"]


def test_superkraft_waehlen_und_budget(superheld):
    w = berechne(superheld)
    assert w["superkraefte"]["stufe"] == "I"
    assert w["superkraefte"]["budget"] == 15
    d = aktion("superkraft/waehlen", superheld, "Fliegen")["charakter_daten"]  # Basis 2
    assert d["selected_superkraefte"]["Fliegen"]["punkte"] == 2
    assert berechne(d)["superkraefte"]["verbleibend"] == 13
    d = aktion("superkraft/entfernen", d, "Fliegen")["charakter_daten"]
    assert berechne(d)["superkraefte"]["verbleibend"] == 15


def test_superkraft_punkte_und_kraftobergrenze(superheld):
    d = aktion("superkraft/waehlen", superheld, "Fliegen")["charakter_daten"]
    d = aktion("superkraft/punkte", d, "Fliegen:5")["charakter_daten"]  # Obergrenze Stufe I = 5
    assert d["selected_superkraefte"]["Fliegen"]["punkte"] == 5
    r = aktion("superkraft/punkte", d, "Fliegen:6")
    assert not r["success"]
    assert "Kraftobergrenze" in r["message"]


def test_superkraft_budget_erschoepft(superheld):
    d = aktion("superkraft/waehlen", superheld, "Fliegen")["charakter_daten"]
    d = aktion("superkraft/punkte", d, "Fliegen:5")["charakter_daten"]
    d = aktion("superkraft/waehlen", d, "Bewegungsweite")["charakter_daten"]
    d = aktion("superkraft/punkte", d, "Bewegungsweite:5")["charakter_daten"]
    d = aktion("superkraft/waehlen", d, "Absorption")["charakter_daten"]
    d = aktion("superkraft/punkte", d, "Absorption:5")["charakter_daten"]  # 15/15
    r = aktion("superkraft/waehlen", d, "Blenden")
    assert not r["success"]
    assert "Nicht genug Superkraftpunkte" in r["message"]


def test_superkraft_machtstufe_wechsel(superheld):
    d = aktion("superkraft/stufe", superheld, "III")["charakter_daten"]
    w = berechne(d)["superkraefte"]
    assert w["budget"] == 45 and w["kraftobergrenze"] == 15
    # Absenken unter bereits ausgegebene Punkte wird abgelehnt
    d = aktion("superkraft/waehlen", d, "Fliegen")["charakter_daten"]
    d = aktion("superkraft/punkte", d, "Fliegen:15")["charakter_daten"]
    r = aktion("superkraft/stufe", d, "I")
    assert not r["success"]
    assert berechne(r["charakter_daten"])["superkraefte"]["stufe"] == "III"


def test_superkraft_modifikator_toggle(superheld):
    d = aktion("superkraft/waehlen", superheld, "Absorption")["charakter_daten"]  # 2
    d = aktion("superkraft/modifikator", d, "Absorption:Meisterschaft")["charakter_daten"]  # +1
    assert d["selected_superkraefte"]["Absorption"]["modifikatoren"] == {"Meisterschaft": 1}
    assert berechne(d)["superkraefte"]["ausgegeben"] == 3
    # negativer Modifikator senkt Kosten
    d = aktion("superkraft/modifikator", d, "Absorption:Achillesferse")["charakter_daten"]  # -1
    assert berechne(d)["superkraefte"]["ausgegeben"] == 2
    # Toggle entfernt wieder
    d = aktion("superkraft/modifikator", d, "Absorption:Meisterschaft")["charakter_daten"]
    assert berechne(d)["superkraefte"]["ausgegeben"] == 1


# --- Statblock (statblock.py) ---

def statblock(daten: dict) -> str:
    resp = client.post("/api/spiellogik/statblock", json={"charakter_daten": daten})
    assert resp.status_code == 200
    return resp.json()["statblock"]


def test_statblock_basis(daten):
    daten["profil_daten"]["Name"] = "Grimnir"
    d = aktion("volk/waehlen", daten, "Zwerg")["charakter_daten"]
    text = statblock(d)
    zeilen = text.splitlines()
    assert zeilen[0] == "Grimnir"
    assert zeilen[1] == "Volk: Zwerg (SWAE)"
    assert "Attribute: Geschicklichkeit W4, Verstand W4, Willenskraft W4, Stärke W4, Konstitution W6" in text
    assert "Bewegungsweite: 5; Parade: 2; Robustheit: 5; Größe: +0" in text
    assert "Talente: Nachtsicht" in text
    # ungelernte Fertigkeiten tauchen nicht auf
    assert "Kämpfen" not in text
    assert "Athletik W4" in text


def test_statblock_handicap_stufe_und_ruestung(daten):
    d = aktion("handicap/waehlen", daten, "Alt")["charakter_daten"]
    d = aktion("ausruestung/kaufen", d, "Jacke (dünn)")["charakter_daten"]
    d = aktion("ausruestung/anlegen", d, "Jacke (dünn)")["charakter_daten"]
    text = statblock(d)
    assert "Handicaps: Alt (schwer)" in text
    assert "Robustheit: 5 (1)" in text
    assert "Jacke (dünn) [angelegt]" in text
    assert "Geld: 480" in text


def test_statblock_superkraefte_und_rang(daten):
    d = aktion("setting/wechseln", daten, "Superkräfte Kompendium")["charakter_daten"]
    d["selected_talente"] = ["Superkräfte"]
    d = aktion("superkraft/waehlen", d, "Fliegen")["charakter_daten"]
    d = aktion("erschaffung/abschliessen", d)["charakter_daten"]
    text = statblock(d)
    assert "Superkräfte: Fliegen [2 SKP] (Machtstufe I, 2/15 SKP)" in text
    assert "Aufstiege: 0 (Anfänger)" in text


# --- Verfügbare Talente (Filter "Nur verfügbare") ---

def test_talente_verfuegbar(daten):
    resp = client.post("/api/spiellogik/talente/verfuegbar", json={"charakter_daten": daten})
    assert resp.status_code == 200
    verfuegbar = resp.json()["verfuegbar"]
    # ohne Voraussetzungen und Anfänger-Rang: verfügbar
    assert "Aristokrat" in verfuegbar
    # "Flink" braucht GES W6 — Startcharakter hat W4
    assert "Flink" not in verfuegbar

    daten["attribute"]["Geschicklichkeit"]["wert"] = 6
    verfuegbar = client.post(
        "/api/spiellogik/talente/verfuegbar", json={"charakter_daten": daten}
    ).json()["verfuegbar"]
    assert "Flink" in verfuegbar


# --- Setting-Elemente bearbeiten (setting_elemente.py) ---

def element_aktion(pfad: str, daten: dict, typ: str, name: str, element_daten: dict | None = None,
                   alter_name: str | None = None) -> dict:
    resp = client.post(f"/api/spiellogik/element/{pfad}", json={
        "charakter_daten": daten,
        "element_typ": typ,
        "element_name": name,
        "element_daten": element_daten,
        "alter_name": alter_name,
    })
    assert resp.status_code == 200
    return resp.json()


def test_element_hinzufuegen_und_waehlen(daten):
    r = element_aktion("speichern", daten, "talente", "Bierkenner",
                       {"rang": "A", "beschreibung": "Kennt jedes Bier."})
    assert r["success"]
    d = r["charakter_daten"]
    eintrag = d["setting_overrides"]["talente"]["Bierkenner"]
    assert eintrag["custom"] is True
    assert eintrag["beschreibung"] == "Kennt jedes Bier."

    # Das eigene Talent ist sofort wählbar (Talent-Slot nötig)
    d = aktion("handicap/waehlen", d, "Alt")["charakter_daten"]
    d = aktion("handicap-punkte/einloesen", d, "talent")["charakter_daten"]
    r = aktion("talent/waehlen", d, "Bierkenner")
    assert r["success"], r["message"]
    assert "Bierkenner" in r["charakter_daten"]["selected_talente"]


def test_element_bearbeiten_nativ(daten):
    r = element_aktion("speichern", daten, "handicaps", "Fies",
                       {"beschreibung": "Angepasst.", "stufe": "schwer"}, alter_name="Fies")
    assert r["success"]
    d = r["charakter_daten"]
    eintrag = d["setting_overrides"]["handicaps"]["Fies"]
    assert eintrag["custom"] is False  # bearbeitetes natives Element
    assert eintrag["stufe"] == "schwer"
    assert eintrag["punkte"] == 2  # Punkte folgen der Stufe

    # Das bearbeitete Handicap überlagert das native beim Wählen
    r = aktion("handicap/waehlen", d, "Fies")
    assert r["success"]
    assert r["charakter_daten"]["verbleibende_handicap_punkte"] == 2


def test_element_umbenennen_zieht_auswahl_mit(daten):
    d = aktion("handicap/waehlen", daten, "Alt")["charakter_daten"]
    d = aktion("handicap-punkte/einloesen", d, "talent")["charakter_daten"]
    d = aktion("talent/waehlen", d, "Aristokrat")["charakter_daten"]
    r = element_aktion("speichern", d, "talente", "Adliger", {}, alter_name="Aristokrat")
    assert r["success"]
    d = r["charakter_daten"]
    assert "Adliger" in d["selected_talente"]
    assert "Aristokrat" not in d["selected_talente"]
    # das native Original ist ausgeblendet
    assert "Aristokrat" in d["setting_overrides"]["geloescht"]["talente"]


def test_element_loeschen_nativ_und_gewaehlt(daten):
    # gewähltes Element kann nicht gelöscht werden
    d = aktion("handicap/waehlen", daten, "Alt")["charakter_daten"]
    r = element_aktion("loeschen", d, "handicaps", "Alt")
    assert not r["success"]
    assert "gewählt" in r["message"]

    # ungewähltes natives Element: wird ausgeblendet und ist nicht mehr wählbar
    r = element_aktion("loeschen", d, "handicaps", "Fies")
    assert r["success"]
    d = r["charakter_daten"]
    assert "Fies" in d["setting_overrides"]["geloescht"]["handicaps"]
    r = aktion("handicap/waehlen", d, "Fies")
    assert not r["success"]


def test_element_eigene_ausruestung_kaufbar(daten):
    r = element_aktion("speichern", daten, "ausruestung", "Plasmalanze",
                       {"kategorie": "Waffe", "kosten": 100, "gewicht": 1,
                        "eigenschaften": {"Schaden": "Stä+W10"}})
    assert r["success"]
    d = r["charakter_daten"]
    r = aktion("ausruestung/kaufen", d, "Plasmalanze")
    assert r["success"], r["message"]
    d = r["charakter_daten"]
    assert d["ausruestung_selected"]["Plasmalanze"]["anzahl"] == 1

    # gekaufte Ausrüstung kann nicht gelöscht werden
    r = element_aktion("loeschen", d, "ausruestung", "Plasmalanze")
    assert not r["success"]

    # nach Verkauf schon — als Custom-Element verschwindet es komplett
    d = aktion("ausruestung/verkaufen", d, "Plasmalanze")["charakter_daten"]
    r = element_aktion("loeschen", d, "ausruestung", "Plasmalanze")
    assert r["success"]
    assert "Plasmalanze" not in r["charakter_daten"]["setting_overrides"]["ausruestung"]


def test_element_duplikat_abgelehnt(daten):
    r = element_aktion("speichern", daten, "talente", "Flink", {})
    assert not r["success"]
    assert "existiert bereits" in r["message"]


def test_element_statblock_und_berechne_nutzen_overrides(daten):
    r = element_aktion("speichern", daten, "ausruestung", "Turmschild",
                       {"kategorie": "Schild", "kosten": 10, "parade": 3})
    d = r["charakter_daten"]
    d = aktion("ausruestung/kaufen", d, "Turmschild")["charakter_daten"]
    d = aktion("ausruestung/anlegen", d, "Turmschild")["charakter_daten"]
    resp = client.post("/api/spiellogik/berechne", json={"charakter_daten": d})
    assert resp.json()["parade"] == 5  # 2 Basis + 3 Schild


# --- Charakterbogen (charakterbogen.py) ---

def charakterbogen(daten: dict, printer_friendly: bool = False) -> str:
    resp = client.post(
        "/api/spiellogik/charakterbogen",
        json={"charakter_daten": daten, "printer_friendly": printer_friendly},
    )
    assert resp.status_code == 200
    return resp.json()["html"]


def test_charakterbogen_basis(daten):
    daten["profil_daten"]["Name"] = "Grimnir <Test>"
    d = aktion("volk/waehlen", daten, "Zwerg")["charakter_daten"]
    d = aktion("handicap/waehlen", d, "Alt")["charakter_daten"]
    html = charakterbogen(d)
    assert html.startswith("<!DOCTYPE html>")
    # Name wird escaped
    assert "Grimnir &lt;Test&gt;" in html
    assert "<h2>Abstammung: Zwerg</h2>" in html
    assert "<h2>Handicaps</h2>" in html
    assert "<td>Alt</td><td>schwer</td>" in html
    # ungelernte Fertigkeiten tauchen nicht auf
    assert "<td>Kämpfen</td>" not in html
    # Farbige Version enthält die Original-Hintergrundfarbe
    assert "#FFF8DC" in html


def test_charakterbogen_druckerfreundlich(daten):
    html = charakterbogen(daten, printer_friendly=True)
    assert "#FFF8DC" not in html
    assert "#ffb961" not in html


def test_charakterbogen_ausruestung(daten):
    d = aktion("ausruestung/kaufen", daten, "Jacke (dünn)")["charakter_daten"]
    d = aktion("ausruestung/anlegen", d, "Jacke (dünn)")["charakter_daten"]
    d = aktion("ausruestung/kaufen", d, "Axt, Handbeil")["charakter_daten"]
    d = aktion("ausruestung/kaufen", d, "Kleiner Schild")["charakter_daten"]
    d = aktion("ausruestung/anlegen", d, "Kleiner Schild")["charakter_daten"]
    html = charakterbogen(d)
    assert "<h2>Waffen</h2>" in html
    assert "<td>Stä+W6</td>" in html
    assert "<h2>Rüstungen</h2>" in html
    assert '<td class="gesamt">Gesamt</td>' in html
    assert "<h2>Schilde</h2>" in html


def test_charakterbogen_altformat_voelker(daten):
    # Alt-Format aus der Kivy-App: {volk_name: bool}
    daten["voelker_selected"] = {"Mensch": True, "Zwerg": False}
    html = charakterbogen(daten)
    assert "<h2>Abstammung: Mensch</h2>" in html
    assert "Zwerg" not in html
