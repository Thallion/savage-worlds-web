from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.services import charakterbild

router = APIRouter(prefix="/api/bilder", tags=["bilder"])


@router.get("/{bild_id}/{variante}.webp")
def bild_abrufen(bild_id: str, variante: str):
    """Liefert eine Porträt-Variante aus — ohne Login: die nicht erratbare
    bild_id ist die Berechtigung (<img src> kann keinen Bearer-Header senden).
    Neue Bilder bekommen immer eine neue ID, daher immutable."""
    ziel = charakterbild.pfad(bild_id, variante)
    if ziel is None or not ziel.is_file():
        raise HTTPException(status_code=404, detail="Bild nicht gefunden")
    return FileResponse(
        ziel,
        media_type="image/webp",
        headers={"Cache-Control": "public, max-age=31536000, immutable"},
    )
