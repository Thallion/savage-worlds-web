import base64
import binascii
from datetime import datetime
from typing import Any
from urllib.parse import quote

from fastapi import APIRouter, Body, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.config import settings
from app.db.database import get_db
from app.db import models as db_models
from app.schemas.charakter import (
    BildFokus,
    CharakterCreate,
    CharakterUpdate,
    CharakterDetail,
    CharakterListItem,
    CharakterVerschieben,
)
from app.services import charakterbild
from app.services.charakter_init import (
    entpacke_charakter_export,
    ergaenze_fehlende_eigenschaften,
    initialisiere_charakter_daten,
)

router = APIRouter(prefix="/api/charaktere", tags=["charaktere"])


@router.get("", response_model=list[CharakterListItem])
def list_charaktere(
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_user),
):
    return (
        db.query(db_models.Charakter)
        .filter(db_models.Charakter.user_id == current_user.id)
        .order_by(db_models.Charakter.aktualisiert_am.desc())
        .all()
    )


@router.post("", response_model=CharakterDetail, status_code=status.HTTP_201_CREATED)
def create_charakter(
    data: CharakterCreate,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_user),
):
    try:
        charakter_daten = initialisiere_charakter_daten(data.char_name, data.active_setting_name)
    except FileNotFoundError:
        raise HTTPException(
            status_code=404, detail=f"Setting '{data.active_setting_name}' nicht gefunden"
        )

    charakter = db_models.Charakter(
        user_id=current_user.id,
        char_name=data.char_name,
        active_setting_name=data.active_setting_name,
        charakter_daten=charakter_daten,
    )
    db.add(charakter)
    db.commit()
    db.refresh(charakter)
    return charakter


@router.post("/import", response_model=CharakterDetail, status_code=status.HTTP_201_CREATED)
def import_charakter(
    charakter_daten: dict[str, Any] = Body(...),
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_user),
):
    """Importiert einen Charakter aus einem Export-JSON — nackte charakter_daten
    (wie /{id}/export sie liefert) oder ein Voll-Export mit Wrapper (DB-Zeile).
    Fehlende Felder — auch bei Alt-Exporten aus der Kivy-App — werden über die
    Lazy-Init-Normalisierung nachgefüllt."""
    if not isinstance(charakter_daten, dict) or not charakter_daten:
        raise HTTPException(status_code=422, detail="Kein gültiges Charakter-JSON")

    daten = dict(entpacke_charakter_export(charakter_daten))
    # Eingebettetes Porträt aus dem Export (siehe export_charakter) — läuft durch
    # dieselbe Prüfung wie ein Upload; ein kaputtes Bild verhindert den Import nicht.
    portraet = daten.pop("_portraet", None)
    if portraet is None:
        portraet = charakter_daten.pop("_portraet", None) if isinstance(charakter_daten, dict) else None
    daten, _ = ergaenze_fehlende_eigenschaften(daten)
    char_name = (
        daten.get("profil_daten", {}).get("Name") or ""
    ).strip() or "Importierter Charakter"
    char_name = _eindeutiger_char_name(db, current_user.id, char_name)

    charakter = db_models.Charakter(
        user_id=current_user.id,
        char_name=char_name,
        active_setting_name=daten.get("active_setting_name", "SWAE"),
        char_gen_completed=bool(daten.get("char_gen_completed", False)),
        charakter_daten=daten,
    )
    db.add(charakter)
    db.commit()
    db.refresh(charakter)

    if isinstance(portraet, dict) and isinstance(portraet.get("daten"), str):
        try:
            roh = base64.b64decode(portraet["daten"], validate=True)
            fokus_y = portraet.get("fokus_y")
            varianten = charakterbild.erzeuge_varianten(
                roh, fokus_y if isinstance(fokus_y, (int, float)) else None
            )
            charakterbild.pruefe_kontingent(_belegter_bildspeicher(db, current_user.id), varianten)
        except (binascii.Error, ValueError, charakterbild.BildFehler):
            pass
        else:
            charakter.bild_id = charakterbild.speichere(varianten)
            charakter.bild_fokus_y = fokus_y if isinstance(fokus_y, (int, float)) else None
            db.commit()
            db.refresh(charakter)
    return charakter


