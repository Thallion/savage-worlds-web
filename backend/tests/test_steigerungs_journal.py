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
    # Kivy-Import/Archetyp: nur das Kauf-Journal ist vorhanden.
    # Erschaffungs-Käufe zählen als "Start", mit Aufstiegen bezahlte bekommen
    # den Rang aus der laufenden Summe der ausgegebenen Aufstiege.
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
    assert "<td>Start</td>" in html
    assert "Geschicklichkeit: W6" in html
    assert "1 Attributspunkte" in html
    assert "2 Handicap-Punkte" in html


def test_bogen_cost_entries_rang_zum_zeitpunkt_der_steigerung(daten):
    daten["char_gen_completed"] = True
    daten["aufstiege_gesamt"] = 5
    daten["verbleibende_aufstiege"] = 0  # Charakter ist aktuell Fortgeschritten
    daten["steigerungs_journal"] = {
        "cost_entries": [
            {"typ": "fertigkeit", "name": "Kämpfen", "wert": 6,
             "zahlungsquelle": "Fertigkeitspunkte", "kosten": 1},
            {"typ": "attribut", "name": "Stärke", "wert": 6,
             "zahlungsquelle": "Aufstiege", "kosten": 1},  # 1. Aufstieg -> Anfänger
            {"typ": "attribut", "name": "Stärke", "wert": 8,
             "zahlungsquelle": "Aufstiege", "kosten": 1},  # 2. Aufstieg -> Anfänger
            {"typ": "fertigkeit", "name": "Kämpfen", "wert": 8,
             "zahlungsquelle": "Aufstiege", "kosten": 1},  # 3. Aufstieg -> Anfänger
            {"typ": "talent", "name": "Kampfreflexe",
             "zahlungsquelle": "Aufstiege", "kosten": 1},  # 4. Aufstieg -> Fortgeschritten
        ]
    }
    html = bogen_html(daten)
    import re

    raenge = re.findall(r"<tr><td>([^<]*)</td>", html.split("<h2>Steigerungen</h2>")[1])
    assert raenge == ["Start", "Anfänger", "Anfänger", "Anfänger", "Fortgeschritten"]


def test_abgekauftes_abstammungs_handicap_in_bogen_und_statblock(daten):
    d = aktion("volk/waehlen", daten, "Avionen")["charakter_daten"]  # Zerbrechlich (leicht)
    d = mit_aufstieg(d)
    d = aktion("handicap/entfernen", d, "Zerbrechlich")["charakter_daten"]
    assert entries(d)[-1]["details"]["volk"] is True

    assert "<s>Zerbrechlich (-1 Robustheit durch hohle Knochen)</s> — abgekauft" in bogen_html(d)
    resp = client.post("/api/spiellogik/statblock", json={"charakter_daten": d})
    statblock = resp.json()["statblock"]
    assert "Nichtschwimmer" in statblock
    assert "Zerbrechlich" not in statblock
    resp = client.post("/api/spiellogik/charakterbogen/pdf", json={"charakter_daten": d})
    assert resp.status_code == 200


def test_reduzierte_abstammungs_phobie_mit_eigenem_namen_im_bogen():
    # Zwerg (Savage Aventurien): Freitext "Meeresphobie (schwer: ...)" ↔ Phobie_schwer
    d = initialisiere_charakter_daten("Radrosch", "Savage Aventurien")
    d = aktion("volk/waehlen", d, "Zwerg")["charakter_daten"]
    d = mit_aufstieg(d)
    r = aktion("handicap/reduzieren", d, "Phobie_schwer")
    assert r["success"], r["message"]
    assert "Meeresphobie (schwer: panische Angst vor offenem und tiefem Wasser) — auf leicht reduziert" in bogen_html(
        r["charakter_daten"]
    )


