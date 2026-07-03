import pytest

from app.services.charakter_init import (
    ergaenze_fehlende_eigenschaften,
    initialisiere_charakter_daten,
)

GRUNDFERTIGKEITEN = {"Allgemeinwissen", "Athletik", "Heimlichkeit", "Überreden", "Wahrnehmung"}


def test_swae_initialisierung():
    daten = initialisiere_charakter_daten("Testheld", "SWAE")

    assert set(daten["attribute"].keys()) == {
        "Stärke", "Geschicklichkeit", "Konstitution", "Verstand", "Willenskraft"
    }
    for attr in daten["attribute"].values():
        assert attr["wert"] == 4
        assert attr["modifier"] == 0

    assert len(daten["fertigkeiten"]) == 32
    for name, fert in daten["fertigkeiten"].items():
        if name in GRUNDFERTIGKEITEN:
            assert fert["grundfertigkeit"] and fert["ausgewaehlt"]
            assert fert["wuerfel"] == {"value": 4, "modifier": 0, "typ": "fertigkeit"}
        else:
            assert not fert["grundfertigkeit"]
            assert fert["wuerfel"]["modifier"] == -2
        assert fert["attribut"] in daten["attribute"]

    assert daten["verbleibende_attributsteigerungen"] == 5
    assert daten["maximale_attributsteigerungen"] == 5
    assert daten["verbleibende_fertigkeitssteigerungen"] == 12
    assert daten["gesamt_handicap_punkte"] == 0
    assert daten["profil_daten"]["Name"] == "Testheld"


def test_setting_ohne_attribute_nutzt_standard():
    # 50 Fathoms hat keinen attribute-Key im Setting-JSON
    daten = initialisiere_charakter_daten("Pirat", "50 Fathoms")
    assert len(daten["attribute"]) == 5
    assert all(a["wert"] == 4 for a in daten["attribute"].values())


def test_unbekanntes_setting_wirft_fehler():
    with pytest.raises(FileNotFoundError):
        initialisiere_charakter_daten("X", "GibtEsNicht")


def test_lazy_init_fuellt_leere_dicts():
    alt = {
        "profil_daten": {"Name": "Altbestand"},
        "active_setting_name": "SWAE",
        "char_gen_completed": False,
        "attribute": {},
        "fertigkeiten": {},
        "selected_handicaps": ["Arm"],
        "selected_talente": [],
        "selected_maechte": [],
        "voelker_selected": {},
    }
    neu, geaendert = ergaenze_fehlende_eigenschaften(alt)
    assert geaendert
    assert len(neu["attribute"]) == 5
    assert len(neu["fertigkeiten"]) == 32
    assert neu["verbleibende_attributsteigerungen"] == 5
    # Bestehende Auswahl bleibt erhalten, Original unverändert
    assert neu["selected_handicaps"] == ["Arm"]
    assert alt["attribute"] == {}


def test_lazy_init_laesst_vollstaendige_daten_unangetastet():
    daten = initialisiere_charakter_daten("Voll", "SWAE")
    neu, geaendert = ergaenze_fehlende_eigenschaften(daten)
    assert not geaendert
    assert neu == daten
