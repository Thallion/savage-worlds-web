"""Charakterporträts: Upload prüfen, Varianten erzeugen, ablegen, aufräumen.

Ablage flach unter settings.bilder_path als <bild_id>_<variante>.webp. Die
bild_id (uuid4, 128 Bit) ist zugleich die Berechtigung zum Abruf über
GET /api/bilder/<bild_id>/<variante>.webp — <img src> kann keinen
Bearer-Header mitschicken. Jedes Ersetzen erzeugt eine neue ID, deshalb dürfen
die Dateien als immutable gecacht werden.

Siehe docs/KONZEPT-Charakterbilder.md.
"""

import re
import time
import uuid
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError

from app.config import settings

ERLAUBTE_FORMATE = {"JPEG", "PNG", "WEBP", "GIF"}
MAX_PIXEL = 40_000_000
MIN_BREITE, MIN_HOEHE = 200, 266
STANDARD_FOKUS_Y = 0.2

# Variante → (Breite, Höhe, WebP-Qualität); alle im Hochformat 3:4 außer avatar
VARIANTEN = {
    "gross": (600, 800, 85),
    "karte": (240, 320, 80),
    "avatar": (128, 128, 80),
}

_BILD_ID = re.compile(r"^[0-9a-f]{32}$")

# Pillow warnt erst ab MAX_IMAGE_PIXELS und bricht ab dem Doppelten ab — wir
# prüfen selbst vor dem Dekodieren und lassen Pillow als zweite Linie stehen.
Image.MAX_IMAGE_PIXELS = MAX_PIXEL


class BildFehler(Exception):
    def __init__(self, status_code: int, detail: str):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


def ist_gueltige_bild_id(bild_id: str | None) -> bool:
    return bool(bild_id) and bool(_BILD_ID.match(bild_id))


def _verzeichnis() -> Path:
    pfad = Path(settings.bilder_path)
    pfad.mkdir(parents=True, exist_ok=True)
    return pfad


def pfad(bild_id: str, variante: str) -> Path | None:
    """Dateipfad einer Variante — None bei ungültiger ID/Variante (kein Path-Traversal)."""
    if not ist_gueltige_bild_id(bild_id) or variante not in VARIANTEN:
        return None
    return _verzeichnis() / f"{bild_id}_{variante}.webp"


def _normiere_fokus(fokus_y: float | None) -> float:
    if fokus_y is None:
        return STANDARD_FOKUS_Y
    return min(1.0, max(0.0, float(fokus_y)))


def _oeffne(daten: bytes) -> Image.Image:
    max_bytes = settings.bild_max_upload_mb * 1024 * 1024
    if len(daten) > max_bytes:
        raise BildFehler(413, f"Bild zu groß (max. {settings.bild_max_upload_mb} MB)")
    try:
        img = Image.open(BytesIO(daten))
    except (UnidentifiedImageError, OSError):
        raise BildFehler(400, "Keine gültige Bilddatei (erlaubt: JPEG, PNG, WebP, GIF)")
    if img.format not in ERLAUBTE_FORMATE:
        raise BildFehler(400, "Bildformat nicht unterstützt (erlaubt: JPEG, PNG, WebP, GIF)")
    breite, hoehe = img.size
    if breite * hoehe > MAX_PIXEL:
        raise BildFehler(400, "Bild hat zu viele Pixel (max. 40 Megapixel)")
    try:
        img.seek(0)  # GIF: nur der erste Frame
        img.load()
    except (Image.DecompressionBombError, OSError):
        raise BildFehler(400, "Bilddatei ist beschädigt oder zu groß")
    img = ImageOps.exif_transpose(img)

    # Transparenz auf Weiß legen — WebP könnte Alpha, aber PDF/Druck sind einfacher ohne
    if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
        rgba = img.convert("RGBA")
        hintergrund = Image.new("RGB", rgba.size, (255, 255, 255))
        hintergrund.paste(rgba, mask=rgba.getchannel("A"))
        img = hintergrund
    else:
        img = img.convert("RGB")

    if img.width < MIN_BREITE or img.height < MIN_HOEHE:
        raise BildFehler(400, f"Bild zu klein (mindestens {MIN_BREITE} × {MIN_HOEHE} Pixel)")
    return img


def _auf_3_zu_4(img: Image.Image) -> Image.Image:
    """Mittiger 3:4-Zuschnitt — das Frontend schneidet schon zu, Importe evtl. nicht."""
    b, h = img.size
    if b * 4 > h * 3:  # zu breit
        neue_b = h * 3 // 4
        links = (b - neue_b) // 2
        return img.crop((links, 0, links + neue_b, h))
    neue_h = b * 4 // 3
    oben = (h - neue_h) // 2
    return img.crop((0, oben, b, oben + neue_h))


