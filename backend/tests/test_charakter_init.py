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


# --- Migration von Kivy-Alt-Exporten ---

def test_migration_volk_bool_map():
    alt = {
        "active_setting_name": "SWAE",
        "voelker_selected": {"Elfen": False, "Menschen": True, "Zwerge": False},
    }
    neu, geaendert = ergaenze_fehlende_eigenschaften(alt)
    assert geaendert
    assert list(neu["voelker_selected"].keys()) == ["Menschen"]
    volk_data = neu["voelker_selected"]["Menschen"]
    assert isinstance(volk_data, dict)


def test_migration_volk_ohne_auswahl():
    alt = {"active_setting_name": "SWAE", "voelker_selected": {"Elfen": False}}
    neu, geaendert = ergaenze_fehlende_eigenschaften(alt)
    assert geaendert
    assert neu["voelker_selected"] == {}


def test_migration_talent_kopien_aus_kivy_keys():
    # Die Kivy-App legt Mehrfachauswahl als eigene Keys "Name_2" an; das Web
    # führt den Basisnamen mehrfach in selected_talente
    alt = {
        "active_setting_name": "SWAE",
        "voelker_selected": {"Menschen": True},
        "selected_talente": ["AH (Magie)", "Neue Mächte", "Neue Mächte_2", "HeXXe_3"],
    }
    neu, geaendert = ergaenze_fehlende_eigenschaften(alt)
    assert geaendert
    # "HeXXe_3" bleibt: kein passendes Basis-Talent im Setting
    assert neu["selected_talente"] == ["AH (Magie)", "Neue Mächte", "Neue Mächte", "HeXXe_3"]


def test_migration_ausruestung_aus_selected_elements():
    alt = {
        "active_setting_name": "SWAE",
        "selected_elements": {
            "ausruestung": {
                "Axt, Handbeil": {"ausgewaehlt": True, "anzahl": 1, "zustand": "neu"},
                "Fackel": {"ausgewaehlt": True, "anzahl": 3, "zustand": "neu"},
                "Jacke (dünn)": {"ausgewaehlt": True, "anzahl": 1, "zustand": "neu"},
            }
        },
        "selected_waffen": ["Axt, Handbeil"],
        "selected_ruestungen": ["Jacke (dünn)"],
        "vermoegen": 250,
    }
    neu, geaendert = ergaenze_fehlende_eigenschaften(alt)
    assert geaendert
    ausr = neu["ausruestung_selected"]
    assert ausr["Fackel"] == {"anzahl": 3, "angelegt": False}
    assert ausr["Axt, Handbeil"] == {"anzahl": 1, "angelegt": False}
    # Rüstungen aus selected_ruestungen gelten als angelegt
    assert ausr["Jacke (dünn)"] == {"anzahl": 1, "angelegt": True}
    # SWAE-Startkapital 500, Rest-Vermögen 250 -> 250 ausgegeben
    assert neu["ausruestung_ausgegeben"] == 250


def test_migration_ausruestung_aus_mengen_ohne_vermoegen():
    alt = {
        "active_setting_name": "SWAE",
        "ausruestung_mengen": {"Fackel": 2},
        "selected_allgemeine_ausruestung": ["Fackel"],
    }
    neu, geaendert = ergaenze_fehlende_eigenschaften(alt)
    assert geaendert
    assert neu["ausruestung_selected"]["Fackel"] == {"anzahl": 2, "angelegt": False}
    # Ohne Rest-Vermögen: Ausgaben aus den Katalogkosten (Fackel je 5)
    assert neu["ausruestung_ausgegeben"] == 10


def test_migration_volk_wahl_halbelf_attribut():
    alt = {
        "active_setting_name": "SWAE",
        "voelker_selected": {"Halbelf": True, "Mensch": False},
        "voelker_auswahlen": {"Halbelf": {"halbelf_wahl": "Geschicklichkeit W6"}},
        "attribute": {"Geschicklichkeit": {"wert": 6, "modifier": 0}},
        "selected_talente": ["Nachtsicht"],
    }
    neu, geaendert = ergaenze_fehlende_eigenschaften(alt)
    assert geaendert
    ve = neu["volk_effekte"]
    assert ve["wahl"] == {"typ": "attribut", "ziel": "Geschicklichkeit", "feld": "wert"}
    # Auto-Talent des Volkes wird als Volks-Talent registriert
    assert ve["talente"] == ["Nachtsicht"]


