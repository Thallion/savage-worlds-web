import pytest

from app.config import settings as app_settings
from app.services import setting_verwaltung as sv
from app.services.charakter_init import initialisiere_charakter_daten, load_setting


@pytest.fixture(autouse=True)
def custom_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(app_settings, "custom_settings_path", tmp_path)
    return tmp_path


def test_liste_enthaelt_native_und_custom():
    sv.speichere_custom_setting("Meine Kampagne", sv.leeres_setting("Test"))
    liste = sv.liste_settings()
    namen = {s["name"]: s for s in liste}
    assert "SWAE" in namen and not namen["SWAE"]["custom"]
    assert namen["Meine Kampagne"]["custom"]
    assert namen["SWAE"]["statistik"]["talente"] == 141


def test_load_setting_findet_custom():
    setting = sv.leeres_setting()
    setting["talente"] = {"Eigenes Talent": {"rang": "A"}}
    sv.speichere_custom_setting("Homebrew", setting)
    geladen = load_setting("Homebrew")
    assert "Eigenes Talent" in geladen["talente"]
    # voelker_selected wird beim Speichern konsistent erzeugt
    assert geladen["voelker_selected"] == {}


def test_load_setting_blockt_pfad_ausbruch():
    with pytest.raises(FileNotFoundError):
        load_setting("../config/talent_config")


def test_namenspruefung():
    assert sv.pruefe_neuer_name("  Neu  ") == ("Neu", "")
    assert sv.pruefe_neuer_name("")[0] is None
    assert sv.pruefe_neuer_name("a/b")[0] is None
    assert sv.pruefe_neuer_name("SWAE")[0] is None  # nativ geschützt
    sv.speichere_custom_setting("Belegt", sv.leeres_setting())
    assert sv.pruefe_neuer_name("Belegt")[0] is None


def test_loeschen_nur_custom():
    sv.speichere_custom_setting("Wegwerf", sv.leeres_setting())
    ok, _ = sv.loesche_custom_setting("Wegwerf")
    assert ok and not sv.ist_custom_setting("Wegwerf")
    ok, fehler = sv.loesche_custom_setting("SWAE")
    assert not ok and "mitgeliefert" in fehler


def test_zusammenfuehrung_spaetere_quelle_gewinnt():
    a = sv.leeres_setting()
    a["talente"] = {"Attraktiv": {"rang": "A", "beschreibung": "alt"}, "Nur A": {"rang": "A"}}
    a["startgeld"] = 500
    b = sv.leeres_setting()
    b["talente"] = {"Attraktiv": {"rang": "A", "beschreibung": "neu"}, "Nur B": {"rang": "F"}}
    b["startgeld"] = 250
    sv.speichere_custom_setting("Quelle A", a)
    sv.speichere_custom_setting("Quelle B", b)

    ergebnis, konflikte = sv.fuehre_zusammen(["Quelle A", "Quelle B"])

    assert set(ergebnis["talente"]) == {"Attraktiv", "Nur A", "Nur B"}
    assert ergebnis["talente"]["Attraktiv"]["beschreibung"] == "neu"
    assert ergebnis["startgeld"] == 250
    typen = {(k["typ"], k["name"]) for k in konflikte}
    assert ("talente", "Attraktiv") in typen
    assert ("startgeld", "startgeld") in typen
    # gleiche Elemente ohne Abweichung erzeugen keinen Konflikt
    assert ("talente", "Nur A") not in typen


def test_zusammenfuehrung_native_settings_ist_spielbar():
    ergebnis, _ = sv.fuehre_zusammen(["SWAE", "Hellfrost"])
    assert len(ergebnis["voelker"]) > len(load_setting("SWAE")["voelker"])
    assert ergebnis["attribute"]
    assert ergebnis["fertigkeiten_daten"]
    sv.speichere_custom_setting("Merged", ergebnis)
    daten = initialisiere_charakter_daten("Held", "Merged")
    assert daten["attribute"] and daten["fertigkeiten"]


def test_aus_charakter_uebernimmt_overrides():
    daten = initialisiere_charakter_daten("Held", "SWAE")
    daten["setting_overrides"] = {
        "talente": {"Hausregel-Talent": {"rang": "A", "custom": True}},
        "geloescht": {"handicaps": ["Arm"]},
    }
    setting = sv.aus_charakter(daten)
    assert "Hausregel-Talent" in setting["talente"]
    assert "Arm" not in setting["handicaps"]
    assert "Arm" in load_setting("SWAE")["handicaps"]  # Original unangetastet


def test_elementauswahl():
    setting, konflikte, fehlend = sv.aus_elementauswahl(
        "SWAE",
        {
            "SWAE": {"voelker": ["Mensch"], "talente": ["Attraktiv"], "handicaps": ["Arm"]},
            "Hellfrost": {"talente": ["Attraktiv", "Gibt es nicht"]},
        },
    )
    assert set(setting["voelker"]) == {"Mensch"}
    assert set(setting["talente"]) == {"Attraktiv"}
    assert setting["attribute"] == load_setting("SWAE")["attribute"]
    # keine Fertigkeiten gewählt -> Basis-Fertigkeiten komplett übernommen
    assert setting["fertigkeiten_daten"] == load_setting("SWAE")["fertigkeiten_daten"]
    assert fehlend == ["Hellfrost: talente/Gibt es nicht"]
    # "Attraktiv" ist in beiden Quellen identisch -> kein Konflikt
    assert konflikte == []


def test_elementauswahl_krafte_kopiert_zusatztabellen():
    setting, _, _ = sv.aus_elementauswahl(
        "SWAE", {"Superkräfte Kompendium": {"krafte": ["Fliegen"]}}
    )
    assert "Fliegen" in setting["krafte"]
    assert setting.get("machtstufen")


