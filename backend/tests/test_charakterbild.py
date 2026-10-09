"""Charakterporträts: Upload-Pipeline, Endpunkte, Aufräumen, Export/Import, Bogen."""

import base64
import os
import time
from io import BytesIO

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from main import app
from app.api.deps import get_current_user
from app.config import settings as app_settings
from app.db import models as db_models
from app.db.database import Base, get_db
from app.services import charakterbild
from app.services.charakter_init import initialisiere_charakter_daten


def _bild(breite=900, hoehe=1200, fmt="JPEG", farbe=(120, 60, 30), exif_gps=False) -> bytes:
    img = Image.new("RGB", (breite, hoehe), farbe)
    puffer = BytesIO()
    kwargs = {}
    if exif_gps:
        exif = Image.Exif()
        exif[0x010F] = "Testkamera"  # Make
        kwargs["exif"] = exif
    img.save(puffer, fmt, **kwargs)
    return puffer.getvalue()


@pytest.fixture(autouse=True)
def bilder_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(app_settings, "bilder_path", tmp_path / "bilder")
    return tmp_path / "bilder"


@pytest.fixture
def client():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autocommit=False, autoflush=False)

    with Session() as db:
        for name in ("held", "fremd"):
            db.add(db_models.User(email=f"{name}@example.org", benutzername=name, hashed_password="x"))
        db.commit()

    aktueller = {"name": "held"}

    def _db():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    def _user():
        with Session() as db:
            return db.query(db_models.User).filter_by(benutzername=aktueller["name"]).first()

    app.dependency_overrides[get_db] = _db
    app.dependency_overrides[get_current_user] = _user
    c = TestClient(app)
    c.aktueller = aktueller
    c.Session = Session
    yield c
    app.dependency_overrides.clear()


def _neuer_charakter(client, name="Porträtheld") -> dict:
    r = client.post("/api/charaktere", json={"char_name": name, "active_setting_name": "SWAE"})
    assert r.status_code == 201, r.text
    return r.json()


def _hochladen(client, char_id, inhalt, fokus_y=None, dateiname="bild.jpg"):
    data = {"fokus_y": str(fokus_y)} if fokus_y is not None else {}
    return client.put(
        f"/api/charaktere/{char_id}/bild",
        files={"datei": (dateiname, inhalt, "application/octet-stream")},
        data=data,
    )


# ---- Pipeline ----

@pytest.mark.parametrize("fmt", ["JPEG", "PNG", "WEBP", "GIF"])
def test_varianten_masse(fmt):
    varianten = charakterbild.erzeuge_varianten(_bild(fmt=fmt))
    masse = {k: Image.open(BytesIO(v)).size for k, v in varianten.items()}
    assert masse == {"gross": (600, 800), "karte": (240, 320), "avatar": (128, 128)}
    assert all(Image.open(BytesIO(v)).format == "WEBP" for v in varianten.values())


def test_querformat_wird_auf_3_zu_4_geschnitten():
    varianten = charakterbild.erzeuge_varianten(_bild(1600, 900))
    assert Image.open(BytesIO(varianten["gross"])).size == (600, 800)


def test_kleines_bild_wird_nicht_hochskaliert():
    varianten = charakterbild.erzeuge_varianten(_bild(300, 400))
    assert Image.open(BytesIO(varianten["gross"])).size == (300, 400)


def test_exif_wird_entfernt():
    varianten = charakterbild.erzeuge_varianten(_bild(exif_gps=True))
    for inhalt in varianten.values():
        assert not Image.open(BytesIO(inhalt)).getexif()


def test_transparenz_wird_weiss():
    img = Image.new("RGBA", (300, 400), (0, 0, 0, 0))
    puffer = BytesIO()
    img.save(puffer, "PNG")
    gross = Image.open(BytesIO(charakterbild.erzeuge_varianten(puffer.getvalue())["gross"]))
    assert gross.convert("RGB").getpixel((10, 10)) >= (250, 250, 250)