def _webp(img: Image.Image, qualitaet: int) -> bytes:
    puffer = BytesIO()
    # Ohne exif=… speichert Pillow keine Metadaten (GPS aus Handyfotos fällt weg)
    img.save(puffer, "WEBP", quality=qualitaet, method=4)
    return puffer.getvalue()


def _avatar(portraet: Image.Image, fokus_y: float) -> Image.Image:
    seite = portraet.width
    oben = round(fokus_y * (portraet.height - seite))
    quadrat = portraet.crop((0, oben, seite, oben + seite))
    b, h, _ = VARIANTEN["avatar"]
    return quadrat.resize((b, h), Image.LANCZOS)


def erzeuge_varianten(daten: bytes, fokus_y: float | None = None) -> dict[str, bytes]:
    """Prüft einen Upload und liefert alle Varianten als WebP-Bytes."""
    portraet = _auf_3_zu_4(_oeffne(daten))
    fokus = _normiere_fokus(fokus_y)

    ergebnis = {}
    for variante in ("gross", "karte"):
        b, h, q = VARIANTEN[variante]
        # Nicht hochskalieren: kleinere Porträts behalten ihre Größe
        if portraet.width > b:
            bild = portraet.resize((b, h), Image.LANCZOS)
        else:
            bild = portraet
        ergebnis[variante] = _webp(bild, q)
    ergebnis["avatar"] = _webp(_avatar(portraet, fokus), VARIANTEN["avatar"][2])
    return ergebnis


def neuer_avatar(bild_id: str, fokus_y: float | None) -> bytes:
    """Avatar aus der gespeicherten gross-Variante mit neuem Fokus berechnen."""
    quelle = lade(bild_id, "gross")
    if quelle is None:
        raise BildFehler(404, "Bild nicht gefunden")
    portraet = Image.open(BytesIO(quelle)).convert("RGB")
    return _webp(_avatar(portraet, _normiere_fokus(fokus_y)), VARIANTEN["avatar"][2])


def speichere(varianten: dict[str, bytes], bild_id: str | None = None) -> str:
    """Schreibt die Varianten; ohne bild_id wird eine neue erzeugt."""
    bild_id = bild_id or uuid.uuid4().hex
    for variante, inhalt in varianten.items():
        ziel = pfad(bild_id, variante)
        tmp = ziel.with_suffix(".tmp")
        tmp.write_bytes(inhalt)
        tmp.replace(ziel)
    return bild_id


def lade(bild_id: str | None, variante: str = "gross") -> bytes | None:
    ziel = pfad(bild_id or "", variante)
    if ziel is None or not ziel.is_file():
        return None
    return ziel.read_bytes()


def loesche(bild_id: str | None) -> None:
    if not ist_gueltige_bild_id(bild_id):
        return
    for variante in VARIANTEN:
        ziel = pfad(bild_id, variante)
        if ziel is not None:
            ziel.unlink(missing_ok=True)


def belegter_speicher(bild_ids) -> int:
    """Summe der Dateigrößen aller Varianten der übergebenen Bilder (Bytes)."""
    summe = 0
    for bild_id in bild_ids:
        for variante in VARIANTEN:
            ziel = pfad(bild_id or "", variante)
            if ziel is not None and ziel.is_file():
                summe += ziel.stat().st_size
    return summe


def pruefe_kontingent(belegt: int, neu: dict[str, bytes]) -> None:
    grenze = settings.bild_kontingent_mb * 1024 * 1024
    if belegt + sum(len(v) for v in neu.values()) > grenze:
        raise BildFehler(
            409, f"Speicherkontingent für Bilder erschöpft (max. {settings.bild_kontingent_mb} MB)"
        )


def raeume_waisen_auf(bekannte_ids: set[str], min_alter_s: int = 3600) -> int:
    """Löscht Dateien, deren bild_id keinem Charakter gehört und die älter als
    min_alter_s sind (frische Uploads laufen evtl. noch). Gibt die Anzahl zurück."""
    grenze = time.time() - min_alter_s
    geloescht = 0
    for datei in _verzeichnis().iterdir():
        bild_id = datei.name.split("_", 1)[0]
        if bild_id in bekannte_ids:
            continue
        try:
            if datei.stat().st_mtime < grenze:
                datei.unlink()
                geloescht += 1
        except OSError:
            pass
    return geloescht
