from fastapi import APIRouter, HTTPException

from app.services import bestiarium as bestiarium_service

router = APIRouter(prefix="/api/bestiarium", tags=["bestiarium"])


@router.get("")
def list_kreaturen():
    """Kurzinfos aller Kreaturen (id, name, kategorie, wildcard, Werte)."""
    return bestiarium_service.liste_kreaturen()


@router.get("/{kreatur_id}")
def get_kreatur(kreatur_id: str):
    """Vollständiger Bestiarium-Eintrag inklusive Spezialfähigkeiten."""
    kreatur = bestiarium_service.lade_kreatur(kreatur_id)
    if kreatur is None:
        raise HTTPException(status_code=404, detail="Kreatur nicht gefunden")
    return kreatur


@router.get("/{kreatur_id}/kampfprofil")
def get_kampfprofil(kreatur_id: str):
    """Kampfprofil der Kreatur für den Kampfsimulator."""
    kreatur = bestiarium_service.lade_kreatur(kreatur_id)
    if kreatur is None:
        raise HTTPException(status_code=404, detail="Kreatur nicht gefunden")
    return bestiarium_service.generiere_kampfprofil(kreatur)
