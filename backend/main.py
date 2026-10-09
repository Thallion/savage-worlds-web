import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from sqlalchemy import inspect, text

from app.config import settings
from app.db.database import SessionLocal, engine
from app.db.models import Base, Charakter
from app.services import charakterbild
from app.api.auth import router as auth_router
from app.api.archetypen import router as archetypen_router
from app.api.bestiarium import router as bestiarium_router
from app.api.bilder import router as bilder_router
from app.api.charaktere import router as charaktere_router
from app.api.einstellungen import router as einstellungen_router
from app.api.ordner import router as ordner_router
from app.api.spiellogik import router as spiellogik_router

data_dir = Path("data")
data_dir.mkdir(exist_ok=True)

Base.metadata.create_all(bind=engine)


def _leichte_migration() -> None:
    """Ergänzt fehlende Spalten in bestehenden DBs. create_all() legt zwar neue
    Tabellen (ordner) an, verändert aber keine vorhandenen. Kein Alembic → wir
    fügen ordner_id bei Bedarf idempotent per ADD COLUMN hinzu."""
    inspector = inspect(engine)
    spalten = {s["name"] for s in inspector.get_columns("charaktere")}
    if "ordner_id" not in spalten:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE charaktere ADD COLUMN ordner_id INTEGER REFERENCES ordner(id)"))
    if "bild_id" not in spalten:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE charaktere ADD COLUMN bild_id VARCHAR(32)"))
    if "bild_fokus_y" not in spalten:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE charaktere ADD COLUMN bild_fokus_y FLOAT"))


def _bild_waisen_aufraeumen() -> None:
    """Porträt-Dateien ohne Charakter löschen (Absturz zwischen Schreiben und Commit)."""
    with SessionLocal() as db:
        bekannte = {
            bild_id for (bild_id,) in db.query(Charakter.bild_id).filter(Charakter.bild_id.isnot(None))
        }
    charakterbild.raeume_waisen_auf(bekannte)


_leichte_migration()
_bild_waisen_aufraeumen()

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(charaktere_router)
app.include_router(ordner_router)
app.include_router(archetypen_router)
app.include_router(bestiarium_router)
app.include_router(bilder_router)
app.include_router(einstellungen_router)
app.include_router(spiellogik_router)


@app.get("/api/health")
def health():
    return {"status": "ok", "version": "0.1.0"}
