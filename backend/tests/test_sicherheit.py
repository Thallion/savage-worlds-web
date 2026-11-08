"""Sicherheit: Passwort-Hashing/-Regeln, Token-Invalidierung und die
Besitzer-Prüfung eigener Settings — mit echter Anmeldung statt
überschriebenem get_current_user."""

import hashlib
import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from main import app
from app.api import auth
from app.config import settings as app_settings
from app.db import models as db_models
from app.db.database import Base, get_db
from app.services import setting_verwaltung as sv


@pytest.fixture(autouse=True)
def umgebung(tmp_path, monkeypatch):
    monkeypatch.setattr(app_settings, "custom_settings_path", tmp_path / "settings")
    monkeypatch.setattr(app_settings, "admin_emails", "admin@example.org")
    # 600k Iterationen machen die Tests unnötig langsam
    monkeypatch.setattr(auth, "_PBKDF2_ITERATIONEN", 1_000)


@pytest.fixture
def client():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autocommit=False, autoflush=False)

    def _db():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _db
    c = TestClient(app)
    c.Session = Session
    yield c
    app.dependency_overrides.clear()


def _registriere(client, name: str, passwort: str = "geheim123") -> dict:
    r = client.post(
        "/api/auth/register",
        json={"email": f"{name}@example.org", "benutzername": name, "passwort": passwort},
    )
    assert r.status_code == 201, r.text
    r = client.post("/api/auth/login", json={"email": f"{name}@example.org", "passwort": passwort})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _leeres_setting(client, kopf: dict, name: str):
    return client.post("/api/settings", json={"name": name, "modus": "leer"}, headers=kopf)


# --- Passwörter & Tokens ---------------------------------------------------


def test_registrierung_verlangt_mindestlaenge(client):
    r = client.post(
        "/api/auth/register",
        json={"email": "kurz@example.org", "benutzername": "kurz", "passwort": "1234567"},
    )
    assert r.status_code == 400
    assert "mindestens 8" in r.json()["detail"]


def test_hash_format_und_alte_hashes_werden_umgeschluesselt(client):
    # Alter Hash (salt:key, 100k Iterationen) wie vor der Umstellung
    salt = os.urandom(32)
    alt = salt.hex() + ":" + hashlib.pbkdf2_hmac("sha256", b"altespw1", salt, 100_000).hex()
    with client.Session() as db:
        db.add(db_models.User(email="alt@example.org", benutzername="alt", hashed_password=alt))
        db.commit()

    r = client.post("/api/auth/login", json={"email": "alt@example.org", "passwort": "altespw1"})
    assert r.status_code == 200
    with client.Session() as db:
        neu = db.query(db_models.User).filter_by(benutzername="alt").one().hashed_password
    assert neu.startswith("pbkdf2_sha256$1000$")
    # Login funktioniert auch mit dem neuen Hash
    r = client.post("/api/auth/login", json={"email": "alt@example.org", "passwort": "altespw1"})
    assert r.status_code == 200
    assert not auth._verify_password("falsch", neu)


def test_passwortaenderung_entwertet_alte_tokens(client):
    alt = _registriere(client, "held")
    assert client.get("/api/auth/me", headers=alt).status_code == 200

    r = client.put(
        "/api/auth/passwort",
        json={"aktuelles_passwort": "geheim123", "neues_passwort": "kurz"},
        headers=alt,
    )
    assert r.status_code == 400

    r = client.put(
        "/api/auth/passwort",
        json={"aktuelles_passwort": "geheim123", "neues_passwort": "nochgeheimer"},
        headers=alt,
    )
    assert r.status_code == 200
    neu = {"Authorization": f"Bearer {r.json()['access_token']}"}
    assert client.get("/api/auth/me", headers=alt).status_code == 401
    assert client.get("/api/auth/me", headers=neu).status_code == 200


def test_token_ohne_passwort_fingerabdruck_wird_abgelehnt(client):
    _registriere(client, "held")
    from app.jwt_utils import encode

    token = encode({"sub": 1, "exp": 9_999_999_999}, app_settings.secret_key)
    r = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 401


# --- Besitzer eigener Settings ---------------------------------------------