@router.get("/{charakter_id}", response_model=CharakterDetail)
def get_charakter(
    charakter_id: int,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_user),
):
    charakter = _get_own_charakter(db, charakter_id, current_user.id)

    daten, geaendert = ergaenze_fehlende_eigenschaften(charakter.charakter_daten)
    if geaendert:
        # JSON-Column ohne MutableDict: nur eine Neuzuweisung wird von SQLAlchemy erkannt
        charakter.charakter_daten = daten
        db.commit()
        db.refresh(charakter)

    return charakter


@router.put("/{charakter_id}", response_model=CharakterDetail)
def update_charakter(
    charakter_id: int,
    data: CharakterUpdate,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_user),
):
    charakter = _get_own_charakter(db, charakter_id, current_user.id)

    if data.active_setting_name is not None:
        charakter.active_setting_name = data.active_setting_name
    if data.char_gen_completed is not None:
        charakter.char_gen_completed = data.char_gen_completed
    if data.charakter_daten is not None:
        charakter.charakter_daten = data.charakter_daten

    # Der Name im Profil ist die Quelle der Wahrheit: wird er im Editor geändert,
    # zieht die Spalte char_name nach (Charakterliste, Export-Dateiname). Nur wenn
    # keine charakter_daten mitkommen, zählt ein explizit gesetztes char_name.
    neuer_name = data.char_name
    if data.charakter_daten is not None:
        neuer_name = (data.charakter_daten.get("profil_daten") or {}).get("Name")
    if neuer_name is not None:
        neuer_name = neuer_name.strip()
        if neuer_name and neuer_name != charakter.char_name:
            charakter.char_name = _eindeutiger_char_name(
                db, current_user.id, neuer_name, ausser_id=charakter.id
            )

    charakter.aktualisiert_am = datetime.utcnow()
    db.commit()
    db.refresh(charakter)
    return charakter


@router.put("/{charakter_id}/verschieben", response_model=CharakterDetail)
def verschiebe_charakter(
    charakter_id: int,
    data: CharakterVerschieben,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_user),
):
    """Verschiebt einen Charakter in einen Ordner (ordner_id) oder heraus (None)."""
    charakter = _get_own_charakter(db, charakter_id, current_user.id)

    if data.ordner_id is not None:
        # Zielordner muss existieren und dem Nutzer gehören.
        ordner = (
            db.query(db_models.Ordner)
            .filter(
                db_models.Ordner.id == data.ordner_id,
                db_models.Ordner.user_id == current_user.id,
            )
            .first()
        )
        if not ordner:
            raise HTTPException(status_code=404, detail="Ordner nicht gefunden")

    charakter.ordner_id = data.ordner_id
    db.commit()
    db.refresh(charakter)
    return charakter


@router.delete("/{charakter_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_charakter(
    charakter_id: int,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_user),
):
    charakter = _get_own_charakter(db, charakter_id, current_user.id)
    bild_id = charakter.bild_id
    db.delete(charakter)
    db.commit()
    charakterbild.loesche(bild_id)


@router.put("/{charakter_id}/bild", response_model=CharakterDetail)
async def bild_hochladen(
    charakter_id: int,
    datei: UploadFile = File(...),
    fokus_y: float | None = Form(None),
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_user),
):
    """Setzt oder ersetzt das Porträt. Wirkt sofort (nicht erst beim Speichern
    des Charakters) und gehört nicht zum charakter_daten-Blob."""
    charakter = _get_own_charakter(db, charakter_id, current_user.id)
    if fokus_y is not None:
        fokus_y = min(1.0, max(0.0, fokus_y))

    # Eine Datei über dem Limit gar nicht erst ganz einlesen
    max_bytes = settings.bild_max_upload_mb * 1024 * 1024
    roh = await datei.read(max_bytes + 1)
    try:
        varianten = charakterbild.erzeuge_varianten(roh, fokus_y)
        belegt = _belegter_bildspeicher(db, current_user.id, ausser_id=charakter.id)
        charakterbild.pruefe_kontingent(belegt, varianten)
    except charakterbild.BildFehler as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)

    altes_bild = charakter.bild_id
    charakter.bild_id = charakterbild.speichere(varianten)
    charakter.bild_fokus_y = fokus_y
    db.commit()
    db.refresh(charakter)
    charakterbild.loesche(altes_bild)
    return charakter


