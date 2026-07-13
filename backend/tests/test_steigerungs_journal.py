"""Steigerungs-Journal: Einträge nach der Erschaffung und die Sektion
"Steigerungen" im Charakterbogen (Original: historie_view.py / html_utils.py)."""

import pytest
from fastapi.testclient import TestClient

from main import app
from app.services.charakter_init import initialisiere_charakter_daten

client = TestClient(app)


@pytest.fixture
def daten():
    return initialisiere_charakter_daten("Testheld", "SWAE")


def aktion(pfad: str, daten: dict, element: str | None = None, **extra) -> dict:
    resp = client.post(
        f"/api/spiellogik/{pfad}",
        json={"charakter_daten": daten, "element_name": element, **extra},
    )
    assert resp.status_code == 200
    return resp.json()


def mit_aufstieg(daten: dict, anzahl: int = 1) -> dict:
    d = aktion("erschaffung/abschliessen", daten)["charakter_daten"]
    for _ in range(anzahl):
        d = aktion("aufstieg/hinzufuegen", d)["charakter_daten"]
    return d


def entries(d: dict) -> list:
    return d.get("steigerungs_journal", {}).get("entries", [])


# --- Einträge schreiben und zurücknehmen ---

def test_erschaffung_schreibt_kein_journal(daten):
    d = aktion("attribut/steigern", daten, "Stärke")["charakter_daten"]
    d = aktion("fertigkeit/steigern", d, "Kämpfen")["charakter_daten"]
    assert "steigerungs_journal" not in d


def test_attribut_steigerung_wird_geloggt_und_beim_senken_entfernt(daten):
    d = mit_aufstieg(daten)
    d = aktion("attribut/steigern", d, "Stärke")["charakter_daten"]
    eintrag = entries(d)[0]
    assert eintrag["type"] == "attribut_steigerung"
    assert eintrag["rang"] == "Anfänger"
    assert eintrag["details"] == {
        "name": "Stärke",
        "von": "4",
        "nach": "6",
        "kosten": 1,
        "kosten_typ": "Aufstieg",
    }

    d = aktion("attribut/senken", d, "Stärke")["charakter_daten"]
    assert entries(d) == []


def test_fertigkeit_steigerung_loggt_halben_aufstieg(daten):
    d = mit_aufstieg(daten)
    d = aktion("fertigkeit/steigern", d, "Kämpfen")["charakter_daten"]  # ungelernt -> W4
    eintrag = entries(d)[0]
    assert eintrag["type"] == "fertigkeit_steigerung"
    assert eintrag["details"]["von"] == "4-2"
    assert eintrag["details"]["nach"] == "4"
    assert eintrag["details"]["kosten"] == 0.5

    d = aktion("fertigkeit/senken", d, "Kämpfen")["charakter_daten"]
    assert entries(d) == []


def test_senken_entfernt_den_letzten_eintrag_der_fertigkeit(daten):
    d = mit_aufstieg(daten, anzahl=2)
    d = aktion("fertigkeit/steigern", d, "Kämpfen")["charakter_daten"]  # -> W4
    d = aktion("fertigkeit/steigern", d, "Kämpfen", ignoriere_pruefungen=True)["charakter_daten"]  # -> W6
    d = aktion("fertigkeit/steigern", d, "Reiten")["charakter_daten"]
    assert len(entries(d)) == 3

    d = aktion("fertigkeit/senken", d, "Kämpfen")["charakter_daten"]
    verbleibend = entries(d)
    assert len(verbleibend) == 2
    assert [e["details"]["nach"] for e in verbleibend] == ["4", "4"]
    assert {e["details"]["name"] for e in verbleibend} == {"Kämpfen", "Reiten"}


def test_talent_per_aufstieg_wird_geloggt_und_beim_entfernen_zurueckgenommen(daten):
    d = mit_aufstieg(daten)
    d = aktion("talent/waehlen", d, "Aristokrat")["charakter_daten"]
    eintrag = entries(d)[0]
    assert eintrag["type"] == "talent_hinzugefuegt"
    assert eintrag["details"] == {"name": "Aristokrat", "kosten": 1, "kosten_typ": "Aufstieg"}

    d = aktion("talent/entfernen", d, "Aristokrat")["charakter_daten"]
    assert entries(d) == []


def test_handicap_abkaufen_und_reduzieren_werden_geloggt(daten):
    d = aktion("handicap/waehlen", daten, "Arm")["charakter_daten"]  # leicht
    d = aktion("handicap/waehlen", d, "Langsam_schwer")["charakter_daten"]
    d = mit_aufstieg(d, anzahl=2)

    d = aktion("handicap/entfernen", d, "Arm")["charakter_daten"]
    d = aktion("handicap/reduzieren", d, "Langsam_schwer")["charakter_daten"]
    typen = [e["type"] for e in entries(d)]
    assert typen == ["handicap_entfernt", "handicap_reduziert"]
    assert all(e["details"]["kosten_typ"] == "Aufstieg" for e in entries(d))


def test_rang_im_eintrag_ist_der_nach_der_buchung_erreichte(daten):
    d = mit_aufstieg(daten, anzahl=4)
    for _ in range(4):
        d = aktion("attribut/steigern", d, "Stärke")["charakter_daten"]
    assert [e["rang"] for e in entries(d)] == [
        "Anfänger", "Anfänger", "Anfänger", "Fortgeschritten",
    ]


# --- Charakterbogen-Sektion ---

def bogen_html(d: dict) -> str:
    resp = client.post("/api/spiellogik/charakterbogen", json={"charakter_daten": d})
    assert resp.status_code == 200
    return resp.json()["html"]


def test_bogen_ohne_journal_ohne_sektion(daten):
    assert "<h2>Steigerungen</h2>" not in bogen_html(daten)


def test_bogen_zeigt_journal_entries(daten):
    d = mit_aufstieg(daten)
    d = aktion("attribut/steigern", d, "Stärke")["charakter_daten"]
    html = bogen_html(d)
    assert "<h2>Steigerungen</h2>" in html
    assert "Stärke: W4 → W6" in html
    assert "1 Aufstieg" in html


def test_bogen_faellt_auf_cost_entries_zurueck(daten):
    # Kivy-Import/Archetyp: nur das Erschaffungs-Kauf-Journal ist vorhanden
    daten["steigerungs_journal"] = {
        "cost_entries": [
            {"typ": "attribut", "name": "Geschicklichkeit", "wert": 6,
             "zahlungsquelle": "Attributspunkte", "kosten": 1},
            {"typ": "talent", "name": "Schnell",
             "zahlungsquelle": "Handicap-Punkte", "kosten": 2},
        ]
    }
    html = bogen_html(daten)
    assert "<h2>Steigerungen</h2>" in html
    assert "Geschicklichkeit: W6" in html
    assert "1 Attributspunkte" in html
    assert "2 Handicap-Punkte" in html