@pytest.mark.parametrize(
    "name, eintrag, erwartet",
    [
        ("phobie", "Meeresphobie (schwer: panische Angst)", True),
        ("phobie", "Phobie (leicht: Geruchssinn)", True),
        ("schwäche (silber)", "Schwäche: Silber (+4 Schaden)", True),
        ("schwäche (pfahl)", "Schwäche: Sonnenlicht (2W6)", False),
        ("pazifist", "Pazifist_schwer", True),
        ("klaustrophobie", "Phobie (schwer)", False),
        ("stur", "Sturkopf", False),
    ],
)
def test_volk_handicap_passt(name, eintrag, erwartet):
    from app.services.volk_effekte import volk_handicap_passt

    assert volk_handicap_passt(name, eintrag) is erwartet


def test_jedes_abstammungs_handicap_hat_einen_freitext():
    # Sonst lässt sich ein Abkauf/eine Reduzierung im Volk-Block nicht markieren
    import json
    from pathlib import Path

    from app.services.volk_effekte import volk_handicap_passt

    fehlend = []
    for pfad in sorted(Path("gamelogic/settings").glob("*.json")):
        setting = json.loads(pfad.read_text(encoding="utf-8"))
        handicaps = setting.get("handicaps") or {}
        for volk_name, volk in (setting.get("voelker") or {}).items():
            for key in (volk.get("effects") or {}).get("auto_handicaps", []):
                name = (handicaps.get(key) or {}).get("name") or key.removesuffix("_leicht").removesuffix("_schwer")
                if not any(volk_handicap_passt(name, t) for t in volk.get("handicaps") or []):
                    fehlend.append(f"{pfad.stem}/{volk_name}: {key}")
    assert not fehlend


# --- Talent "Machtpunkte": einmal pro Rang, ab Legendär beliebig oft mit 2 MP ---

def _machtpunkte(d: dict) -> int:
    from app.services.charakter_init import load_setting
    from app.services.talent_voraussetzungen import macht_kapazitaet

    return macht_kapazitaet(d, load_setting("SWAE")["talente"])[1]


def _mit_ah(daten: dict) -> dict:
    daten["verbleibende_talente"] = 2
    return aktion("talent/waehlen", daten, "AH (Magie)")["charakter_daten"]


def test_machtpunkte_nur_einmal_pro_rang(daten):
    d = _mit_ah(daten)
    basis = _machtpunkte(d)
    d = aktion("talent/waehlen", d, "Machtpunkte")["charakter_daten"]
    assert _machtpunkte(d) == basis + 5

    zweite = aktion("talent/waehlen", d, "Machtpunkte")
    assert not zweite["success"]
    assert "einmal pro Rang" in zweite["message"]
    assert zweite["bestaetigung_moeglich"]

    # Nächster Rang: wieder wählbar
    d = mit_aufstieg(d, anzahl=5)
    d["verbleibende_aufstiege"] = 1  # 4 ausgegeben → Fortgeschritten
    d = aktion("talent/waehlen", d, "Machtpunkte")
    assert d["success"], d["message"]
    assert _machtpunkte(d["charakter_daten"]) == basis + 10


def test_machtpunkte_ab_legendaer_beliebig_oft_mit_2_punkten(daten):
    d = _mit_ah(daten)
    basis = _machtpunkte(d)
    d = mit_aufstieg(d, anzahl=19)
    d["verbleibende_aufstiege"] = 3  # 16 ausgegeben → Legendär
    for _ in range(3):
        ergebnis = aktion("talent/waehlen", d, "Machtpunkte")
        assert ergebnis["success"], ergebnis["message"]
        d = ergebnis["charakter_daten"]
    assert _machtpunkte(d) == basis + 3 * 2

    # Rücknahme eines Legendär-Kaufs nimmt auch nur 2 MP zurück
    d = aktion("talent/entfernen", d, "Machtpunkte")["charakter_daten"]
    assert _machtpunkte(d) == basis + 2 * 2


def test_machtpunkte_rang_vor_der_buchung_zaehlt(daten):
    """Der Kauf mit dem 16. Aufstieg zählt noch als Heroisch (wie das Rang-Gate)."""
    d = _mit_ah(daten)
    basis = _machtpunkte(d)
    d = mit_aufstieg(d, anzahl=16)
    d["verbleibende_aufstiege"] = 1  # 15 ausgegeben → Heroisch
    d = aktion("talent/waehlen", d, "Machtpunkte")["charakter_daten"]
    assert _machtpunkte(d) == basis + 5