def test_nur_besitzer_darf_setting_aendern(client):
    held = _registriere(client, "held")
    fremd = _registriere(client, "fremd")
    assert _leeres_setting(client, held, "Heldenwelt").status_code == 201

    # Lesen und Benutzen bleibt für alle offen
    assert client.get("/api/settings/Heldenwelt", headers=fremd).status_code == 200

    for methode, pfad, body in (
        ("put", "/api/settings/Heldenwelt", {"beschreibung": "gekapert"}),
        ("post", "/api/settings/Heldenwelt/elemente", {"quelle": "SWAE", "elemente": {}}),
        (
            "put",
            "/api/settings/Heldenwelt/elemente",
            {"typ": "talente", "element_name": "X", "element_daten": {}},
        ),
        (
            "post",
            "/api/settings/Heldenwelt/elemente/entfernen",
            {"typ": "talente", "element_name": "X"},
        ),
    ):
        r = getattr(client, methode)(pfad, json=body, headers=fremd)
        assert r.status_code == 403, (pfad, r.text)
    assert client.delete("/api/settings/Heldenwelt", headers=fremd).status_code == 403

    # Besitzer darf
    r = client.put("/api/settings/Heldenwelt", json={"beschreibung": "meins"}, headers=held)
    assert r.status_code == 200
    assert client.delete("/api/settings/Heldenwelt", headers=held).status_code == 204


def test_bearbeitbar_flag_und_besitzer_bleibt_intern(client):
    held = _registriere(client, "held")
    fremd = _registriere(client, "fremd")
    _leeres_setting(client, held, "Heldenwelt")

    def flag(kopf):
        liste = client.get("/api/settings", headers=kopf).json()
        return {s["name"]: s["bearbeitbar"] for s in liste}

    assert flag(held)["Heldenwelt"] is True
    assert flag(fremd)["Heldenwelt"] is False
    assert flag({})["Heldenwelt"] is False
    assert flag(held)["SWAE"] is False

    detail = client.get("/api/settings/Heldenwelt", headers=held).json()
    assert detail["bearbeitbar"] is True
    assert sv.BESITZER_KEY not in detail
    export = client.get("/api/settings/Heldenwelt/export", headers=held).json()
    assert sv.BESITZER_KEY not in export


def test_import_und_kopie_gehoeren_dem_importierenden(client):
    held = _registriere(client, "held")
    fremd = _registriere(client, "fremd")
    _leeres_setting(client, held, "Heldenwelt")

    r = client.post(
        "/api/settings",
        json={"name": "Meine Kopie", "modus": "kopie", "quellen": ["Heldenwelt"]},
        headers=fremd,
    )
    assert r.status_code == 201
    # Ein eingeschleuster Besitzer im Import-JSON wird ignoriert
    r = client.post(
        "/api/settings/import",
        json={"name": "Import", "talente": {}, sv.BESITZER_KEY: 1},
        headers=fremd,
    )
    assert r.status_code == 201
    assert sv.besitzer_von("Meine Kopie") == 2
    assert sv.besitzer_von("Import") == 2


def test_alte_settings_ohne_besitzer_nur_fuer_admins(client):
    held = _registriere(client, "held")
    admin = _registriere(client, "admin")
    sv.speichere_custom_setting("Altbestand", sv.leeres_setting())

    r = client.put("/api/settings/Altbestand", json={"beschreibung": "x"}, headers=held)
    assert r.status_code == 403
    r = client.put("/api/settings/Altbestand", json={"beschreibung": "x"}, headers=admin)
    assert r.status_code == 200
    # Admin darf auch fremde Settings
    _leeres_setting(client, held, "Heldenwelt")
    assert client.delete("/api/settings/Heldenwelt", headers=admin).status_code == 204


def test_kontingent_und_groessengrenze(client, monkeypatch):
    held = _registriere(client, "held")
    monkeypatch.setattr(app_settings, "settings_max_pro_nutzer", 2)
    assert _leeres_setting(client, held, "Eins").status_code == 201
    assert _leeres_setting(client, held, "Zwei").status_code == 201
    r = _leeres_setting(client, held, "Drei")
    assert r.status_code == 422
    assert "bereits 2" in r.json()["detail"]

    monkeypatch.setattr(app_settings, "settings_max_pro_nutzer", 25)
    monkeypatch.setattr(app_settings, "setting_max_mb", 0)
    r = client.post(
        "/api/settings/import", json={"name": "Riesig", "talente": {}}, headers=held
    )
    assert r.status_code == 422
    assert "zu groß" in r.json()["detail"]