def test_migration_volk_wahl_mensch_talent():
    alt = {
        "active_setting_name": "SWAE",
        "voelker_selected": {"Mensch": True},
        "voelker_auswahlen": {"Mensch": {"vielseitig_wahl": "Talent: Flink"}},
    }
    neu, _ = ergaenze_fehlende_eigenschaften(alt)
    assert neu["volk_effekte"]["wahl"] == {"typ": "talent"}


def test_migration_mensch_fertigkeitspunkte_wahl():
    alt = {
        "active_setting_name": "SWAE",
        "voelker_selected": {"Mensch": True},
        "voelker_auswahlen": {"Mensch": {"vielseitig_wahl": "+2 Fertigkeitspunkte"}},
    }
    neu, _ = ergaenze_fehlende_eigenschaften(alt)
    assert neu["volk_effekte"]["wahl"] == {"typ": "fertigkeitspunkte"}


def test_migration_mensch_ohne_wahl_bekommt_keine_vorauswahl():
    # In der Kivy-App gab es den Vorteil nur über die explizite Wahl —
    # ohne Eintrag bleibt die Wahl im Völker-Tab offen
    alt = {"active_setting_name": "SWAE", "voelker_selected": {"Mensch": True}}
    neu, _ = ergaenze_fehlende_eigenschaften(alt)
    assert "wahl" not in neu["volk_effekte"]


def test_migration_pathfinder_mensch_talent_und_attribut():
    # Savage Pathfinder Mensch: gewähltes Talent ist ein fester Slot,
    # das gewählte Attribut die Kern-Wahl
    alt = {
        "active_setting_name": "Savage Pathfinder",
        "voelker_selected": {"Mensch": True},
        "voelker_auswahlen": {"Mensch": {"talent": ["Flink"], "attribut": ["Stärke"]}},
    }
    neu, _ = ergaenze_fehlende_eigenschaften(alt)
    ve = neu["volk_effekte"]
    assert ve["talent_slots"] == 1
    assert ve["wahl"] == {"typ": "attribut", "ziel": "Stärke", "feld": "wert"}


def test_migration_spezialwahlen():
    alt = {
        "active_setting_name": "SWAE",
        "voelker_selected": {"Androiden": True},
        "voelker_auswahlen": {"Androiden": {"fertigkeit": ["Kämpfen"], "attribut_malus": "Verstand"}},
        "attribute": {"Verstand": {"wert": 4, "modifier": -2}},
        "fertigkeiten": {"Kämpfen": {"wuerfel": {"value": 6, "modifier": 0}}},
    }
    neu, _ = ergaenze_fehlende_eigenschaften(alt)
    wahlen = neu["volk_effekte"]["wahlen"]
    # Androiden bieten "spezialisierung" als Fertigkeits-Wahl
    assert wahlen["spezialisierung"] == {
        "typ": "fertigkeit", "ziel": "Kämpfen", "war_untrainiert": True, "delta": 2,
    }
    assert wahlen["attribut_schwaeche"]["ziel"] == "Verstand"


def test_migration_wahl_wechsel_rechnet_korrekt_zurueck():
    """Nach der Migration muss ein Wechsel der Kern-Wahl die alte Wahl exakt
    zurücknehmen (kein Doppel-Bonus aus den gebackenen Kivy-Werten)."""
    from app.services.volk_effekte import wende_volk_wahl_an

    alt = {
        "active_setting_name": "SWAE",
        "voelker_selected": {"Halbelf": True},
        "voelker_auswahlen": {"Halbelf": {"halbelf_wahl": "Geschicklichkeit W6"}},
    }
    neu, _ = ergaenze_fehlende_eigenschaften(alt)
    neu["attribute"]["Geschicklichkeit"]["wert"] = 6  # aus Kivy gebacken

    ok, meldung = wende_volk_wahl_an(neu, "Stärke")
    assert ok, meldung
    assert neu["attribute"]["Geschicklichkeit"]["wert"] == 4
    assert neu["attribute"]["Stärke"]["wert"] == 6