@pytest.mark.parametrize(
    "inhalt,status",
    [
        (b"<svg xmlns='http://www.w3.org/2000/svg'></svg>", 400),
        (b"kein bild, nur text", 400),
        (_bild(100, 100), 400),  # zu klein
        (_bild(fmt="BMP"), 400),  # Format nicht erlaubt
    ],
)
def test_ungueltige_uploads(inhalt, status):
    with pytest.raises(charakterbild.BildFehler) as e:
        charakterbild.erzeuge_varianten(inhalt)
    assert e.value.status_code == status


def test_zu_grosse_datei(monkeypatch):
    monkeypatch.setattr(app_settings, "bild_max_upload_mb", 0)
    with pytest.raises(charakterbild.BildFehler) as e:
        charakterbild.erzeuge_varianten(_bild())
    assert e.value.status_code == 413


def test_pixelbombe(monkeypatch):
    monkeypatch.setattr(charakterbild, "MAX_PIXEL", 500 * 500)
    with pytest.raises(charakterbild.BildFehler):
        charakterbild.erzeuge_varianten(_bild(900, 1200))


def test_pfad_validiert_id_und_variante():
    assert charakterbild.pfad("../../etc/passwd", "gross") is None
    assert charakterbild.pfad("a" * 32, "original") is None
    assert charakterbild.pfad("a" * 32, "gross") is not None


def test_waisen_aufraeumen(bilder_dir):
    behalten = charakterbild.speichere(charakterbild.erzeuge_varianten(_bild()))
    waise = charakterbild.speichere(charakterbild.erzeuge_varianten(_bild()))
    frisch = charakterbild.speichere(charakterbild.erzeuge_varianten(_bild()))
    alt = time.time() - 7200
    for datei in bilder_dir.iterdir():
        if not datei.name.startswith(frisch):
            os.utime(datei, (alt, alt))
    assert charakterbild.raeume_waisen_auf({behalten}) == 3
    assert charakterbild.lade(behalten) and charakterbild.lade(frisch)
    assert charakterbild.lade(waise) is None


# ---- Endpunkte ----

def test_upload_abruf_und_liste(client):
    char = _neuer_charakter(client)
    assert char["bild_id"] is None

    r = _hochladen(client, char["id"], _bild(), fokus_y=0.5)
    assert r.status_code == 200, r.text
    bild_id = r.json()["bild_id"]
    assert charakterbild.ist_gueltige_bild_id(bild_id)
    assert r.json()["bild_fokus_y"] == 0.5

    liste = client.get("/api/charaktere").json()
    assert liste[0]["bild_id"] == bild_id

    # Abruf ohne Login, mit langem Cache
    app.dependency_overrides.pop(get_current_user)
    r = client.get(f"/api/bilder/{bild_id}/karte.webp")
    assert r.status_code == 200
    assert r.headers["content-type"] == "image/webp"
    assert "immutable" in r.headers["cache-control"]
    assert client.get(f"/api/bilder/{'0' * 32}/karte.webp").status_code == 404
    assert client.get(f"/api/bilder/{bild_id}/original.webp").status_code == 404


def test_ersetzen_loescht_altes_bild(client):
    char = _neuer_charakter(client)
    alt = _hochladen(client, char["id"], _bild()).json()["bild_id"]
    neu = _hochladen(client, char["id"], _bild(farbe=(0, 0, 200))).json()["bild_id"]
    assert alt != neu
    assert charakterbild.lade(alt) is None
    assert charakterbild.lade(neu) is not None


def test_ungueltiger_upload_aendert_nichts(client):
    char = _neuer_charakter(client)
    alt = _hochladen(client, char["id"], _bild()).json()["bild_id"]
    r = _hochladen(client, char["id"], b"<svg/>", dateiname="x.svg")
    assert r.status_code == 400
    assert client.get(f"/api/charaktere/{char['id']}").json()["bild_id"] == alt


