from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.database import get_db
from app.db import models as db_models
from app.schemas.charakter import CharakterDetail
from app.services import archetypen as archetyp_service

router = APIRouter(prefix="/api/archetypen", tags=["archetypen"])


@router.get("/ordner")
def list_ordner():
    """Ein virtueller (schreibgeschützter) Ordner je Setting mit Anzahl."""
    return archetyp_service.ordner_uebersicht()


@router.get("")
def list_archetypen():
    """Kurzinfos aller Archetypen (id, name, setting, char_gen_completed)."""
    return archetyp_service.liste_archetypen()


@router.get("/{archetyp_id}")
def get_archetyp(archetyp_id: str):
    """Vollständige charakter_daten eines Archetyps zum Ansehen."""
    daten = archetyp_service.lade_daten(archetyp_id)
    if daten is None:
        raise HTTPException(status_code=404, detail="Archetyp nicht gefunden")
    return daten


@router.post(
    "/{archetyp_id}/duplizieren",
    response_model=CharakterDetail,
    status_code=status.HTTP_201_CREATED,
)
def dupliziere_archetyp(
    archetyp_id: str,
    ordner_id: int | None = Body(default=None, embed=True),
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_user),
):
    """Legt aus einem Archetyp einen eigenen, editierbaren Charakter an."""
    daten: dict[str, Any] | None = archetyp_service.lade_daten(archetyp_id)
    if daten is None:
        raise HTTPException(status_code=404, detail="Archetyp nicht gefunden")

    # Optionaler Zielordner muss dem Nutzer gehören.
    if ordner_id is not None:
        ordner = (
            db.query(db_models.Ordner)
            .filter(
                db_models.Ordner.id == ordner_id,
                db_models.Ordner.user_id == current_user.id,
            )
            .first()
        )
        if not ordner:
            raise HTTPException(status_code=404, detail="Ordner nicht gefunden")

    # char_name ist pro User eindeutig — bei Kollision nummerieren (wie beim Import).
    char_name = daten.get("profil_daten", {}).get("Name") or "Archetyp"
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
        ordner_id=ordner_id,
        char_name=char_name,
        active_setting_name=daten.get("active_setting_name", "SWAE"),
        char_gen_completed=bool(daten.get("char_gen_completed", False)),
        charakter_daten=daten,
    )
    db.add(charakter)
    db.commit()
    db.refresh(charakter)
    return charakter