def test_migration_laesst_web_format_unangetastet():
    daten = initialisiere_charakter_daten("Web", "SWAE")
    daten["voelker_selected"] = {"Zwerg": {"name": "Zwerg", "effects": {}}}
    daten["ausruestung_selected"] = {"Fackel": {"anzahl": 1, "angelegt": False}}
    neu, geaendert = ergaenze_fehlende_eigenschaften(daten)
    assert not geaendert
    assert neu == daten


def test_migration_superkraefte_liste_zu_dict():
    """Kivy-Superkräfte-Archetypen führen selected_superkraefte als reine
    Namensliste und halten Punkte/Modifikatoren unter
    selected_elements.superkraefte. Ohne Migration bricht /berechne ab und der
    Superkräfte-Tab fehlt in der Kopie — die Auswahl muss ins Web-Format
    {name: {punkte, modifikatoren}} überführt (mit den echten gewählten Punkten
    und Modifikatoren) und die Machtstufe aus dem Gesamtbudget abgeleitet werden.
    """
    alt = {
        "active_setting_name": "Superkräfte Kompendium",
        "char_gen_completed": False,
        "profil_daten": {"Name": "Held"},
        "selected_talente": ["Superkräfte"],
        "selected_superkraefte": ["Ausweichen", "Nahkampfangriff", "Schieben"],
        "selected_elements": {
            "superkraefte": {
                "Ausweichen": {"ausgewaehlt": True, "gewaehlte_kosten": 2,
                               "gewaehlte_modifikatoren": []},
                "Nahkampfangriff": {"ausgewaehlt": True, "gewaehlte_kosten": 6,
                                    "gewaehlte_modifikatoren": [
                                        {"name": "Tödlich", "kosten": 2}]},
                "Schieben": {"ausgewaehlt": True, "gewaehlte_kosten": 4,
                             "gewaehlte_modifikatoren": []},
            }
        },
        "superkraft_punkte_gesamt": 45,
        "superkraft_punkte_verbraucht": 14,
    }
    neu, geaendert = ergaenze_fehlende_eigenschaften(alt)
    assert geaendert
    sk = neu["selected_superkraefte"]
    assert isinstance(sk, dict)
    assert sk["Ausweichen"] == {"punkte": 2, "modifikatoren": {}}
    # Basis-SKP bleiben getrennt von der Modifikator-Kosten
    assert sk["Nahkampfangriff"] == {"punkte": 6, "modifikatoren": {"Tödlich": 2}}
    assert sk["Schieben"] == {"punkte": 4, "modifikatoren": {}}
    # 45 SKP -> Machtstufe III
    assert neu["superkraft_stufe"] == "III"

    # Gesamtkosten (Basis + Modifikatoren) rekonstruieren superkraft_punkte_verbraucht
    from app.services import superkraefte

    assert superkraefte.skp_ausgegeben(neu) == 14


def test_entpacke_charakter_export():
    from app.services.charakter_init import entpacke_charakter_export

    nackt = initialisiere_charakter_daten("Testheld", "SWAE")
    # nackte charakter_daten bleiben unverändert
    assert entpacke_charakter_export(nackt) is nackt

    # Voll-Export (DB-Zeile) wird auf die inneren charakter_daten ausgepackt
    wrapper = {
        "id": 7,
        "char_name": "Mrs. Winchester",
        "active_setting_name": "Deadlands",
        "char_gen_completed": 1,
        "charakter_daten": nackt,
        "benutzername": "JezzB",
        "email": "test@test.de",
    }
    assert entpacke_charakter_export(wrapper) is nackt


