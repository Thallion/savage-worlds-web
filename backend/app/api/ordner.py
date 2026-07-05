from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.database import get_db
from app.db import models as db_models
from app.schemas.ordner import OrdnerCreate, OrdnerResponse, OrdnerUpdate

router = APIRouter(prefix="/api/ordner", tags=["ordner"])


def _get_own_ordner(db: Session, ordner_id: int, user_id: int) -> db_models.Ordner:
    ordner = (
        db.query(db_models.Ordner)
        .filter(db_models.Ordner.id == ordner_id, db_models.Ordner.user_id == user_id)
        .first()
    )
    if not ordner:
        raise HTTPException(status_code=404, detail="Ordner nicht gefunden")
    return ordner


def _mit_anzahl(db: Session, ordner: db_models.Ordner) -> OrdnerResponse:
    anzahl = (
        db.query(func.count(db_models.Charakter.id))
        .filter(db_models.Charakter.ordner_id == ordner.id)
        .scalar()
    )
    return OrdnerResponse(
        id=ordner.id, name=ordner.name, erstellt_am=ordner.erstellt_am, anzahl_charaktere=anzahl
    )


@router.get("", response_model=list[OrdnerResponse])
def list_ordner(
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_user),
):
    # Charakterzahl je Ordner in einem Rutsch ermitteln.
    zaehler = dict(
        db.query(db_models.Charakter.ordner_id, func.count(db_models.Charakter.id))
        .filter(db_models.Charakter.user_id == current_user.id)
        .group_by(db_models.Charakter.ordner_id)
        .all()
    )
    ordner = (
        db.query(db_models.Ordner)
        .filter(db_models.Ordner.user_id == current_user.id)
        .order_by(db_models.Ordner.name)
        .all()
    )
    return [
        OrdnerResponse(
            id=o.id,
            name=o.name,
            erstellt_am=o.erstellt_am,
            anzahl_charaktere=zaehler.get(o.id, 0),
        )
        for o in ordner
    ]


@router.post("", response_model=OrdnerResponse, status_code=status.HTTP_201_CREATED)
def create_ordner(
    data: OrdnerCreate,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_user),
):
    name = data.name.strip()
    if not name:
        raise HTTPException(status_code=422, detail="Ordnername darf nicht leer sein")
    _pruefe_name_frei(db, current_user.id, name)

    ordner = db_models.Ordner(user_id=current_user.id, name=name)
    db.add(ordner)
    db.commit()
    db.refresh(ordner)
    return _mit_anzahl(db, ordner)


@router.put("/{ordner_id}", response_model=OrdnerResponse)
def update_ordner(
    ordner_id: int,
    data: OrdnerUpdate,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_user),
):
    ordner = _get_own_ordner(db, ordner_id, current_user.id)
    name = data.name.strip()
    if not name:
        raise HTTPException(status_code=422, detail="Ordnername darf nicht leer sein")
    if name != ordner.name:
        _pruefe_name_frei(db, current_user.id, name)
        ordner.name = name
        db.commit()
        db.refresh(ordner)
    return _mit_anzahl(db, ordner)


@router.delete("/{ordner_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_ordner(
    ordner_id: int,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_user),
):
    ordner = _get_own_ordner(db, ordner_id, current_user.id)
    # Charaktere bleiben erhalten, landen nur wieder „ohne Ordner".
    db.query(db_models.Charakter).filter(
        db_models.Charakter.ordner_id == ordner.id
    ).update({db_models.Charakter.ordner_id: None})
    db.delete(ordner)
    db.commit()


def _pruefe_name_frei(db: Session, user_id: int, name: str) -> None:
    vorhanden = (
        db.query(db_models.Ordner)
        .filter(db_models.Ordner.user_id == user_id, db_models.Ordner.name == name)
        .first()
    )
    if vorhanden:
        raise HTTPException(status_code=409, detail=f"Ordner '{name}' existiert bereits")
