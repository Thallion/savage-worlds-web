"""Settings-API: Lesen der mitgelieferten Settings plus Verwaltung eigener
Settings (Erstellen leer/als Kopie, Zusammenführung, Aus Charakter,
Elementauswahl; Original: CustomElementManager + setting_merge.py).

Lesen ist offen, alle schreibenden Endpoints erfordern Login. Eigene Settings
gelten instanzweit (wie die custom_*.json der Kivy-App) — gelöscht oder
umbenannt werden kann nur, was kein Charakter gerade benutzt.
"""

import copy

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.database import get_db
from app.db import models as db_models
from app.schemas.einstellungen import (
    ElementeHinzufuegenRequest,
    ElementEntfernenRequest,
    SettingErstellenRequest,
    SettingUpdateRequest,
    SettingVerwaltungResponse,
)
from app.services import setting_verwaltung as sv
from app.services.charakter_init import load_setting

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("")
def list_settings():
    return sv.liste_settings()


@router.get("/{setting_name}")
def get_setting(setting_name: str):
    try:
        setting = load_setting(setting_name)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Setting '{setting_name}' nicht gefunden")
    setting["custom"] = sv.ist_custom_setting(setting_name)
    return setting


def _verwendet_von(db: Session, setting_name: str) -> int:
    return (
        db.query(db_models.Charakter)
        .filter(db_models.Charakter.active_setting_name == setting_name)
        .count()
    )


def _antwort(name: str, setting: dict, konflikte=None, warnungen=None) -> SettingVerwaltungResponse:
    return SettingVerwaltungResponse(
        name=name,
        beschreibung=setting.get("description", ""),
        statistik=sv.statistik(setting),
        konflikte=konflikte or [],
        warnungen=warnungen or [],
    )


@router.post("", response_model=SettingVerwaltungResponse, status_code=status.HTTP_201_CREATED)
def erstelle_setting(
    req: SettingErstellenRequest,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_user),
):
    name, fehler = sv.pruefe_neuer_name(req.name)
    if name is None:
        raise HTTPException(status_code=422, detail=fehler)

    konflikte: list[dict] = []
    warnungen: list[str] = []
    try:
        if req.modus == "leer":
            setting = sv.leeres_setting()
        elif req.modus == "kopie":
            if len(req.quellen) != 1:
                raise HTTPException(status_code=422, detail="Kopie braucht genau ein Quell-Setting")
            setting = copy.deepcopy(load_setting(req.quellen[0]))
        elif req.modus == "zusammenfuehrung":
            if len(req.quellen) < 2:
                raise HTTPException(
                    status_code=422, detail="Zusammenführung braucht mindestens zwei Settings"
                )
            setting, konflikte = sv.fuehre_zusammen(req.quellen)
        elif req.modus == "aus_charakter":
            if req.charakter_id is None:
                raise HTTPException(status_code=422, detail="charakter_id fehlt")
            charakter = (
                db.query(db_models.Charakter)
                .filter(
                    db_models.Charakter.id == req.charakter_id,
                    db_models.Charakter.user_id == current_user.id,
                )
                .first()
            )
            if not charakter:
                raise HTTPException(status_code=404, detail="Charakter nicht gefunden")
            setting = sv.aus_charakter(charakter.charakter_daten)
        else:  # elementauswahl
            if not req.basis:
                raise HTTPException(status_code=422, detail="Basis-Setting fehlt")
            setting, konflikte, fehlend = sv.aus_elementauswahl(req.basis, req.elemente)
            warnungen = [f"Nicht gefunden: {eintrag}" for eintrag in fehlend]
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"Setting '{exc}' nicht gefunden")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    if req.beschreibung:
        setting["description"] = req.beschreibung
    elif not setting.get("description"):
        setting["description"] = f"Eigenes Setting von {current_user.benutzername}"

    sv.speichere_custom_setting(name, setting)
    return _antwort(name, setting, konflikte, warnungen)


@router.put("/{setting_name}", response_model=SettingVerwaltungResponse)
def update_setting(
    setting_name: str,
    req: SettingUpdateRequest,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_user),
):
    if req.neuer_name is not None and req.neuer_name.strip() != setting_name:
        anzahl = _verwendet_von(db, setting_name)
        if anzahl:
            raise HTTPException(
                status_code=409,
                detail=f"'{setting_name}' wird von {anzahl} Charakter(en) benutzt "
                "und kann nicht umbenannt werden",
            )
    setting, name, fehler = sv.aktualisiere_metadaten(setting_name, req.beschreibung, req.neuer_name)
    if setting is None:
        raise HTTPException(status_code=404 if "nicht gefunden" in fehler else 422, detail=fehler)
    return _antwort(name, setting)


@router.delete("/{setting_name}", status_code=status.HTTP_204_NO_CONTENT)
def delete_setting(
    setting_name: str,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_user),
):
    anzahl = _verwendet_von(db, setting_name)
    if anzahl:
        raise HTTPException(
            status_code=409,
            detail=f"'{setting_name}' wird von {anzahl} Charakter(en) benutzt "
            "und kann nicht gelöscht werden",
        )
    ok, fehler = sv.loesche_custom_setting(setting_name)
    if not ok:
        raise HTTPException(status_code=404 if "nicht gefunden" in fehler else 422, detail=fehler)


@router.post("/{setting_name}/elemente", response_model=SettingVerwaltungResponse)
def elemente_hinzufuegen(
    setting_name: str,
    req: ElementeHinzufuegenRequest,
    current_user: db_models.User = Depends(get_current_user),
):
    setting, fehler, fehlend = sv.elemente_hinzufuegen(setting_name, req.quelle, req.elemente)
    if setting is None:
        raise HTTPException(status_code=404 if "nicht gefunden" in fehler else 422, detail=fehler)
    return _antwort(setting_name, setting, warnungen=[f"Nicht gefunden: {e}" for e in fehlend])


@router.post("/{setting_name}/elemente/entfernen", response_model=SettingVerwaltungResponse)
def element_entfernen(
    setting_name: str,
    req: ElementEntfernenRequest,
    current_user: db_models.User = Depends(get_current_user),
):
    setting, fehler = sv.element_entfernen(setting_name, req.typ, req.element_name)
    if setting is None:
        raise HTTPException(status_code=404 if "nicht gefunden" in fehler else 422, detail=fehler)
    return _antwort(setting_name, setting)