def _kivy_cyberware_export(vermoegen=3000.0, talente=None):
    """Kivy-Export mit gekaufter Cyberware: Installationen unter
    selected_elements.cyberware, Implantate zusätzlich in der Ausrüstungsliste,
    Kaufkosten bereits vom Vermögen abgezogen."""
    return {
        "active_setting_name": "SciFi Kompendium",
        "char_gen_completed": False,
        "profil_daten": {"Name": "Cybertest"},
        "vermoegen": vermoegen,
        "selected_talente": talente or [],
        "selected_cyberware": ["Cyberware: Datenbuchse", "Cyberware: Ersatzgliedmaße"],
        "selected_elements": {
            "cyberware": {
                "uuid-1": {
                    "name": "Cyberware: Datenbuchse", "kosten": 5000, "stress": 1,
                    "installiert": True, "aktiv": True, "installations_id": "uuid-1",
                },
                "uuid-2": {
                    "name": "Cyberware: Ersatzgliedmaße", "kosten": 2000, "stress": 1,
                    "installiert": True, "aktiv": False, "installations_id": "uuid-2",
                },
            },
            "ausruestung": {
                "Cyberware: Datenbuchse": {"ausgewaehlt": True, "anzahl": 1},
                "Cyberware: Ersatzgliedmaße": {"ausgewaehlt": True, "anzahl": 1},
                "Rucksack": {"ausgewaehlt": True, "anzahl": 1},
            },
        },
        "voelker_selected": {"Mensch": True},
    }


def test_kivy_import_cyberware_installationen():
    daten, geaendert = ergaenze_fehlende_eigenschaften(_kivy_cyberware_export())
    assert geaendert
    assert daten["cyberware_installationen"] == {
        "Cyberware: Datenbuchse": 1,
        "Cyberware: Ersatzgliedmaße": 1,
    }
    assert daten["cyberware_inaktiv"] == ["Cyberware: Ersatzgliedmaße"]
    assert daten["cyberware_ausgegeben"] == 7000
    # Implantate nicht zusätzlich als normale Ausrüstung, Rest schon
    assert "Cyberware: Datenbuchse" not in daten["ausruestung_selected"]
    assert "Rucksack" in daten["ausruestung_selected"]


def test_kivy_import_cyberware_geld_bleibt_erhalten():
    from app.services.ausruestung import verfuegbares_geld
    from app.services.charakter_init import load_setting

    setting = load_setting("SciFi Kompendium")
    daten, _ = ergaenze_fehlende_eigenschaften(_kivy_cyberware_export(vermoegen=3000.0))
    verfuegbar, _ = verfuegbares_geld(daten, setting)
    assert verfuegbar == 3000.0

    # Mit Cyborg-Budget (deckt Cyberware-Kosten teilweise) muss das
    # verfügbare Geld trotzdem exakt dem Kivy-Vermögen entsprechen
    daten, _ = ergaenze_fehlende_eigenschaften(
        _kivy_cyberware_export(vermoegen=3000.0, talente=["Cyborg"])
    )
    verfuegbar, _ = verfuegbares_geld(daten, setting)
    assert verfuegbar == 3000.0


def test_kivy_import_cyberware_effekt_snapshots_rekonstruiert():
    """Effekte importierter Implantate stecken schon in den Werten — die
    rekonstruierten Snapshots müssen sie bei Deinstallation zurücknehmen."""
    export = _kivy_cyberware_export()
    export["selected_elements"]["cyberware"]["uuid-3"] = {
        "name": "Cyberware: Attributerhöhung", "kosten": 5000, "stress": 2,
        "installiert": True, "aktiv": True, "installations_id": "uuid-3",
        "effekte": {"attribut_erhoehung": True},
        "konfiguration": {"attribut": "Stärke"},
    }
    export["attribute"] = {
        "Stärke": {"attribut_name": "Stärke", "wert": 6, "modifier": 0},  # inkl. Implantat
        "Geschicklichkeit": {"attribut_name": "Geschicklichkeit", "wert": 4, "modifier": 0},
        "Konstitution": {"attribut_name": "Konstitution", "wert": 4, "modifier": 0},
        "Verstand": {"attribut_name": "Verstand", "wert": 4, "modifier": 0},
        "Willenskraft": {"attribut_name": "Willenskraft", "wert": 4, "modifier": 0},
    }
    daten, _ = ergaenze_fehlende_eigenschaften(export)
    snap = daten["cyberware_effekte"]["Cyberware: Attributerhöhung"][0]
    assert snap["attribut"] == "Stärke"
    assert snap["konfiguration"] == {"attribut": "Stärke"}

    from app.services.cyberware import deinstalliere
    from app.services.charakter_init import load_setting

    setting = load_setting("SciFi Kompendium")
    ok, _ = deinstalliere(daten, setting, "Cyberware: Attributerhöhung")
    assert ok
    assert daten["attribute"]["Stärke"]["wert"] == 4