@router.patch("/{charakter_id}/bild", response_model=CharakterDetail)
def bild_fokus_setzen(
    charakter_id: int,
    data: BildFokus,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_user),
):
    """Ändert nur den Avatar-Ausschnitt (vertikaler Fokus im Porträt). Der Avatar
    bekommt mit allen Varianten eine neue ID, damit gecachte Bilder nicht stehen bleiben."""
    charakter = _get_own_charakter(db, charakter_id, current_user.id)
    if not charakter.bild_id:
        raise HTTPException(status_code=404, detail="Charakter hat kein Bild")
    try:
        avatar = charakterbild.neuer_avatar(charakter.bild_id, data.fokus_y)
    except charakterbild.BildFehler as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)

    altes_bild = charakter.bild_id
    varianten = {
        "gross": charakterbild.lade(altes_bild, "gross"),
        "karte": charakterbild.lade(altes_bild, "karte"),
        "avatar": avatar,
    }
    charakter.bild_id = charakterbild.speichere({k: v for k, v in varianten.items() if v})
    charakter.bild_fokus_y = data.fokus_y
    db.commit()
    db.refresh(charakter)
    charakterbild.loesche(altes_bild)
    return charakter


@router.delete("/{charakter_id}/bild", response_model=CharakterDetail)
def bild_entfernen(
    charakter_id: int,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_user),
):
    charakter = _get_own_charakter(db, charakter_id, current_user.id)
    altes_bild = charakter.bild_id
    charakter.bild_id = None
    charakter.bild_fokus_y = None
    db.commit()
    db.refresh(charakter)
    charakterbild.loesche(altes_bild)
    return charakter


@router.get("/{charakter_id}/export")
def export_charakter(
    charakter_id: int,
    mit_bild: bool = True,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_user),
):
    charakter = _get_own_charakter(db, charakter_id, current_user.id)
    inhalt = charakter.charakter_daten
    # Porträt optional eingebettet (reservierter Key, Import entfernt ihn wieder)
    if mit_bild and charakter.bild_id:
        gross = charakterbild.lade(charakter.bild_id, "gross")
        if gross:
            inhalt = {
                **inhalt,
                "_portraet": {
                    "mime": "image/webp",
                    "fokus_y": charakter.bild_fokus_y,
                    "daten": base64.b64encode(gross).decode("ascii"),
                },
            }
    return JSONResponse(
        content=inhalt,
        headers={"Content-Disposition": _content_disposition(f"{charakter.char_name or 'charakter'}.json")},
    )


def _eindeutiger_char_name(
    db: Session, user_id: int, char_name: str, ausser_id: int | None = None
) -> str:
    """char_name ist pro User eindeutig — bei Kollision durchnummerieren.
    ausser_id klammert den Charakter aus, der gerade umbenannt wird."""
    query = db.query(db_models.Charakter.char_name).filter(
        db_models.Charakter.user_id == user_id
    )
    if ausser_id is not None:
        query = query.filter(db_models.Charakter.id != ausser_id)
    vorhandene = {name for (name,) in query}

    if char_name not in vorhandene:
        return char_name
    n = 2
    while f"{char_name} ({n})" in vorhandene:
        n += 1
    return f"{char_name} ({n})"


def _content_disposition(dateiname: str) -> str:
    """Header-Werte müssen latin-1/ASCII sein — Umlaute über filename* (RFC 5987)."""
    ascii_name = dateiname.encode("ascii", "ignore").decode("ascii") or "charakter.json"
    return f"attachment; filename=\"{ascii_name}\"; filename*=UTF-8''{quote(dateiname)}"


def _belegter_bildspeicher(db: Session, user_id: int, ausser_id: int | None = None) -> int:
    query = db.query(db_models.Charakter.bild_id).filter(
        db_models.Charakter.user_id == user_id,
        db_models.Charakter.bild_id.isnot(None),
    )
    if ausser_id is not None:
        query = query.filter(db_models.Charakter.id != ausser_id)
    return charakterbild.belegter_speicher(bild_id for (bild_id,) in query)


def _get_own_charakter(db: Session, charakter_id: int, user_id: int) -> db_models.Charakter:
    charakter = (
        db.query(db_models.Charakter)
        .filter(
            db_models.Charakter.id == charakter_id,
            db_models.Charakter.user_id == user_id,
        )
        .first()
    )
    if not charakter:
        raise HTTPException(status_code=404, detail="Charakter nicht gefunden")
    return charakter
