from datetime import datetime
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.database import get_db
from app.db import models as db_models
from app.schemas.charakter import (
    CharakterCreate,
    CharakterUpdate,
    CharakterDetail,
    CharakterListItem,
)
from app.services.charakter_init import (
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
    """Importiert einen Charakter aus einem Export-JSON (nackte charakter_daten,
    wie /{id}/export sie liefert). Fehlende Felder — auch bei Alt-Exporten aus
    der Kivy-App — werden über die Lazy-Init-Normalisierung nachgefüllt."""
    if not isinstance(charakter_daten, dict) or not charakter_daten:
        raise HTTPException(status_code=422, detail="Kein gültiges Charakter-JSON")

    daten, _ = ergaenze_fehlende_eigenschaften(charakter_daten)
    char_name = daten.get("profil_daten", {}).get("Name") or "Importierter Charakter"

    # char_name ist pro User eindeutig — bei Kollision nummerieren
    vorhandene = {
        name
        for (name,) in db.query(db_models.Charakter.char_name).filter(
            db_models.Charakter.user_id == current_user.id
        )
    }
    if char_name in vorhandene:
        n = 2
        while f"{char_name} ({n})" in vorhandene:
            n += 1
        char_name = f"{char_name} ({n})"

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

    if data.char_name is not None:
        charakter.char_name = data.char_name
    if data.active_setting_name is not None:
        charakter.active_setting_name = data.active_setting_name
    if data.char_gen_completed is not None:
        charakter.char_gen_completed = data.char_gen_completed
    if data.charakter_daten is not None:
        charakter.charakter_daten = data.charakter_daten

    charakter.aktualisiert_am = datetime.utcnow()
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
    db.delete(charakter)
    db.commit()


@router.get("/{charakter_id}/export")
def export_charakter(
    charakter_id: int,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_user),
):
    charakter = _get_own_charakter(db, charakter_id, current_user.id)
    return JSONResponse(
        content=charakter.charakter_daten,
        headers={
            "Content-Disposition": f'attachment; filename="{charakter.char_name or "charakter"}.json"'
        },
    )


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