def test_elemente_hinzufuegen_und_entfernen():
    sv.speichere_custom_setting("Bearbeitbar", sv.leeres_setting())
    setting, fehler, fehlend = sv.elemente_hinzufuegen(
        "Bearbeitbar", "SWAE", {"talente": ["Attraktiv"], "voelker": ["Mensch", "Fehlt"]}
    )
    assert not fehler
    assert "Attraktiv" in setting["talente"] and "Mensch" in setting["voelker"]
    assert fehlend == ["voelker/Fehlt"]
    # voelker_selected wächst mit
    assert load_setting("Bearbeitbar")["voelker_selected"] == {"Mensch": False}

    setting, fehler = sv.element_entfernen("Bearbeitbar", "talente", "Attraktiv")
    assert not fehler and "Attraktiv" not in setting["talente"]
    _, fehler = sv.element_entfernen("Bearbeitbar", "talente", "Attraktiv")
    assert "nicht" in fehler

    # native Settings sind nicht bearbeitbar
    ergebnis, fehler, _ = sv.elemente_hinzufuegen("SWAE", "SWAE", {"talente": ["Attraktiv"]})
    assert ergebnis is None and "mitgeliefert" in fehler


def test_element_setzen_neu_und_bearbeiten():
    sv.speichere_custom_setting("Editierbar", sv.leeres_setting())
    setting, fehler = sv.element_setzen(
        "Editierbar", "talente", "Hausregel", {"rang": "F", "voraussetzungen": "Attraktiv, Adel"}
    )
    assert not fehler
    talent = setting["talente"]["Hausregel"]
    assert talent["custom"] and talent["rang"] == "F"
    assert talent["voraussetzungen"] == ["Attraktiv", "Adel"]

    # Duplikat abgelehnt
    ergebnis, fehler = sv.element_setzen("Editierbar", "talente", "Hausregel", {})
    assert ergebnis is None and "existiert bereits" in fehler

    # Bearbeiten mit Umbenennung; nicht übergebene Felder bleiben erhalten
    setting, fehler = sv.element_setzen(
        "Editierbar", "talente", "Hausregel 2", {"rang": "V"}, alter_name="Hausregel"
    )
    assert not fehler and "Hausregel" not in setting["talente"]
    assert setting["talente"]["Hausregel 2"]["rang"] == "V"
    assert setting["talente"]["Hausregel 2"]["voraussetzungen"] == ["Attraktiv", "Adel"]
    assert load_setting("Editierbar")["talente"]["Hausregel 2"]["rang"] == "V"

    # übernommene native Elemente sind bearbeitbar und bleiben custom=False
    sv.elemente_hinzufuegen("Editierbar", "SWAE", {"talente": ["Attraktiv"]})
    setting, fehler = sv.element_setzen(
        "Editierbar", "talente", "Attraktiv", {"beschreibung": "Hausregel-Text"}, alter_name="Attraktiv"
    )
    assert not fehler
    assert setting["talente"]["Attraktiv"]["beschreibung"] == "Hausregel-Text"
    assert not setting["talente"]["Attraktiv"]["custom"]

    # Superkräfte: gemischte Kosten-Formate bleiben erhalten
    setting, fehler = sv.element_setzen(
        "Editierbar", "krafte", "Laserblick",
        {"kosten": "1/2", "modifikatoren": {"Gebündelt": {"kosten": "1", "beschreibung": "+2"}}},
    )
    assert not fehler
    assert setting["krafte"]["Laserblick"]["kosten"] == "1/2"
    assert setting["krafte"]["Laserblick"]["modifikatoren"]["Gebündelt"]["kosten"] == 1

    # native Settings und nicht editierbare Typen abgelehnt
    ergebnis, fehler = sv.element_setzen("SWAE", "talente", "X", {})
    assert ergebnis is None and "mitgeliefert" in fehler
    ergebnis, fehler = sv.element_setzen("Editierbar", "fertigkeiten_daten", "X", {})
    assert ergebnis is None and "Element-Typ" in fehler


def test_element_setzen_volk_aus_eigenarten():
    sv.speichere_custom_setting("Editierbar", sv.leeres_setting())
    setting, fehler = sv.element_setzen(
        "Editierbar",
        "voelker",
        "Waldgeist",
        {
            "beschreibung": "Test",
            "eigenarten": [{"id": "attributserhoehung", "auswahl": "Stärke"}],
        },
    )
    assert not fehler
    assert setting["voelker"]["Waldgeist"]["custom"]
    # voelker_selected wächst mit (speichere_custom_setting)
    assert load_setting("Editierbar")["voelker_selected"] == {"Waldgeist": False}

    # übernommene native Abstammungen ohne Eigenarten-Rohdaten sind nicht bearbeitbar
    sv.elemente_hinzufuegen("Editierbar", "SWAE", {"voelker": ["Mensch"]})
    ergebnis, fehler = sv.element_setzen(
        "Editierbar", "voelker", "Mensch", {"eigenarten": []}, alter_name="Mensch"
    )
    assert ergebnis is None and "Volkseigenarten" in fehler


def test_metadaten_und_umbenennen():
    sv.speichere_custom_setting("Alt", sv.leeres_setting("Erste Fassung"))
    setting, name, fehler = sv.aktualisiere_metadaten("Alt", "Neue Beschreibung", "Neu")
    assert not fehler and name == "Neu"
    assert setting["description"] == "Neue Beschreibung"
    assert not sv.ist_custom_setting("Alt") and sv.ist_custom_setting("Neu")

    # Umbenennen auf nativen Namen abgelehnt
    _, _, fehler = sv.aktualisiere_metadaten("Neu", None, "SWAE")
    assert "mitgeliefert" in fehler