def test_fokus_aendern_erzeugt_neue_id(client):
    char = _neuer_charakter(client)
    alt = _hochladen(client, char["id"], _bild()).json()["bild_id"]
    r = client.patch(f"/api/charaktere/{char['id']}/bild", json={"fokus_y": 0.9})
    assert r.status_code == 200, r.text
    assert r.json()["bild_id"] != alt and r.json()["bild_fokus_y"] == 0.9
    assert charakterbild.lade(alt) is None
    assert charakterbild.lade(r.json()["bild_id"], "avatar") is not None
    assert client.patch(f"/api/charaktere/{char['id']}/bild", json={"fokus_y": 2}).status_code == 422


def test_entfernen(client):
    char = _neuer_charakter(client)
    bild_id = _hochladen(client, char["id"], _bild()).json()["bild_id"]
    r = client.delete(f"/api/charaktere/{char['id']}/bild")
    assert r.status_code == 200 and r.json()["bild_id"] is None
    assert charakterbild.lade(bild_id) is None


def test_fremder_charakter(client):
    char = _neuer_charakter(client)
    client.aktueller["name"] = "fremd"
    assert _hochladen(client, char["id"], _bild()).status_code == 404
    assert client.delete(f"/api/charaktere/{char['id']}/bild").status_code == 404


def test_kontingent(client, monkeypatch):
    monkeypatch.setattr(app_settings, "bild_kontingent_mb", 0)
    char = _neuer_charakter(client)
    assert _hochladen(client, char["id"], _bild()).status_code == 409


def test_charakter_loeschen_raeumt_auf(client):
    char = _neuer_charakter(client)
    bild_id = _hochladen(client, char["id"], _bild()).json()["bild_id"]
    assert client.delete(f"/api/charaktere/{char['id']}").status_code == 204
    assert charakterbild.lade(bild_id) is None


def test_export_import_mit_bild(client):
    char = _neuer_charakter(client)
    bild_id = _hochladen(client, char["id"], _bild(), fokus_y=0.3).json()["bild_id"]

    export = client.get(f"/api/charaktere/{char['id']}/export").json()
    assert export["_portraet"]["mime"] == "image/webp"
    assert "_portraet" not in client.get(f"/api/charaktere/{char['id']}/export?mit_bild=false").json()

    r = client.post("/api/charaktere/import", json=export)
    assert r.status_code == 201, r.text
    importiert = r.json()
    assert importiert["bild_id"] and importiert["bild_id"] != bild_id
    assert importiert["bild_fokus_y"] == 0.3
    assert "_portraet" not in importiert["charakter_daten"]


def test_import_mit_kaputtem_bild_klappt_trotzdem(client):
    daten = initialisiere_charakter_daten("Kaputt", "SWAE")
    daten["_portraet"] = {"daten": base64.b64encode(b"kein bild").decode()}
    r = client.post("/api/charaktere/import", json=daten)
    assert r.status_code == 201
    assert r.json()["bild_id"] is None


# ---- Charakterbogen ----

def test_charakterbogen_mit_bild(client):
    char = _neuer_charakter(client)
    bild_id = _hochladen(client, char["id"], _bild()).json()["bild_id"]
    daten = client.get(f"/api/charaktere/{char['id']}").json()["charakter_daten"]

    html = client.post(
        "/api/spiellogik/charakterbogen", json={"charakter_daten": daten, "bild_id": bild_id}
    ).json()["html"]
    assert 'class="portraet" src="data:image/webp;base64,' in html

    ohne = client.post("/api/spiellogik/charakterbogen", json={"charakter_daten": daten}).json()["html"]
    assert "portraet" not in ohne.split("<body>")[-1]

    for printer_friendly in (False, True):
        mit = client.post(
            "/api/spiellogik/charakterbogen/pdf",
            json={"charakter_daten": daten, "bild_id": bild_id, "printer_friendly": printer_friendly},
        )
        assert mit.status_code == 200 and mit.content.startswith(b"%PDF")
        assert b"/Subtype /Image" in mit.content or b"/Subtype/Image" in mit.content
