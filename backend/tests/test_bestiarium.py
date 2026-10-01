"""Bestiarium: Datenintegrität der Kreaturen und die /api/bestiarium-Endpunkte.

Die Werte stammen aus dem Regelwerk (SWADE, Kapitel 6). Die Prüfungen hier
fangen Übertragungsfehler ab: Robustheit muss der SWADE-Formel folgen
(2 + Konstitution/2 + Größe + Panzerung, bei Untoten +2) und die
Würfelangaben müssen dem Format entsprechen, das der Simulator parst.
"""

import re

import pytest
from fastapi.testclient import TestClient

from main import app
from app.services import bestiarium as service

client = TestClient(app)

KREATUREN = service.liste_kreaturen()
WUERFEL_MUSTER = re.compile(r"^W\d+([+-]\d+)?$")
ERWARTETE_ATTRIBUTE = {
    "Geschicklichkeit",
    "Konstitution",
    "Stärke",
    "Verstand",
    "Willenskraft",
}


def alle_ids() -> list[str]:
    return [k["id"] for k in KREATUREN]


def seiten(wuerfel: str) -> int:
    treffer = re.match(r"W(\d+)", wuerfel or "")
    return int(treffer.group(1)) if treffer else 0


def test_bestiarium_ist_nicht_leer():
    assert len(KREATUREN) >= 39


def test_ids_sind_eindeutig():
    ids = alle_ids()
    assert len(ids) == len(set(ids))


@pytest.mark.parametrize("kreatur_id", alle_ids())
def test_attribute_und_fertigkeiten_sind_lesbare_wuerfel(kreatur_id):
    kreatur = service.lade_kreatur(kreatur_id)
    assert set(kreatur["attribute"]) == ERWARTETE_ATTRIBUTE
    for wuerfel in list(kreatur["attribute"].values()) + list(kreatur["fertigkeiten"].values()):
        assert WUERFEL_MUSTER.match(wuerfel), f"{kreatur_id}: {wuerfel}"


@pytest.mark.parametrize("kreatur_id", alle_ids())
def test_robustheit_folgt_der_swade_formel(kreatur_id):
    """robustheit ist der gedruckte Gesamtwert inklusive Panzerung."""
    kreatur = service.lade_kreatur(kreatur_id)
    untot = any(f["name"] == "Untot" for f in kreatur["spezialfaehigkeiten"])
    erwartet = (
        2
        + seiten(kreatur["attribute"]["Konstitution"]) // 2
        + kreatur["groesse"]
        + kreatur["panzerung"]
        + (2 if untot else 0)
    )
    assert kreatur["robustheit"] == erwartet


@pytest.mark.parametrize("kreatur_id", alle_ids())
def test_kampfprofil_zieht_panzerung_ab(kreatur_id):
    """Der Simulator verrechnet PB gegen die Panzerung, darum getrennt."""
    kreatur = service.lade_kreatur(kreatur_id)
    profil = service.generiere_kampfprofil(kreatur)
    assert profil["robustheit"] + profil["panzerung"] == kreatur["robustheit"]
    assert profil["panzerung"] == kreatur["panzerung"]
    assert profil["bennys"] == (3 if kreatur["wildcard"] else 0)
    assert profil["widerstandsfaehig"] == kreatur["widerstandsfaehig"]
    assert profil["zaeh"] == kreatur["zaeh"]
    assert profil["groesse"] == kreatur.get("groesse", 0)
    for waffe in profil["waffen"]:
        assert waffe["schaden"]
        assert waffe["fertigkeit"] in {"Kämpfen", "Schießen"}


@pytest.mark.parametrize("kreatur_id", alle_ids())
def test_spezialfaehigkeiten_passen_zu_den_flags(kreatur_id):
    """Die vom Simulator ausgewerteten Flags müssen mit dem Statblock
    übereinstimmen — sonst greift die Regel im Kampf nicht."""
    kreatur = service.lade_kreatur(kreatur_id)
    namen = {f["name"] for f in kreatur["spezialfaehigkeiten"]}
    assert bool(kreatur["widerstandsfaehig"]) == ("Widerstandsfähig" in namen)
    assert kreatur["zaeh"] == ("Zäh" in namen)


def test_lich_ist_der_einzige_wirker():
    """Nur der Lich hat laut Regelwerk Machtpunkte (50) und Zauber."""
    wirker = {
        k["id"]: service.lade_kreatur(k["id"])
        for k in KREATUREN
        if service.lade_kreatur(k["id"]).get("machtpunkte")
    }
    assert set(wirker) == {"lich"}
    lich = wirker["lich"]
    assert lich["machtpunkte"] == 50
    assert lich["arkane_fertigkeit"] == "Zaubern"
    assert lich["arkane_fertigkeit"] in lich["fertigkeiten"]
    assert "Geschoss" in lich["maechte"]
    assert "Betäuben" in lich["maechte"]

    profil = service.generiere_kampfprofil(lich)
    assert profil["machtpunkte"] == 50
    assert profil["arkane_fertigkeit"] == "Zaubern"


def test_nichtwirker_liefern_leere_machtfelder():
    profil = service.generiere_kampfprofil(service.lade_kreatur("troll"))
    assert profil["machtpunkte"] == 0
    assert profil["arkane_fertigkeit"] == ""
    assert profil["maechte"] == []


def test_widerstandsfaehige_und_zaehe_kreaturen():
    """Fixiert, welche Kreaturen die beiden Regeln laut Regelwerk haben."""
    widerstandsfaehig = {k["id"] for k in KREATUREN if service.lade_kreatur(k["id"])["widerstandsfaehig"]}
    zaeh = {k["id"] for k in KREATUREN if service.lade_kreatur(k["id"])["zaeh"]}
    assert widerstandsfaehig == {"drachling", "erdelementar", "minotaurus", "oger", "troll"}
    assert zaeh == {"drache", "hai-weisser-hai", "riesenwurm"}


def test_liste_endpunkt():
    resp = client.get("/api/bestiarium")
    assert resp.status_code == 200
    daten = resp.json()
    assert len(daten) == len(KREATUREN)
    assert {"id", "name", "kategorie", "wildcard", "parade", "robustheit"} <= set(daten[0])


def test_detail_endpunkt():
    resp = client.get("/api/bestiarium/troll")
    assert resp.status_code == 200
    troll = resp.json()
    assert troll["name"] == "Troll"
    assert troll["robustheit"] == 9
    assert troll["panzerung"] == 1
    assert "Rohling" in troll["talente"]
    assert any(f["name"] == "Widerstandsfähig" for f in troll["spezialfaehigkeiten"])


def test_kampfprofil_endpunkt():
    resp = client.get("/api/bestiarium/troll/kampfprofil")
    assert resp.status_code == 200
    profil = resp.json()
    # 9 gedruckt minus 1 Panzerung
    assert profil["robustheit"] == 8
    assert profil["panzerung"] == 1
    assert profil["attribute"]["Stärke"] == "W12+2"
    assert any(w["name"] == "Stachelkeule" for w in profil["waffen"])


def test_unbekannte_kreatur_ergibt_404():
    assert client.get("/api/bestiarium/gibtsnicht").status_code == 404
    assert client.get("/api/bestiarium/gibtsnicht/kampfprofil").status_code == 404
