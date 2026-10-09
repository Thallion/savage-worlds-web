# Konzept: Charakterbilder (Porträts)

Stand: 2026-10-09 · Status: **umgesetzt** (Abweichungen vom ersten Entwurf sind unten eingearbeitet)

Jeder Charakter kann **ein** Porträt bekommen, **nur mit Konto** (Entscheidung: kein Upload im Gastmodus, das ist auch ein Anreiz zur Registrierung). Es erscheint in der Charakterliste
(auch in Ordnern), in der Kopfzeile des Editors, im Profil-Tab, in der Übersicht, auf dem
Charakterbogen (HTML + PDF) und im Kampfsimulator.

---

## 1. Grundsatzentscheidungen

| Frage | Entscheidung | Begründung |
|---|---|---|
| Bild im `charakter_daten`-Blob? | **Nein** | Jede Spiellogik-Aktion schickt den ganzen Blob hin und zurück (`spiellogikAktion` + `/berechne`), und die Undo-Historie hält bis zu 50 Kopien davon im Speicher. 100–200 KB Base64 pro Aktion wären spürbar, auf dem Pi und im Mobilfunknetz erst recht. |
| Bild als BLOB in SQLite? | **Nein** | Bläht `chargen.db` auf und verlangsamt Backups. Die Bytes sind außerdem schlecht cachebar. |
| Bild als Datei auf dem Volume | **Ja** | `data/bilder/` liegt im vorhandenen Docker-Volume `./data`, überlebt also Updates wie `data/settings/`. Nginx/Browser können es aggressiv cachen. |
| Ein Bild pro Charakter | **Ja** | Das deckt den Bedarf ab. Ein Ersetzen erzeugt eine neue Datei-ID, das alte Bild wird gelöscht. |
| Zuschnitt | **im Browser, fest 3:4 (Hochformat)** | Das klassische Porträtformat passt in den Charakterbogen und auf Karten. Der Server schneidet nichts mehr zu, er skaliert nur und kodiert neu. |
| Speicherformat | **WebP** | Etwa 30 % kleiner als JPEG, wird von allen aktuellen Browsern angezeigt und von reportlab (über Pillow) gelesen. |

---

## 2. Formatvorgaben & Größen

### Upload (Eingabe)

- **Erlaubte Typen:** JPEG, PNG, WebP und GIF (nur der erste Frame). Geprüft wird über
  den Bildinhalt mit Pillow, **nicht** über die Endung oder den Content-Type.
- **Nicht unterstützt:** SVG (XSS-Risiko) und HEIC/AVIF (Pillow kann sie ohne Plugin nicht lesen).
  iPhones liefern beim Upload über den Browser ohnehin JPEG.
- **Maximale Dateigröße:** 8 MB pro Upload (Server). Das Frontend skaliert vorher herunter,
  der echte Upload liegt deshalb meist unter 500 KB.
- **Maximale Pixelzahl:** 40 MP (`Image.MAX_IMAGE_PIXELS`), Schutz gegen Decompression-Bombs.
- **Mindestgröße:** 200 × 266 px. Kleinere Bilder werden mit Hinweis abgelehnt, weil sie
  im Bogen pixelig aussehen.

### Gespeicherte Varianten (Ausgabe)

Der Server erzeugt beim Upload drei Varianten. Alle sind WebP, EXIF wird entfernt
(GPS-Daten aus Handyfotos!) und die Ausrichtung vorher mit `ImageOps.exif_transpose`
angewendet.

| Variante | Maße (B×H) | Qualität | ≈ Größe | Verwendung |
|---|---|---|---|---|
| `gross` | 600 × 800 | 85 | 60–120 KB | Profil-Tab, Übersicht, Charakterbogen (HTML/PDF) |
| `karte` | 240 × 320 | 80 | 12–25 KB | Charakterkarte in Liste/Ordner |
| `avatar` | 128 × 128 (Quadrat) | 80 | 4–8 KB | Editor-Kopfzeile, Ordner-Kopf, Kampfsimulator |

- Bilder, die kleiner als die Zielgröße sind, werden **nicht** hochskaliert, aber auf 3:4 gebracht.
- **Avatar-Zuschnitt:** ein Quadrat aus dem 3:4-Bild, horizontal zentriert. Die
  vertikale Position kommt aus `fokus_y` (0–1, Standard 0.2, weil Gesichter meist im
  oberen Drittel liegen). `fokus_y` legt der Zuschneide-Dialog fest (siehe 5.3).
- **600 × 800 reicht für den Druck:** Im PDF ist das Bild 35 × 46,7 mm groß, das entspricht etwa 435 dpi.

### Kontingent

- Pro Konto **max. 50 MB** (Summe aller Varianten, ca. 300–500 Porträts). Bei 1 Bild pro
  Charakter ist das praktisch nur eine Missbrauchsbremse.
- Beides ist per Env-Var einstellbar: `CHARGEN_BILD_MAX_UPLOAD_MB`, `CHARGEN_BILD_KONTINGENT_MB`.

---

## 3. Speicherkonzept (Backend)

### 3.1 Ablage auf der Platte

```
data/
├── chargen.db
├── settings/
└── bilder/
    ├── <bild_id>_gross.webp
    ├── <bild_id>_karte.webp
    └── <bild_id>_avatar.webp
```

Flach statt `bilder/<user_id>/`: Der Abruf kennt nur die `bild_id` (siehe 3.3). Die Zuordnung zum
Konto steht in der DB (`charaktere.bild_id`), Kontingent und Konto-Löschung laufen darüber.

- `bild_id` = `uuid4().hex` (128 Bit, nicht erratbar).
- Neues Setting in `app/config.py`: `bilder_path: Path = Path("data") / "bilder"`.
  Das Verzeichnis wird beim Start angelegt, wie bei `custom_settings_path`.
- Pfad-Sicherheit: `bild_id` wird per Regex `^[0-9a-f]{32}$` validiert, bevor ein Pfad
  daraus gebaut wird (kein Path-Traversal).

### 3.2 Datenbank

Eine neue, nullable Spalte am `Charakter` reicht, eine eigene Tabelle ist nicht nötig:

```python
# app/db/models.py — Charakter
bild_id = Column(String(32), nullable=True)      # None = kein Porträt
bild_fokus_y = Column(Float, nullable=True)       # optional, nur für Avatar-Neuberechnung
```

Weil es kein Alembic gibt, kommt die Migration als kleiner idempotenter Startup-Check
(`ALTER TABLE charaktere ADD COLUMN bild_id VARCHAR(32)`, wenn die Spalte fehlt), damit die
Prod-DB auf dem Pi nicht gelöscht werden muss.

**Warum am Charakter und nicht im Blob:** Das Bild gehört zur Server-Zeile (Besitzer,
Löschen, Kontingent). Die Spiellogik interessiert sich nicht dafür, Undo/Redo soll es
nicht anfassen, und der JSON-Export soll nicht auf eine fremde Server-Datei verweisen.

### 3.3 Auslieferung: Bild-URLs ohne Auth-Header

Problem: `<img src>` kann keinen `Authorization: Bearer`-Header mitschicken, und der Token
liegt im `localStorage` (siehe `api/client.ts`).

Lösung: **Capability-URLs**. Die nicht erratbare `bild_id` *ist* die Berechtigung:

```
GET /api/bilder/<bild_id>/<variante>.webp      (ohne Login)
→ Cache-Control: public, max-age=31536000, immutable
```

- Die ID taucht nur in Antworten an den Besitzer auf (Charakterliste/Detail). Es gibt keine
  Auflistung, die Antwort ist immer 404 bei unbekannter ID oder Variante.
- Weil jedes Ersetzen eine neue ID erzeugt, ist `immutable` gefahrlos (Cache-Busting über die ID).
- Optional später: Nginx liefert `data/bilder` direkt aus (`location /api/bilder/`), statt
  den Weg über FastAPI zu gehen. Für den Anfang reicht `FileResponse`.
- Alternative mit echter Prüfung (Blob per `fetch` laden + `URL.createObjectURL`) wäre
  aufwendiger und nicht cachebar. Für Charakterporträts ist das nicht angemessen.

### 3.4 API-Endpunkte

Neuer Router `app/api/bilder.py`, außerdem eine Erweiterung von `charaktere.py`:

| Methode | Route | Auth | Beschreibung |
|---|---|---|---|
| `PUT` | `/api/charaktere/{id}/bild` | ✔ | `multipart/form-data` mit `datei` und optional `fokus_y`. Prüfen, Varianten erzeugen, altes Bild löschen, `bild_id` setzen. Antwort: `CharakterDetail`. |
| `PATCH` | `/api/charaktere/{id}/bild` | ✔ | Nur `fokus_y` ändern, der Avatar wird aus `gross` neu berechnet. Alle Varianten bekommen eine neue ID, damit kein gecachter Avatar stehen bleibt. |
| `DELETE` | `/api/charaktere/{id}/bild` | ✔ | Dateien löschen, `bild_id = NULL`. |
| `GET` | `/api/bilder/{bild_id}/{variante}.webp` | – | Ausliefern (siehe 3.3). |

`python-multipart` steht schon in `requirements.txt`. Pillow kommt als Abhängigkeit von reportlab
mit, gehört aber explizit in die requirements (`pillow>=10`).

Die Verarbeitung landet in `app/services/charakterbild.py`:
`verarbeite_upload(bytes, fokus_y) -> dict[variante, bytes]`, `speichere(...)`, `loesche(...)`,
`belegter_speicher(user_id)`.

### 3.5 Schemas

```python
# schemas/charakter.py — CharakterResponse & CharakterListItem
bild_id: str | None = None
```

Das Frontend baut die URLs selbst, so bleiben die Schemas schlank:
`/api/bilder/${bild_id}/karte.webp`.

### 3.6 Lebenszyklus & Aufräumen

| Ereignis | Verhalten |
|---|---|
| Charakter löschen | Dateien in `delete_charakter` löschen (nach dem Commit). |
| Konto löschen | Alle `bild_id`s der Charaktere des Kontos löschen. |
| Bild ersetzen | Neue ID schreiben → DB committen → alte Dateien löschen. |
| Archetyp duplizieren | Kein Bild (Archetypen haben keins). |
| Waisen (z. B. Absturz zwischen Schreiben und Commit) | Aufräumjob beim Start: Dateien, deren ID in keiner `charaktere.bild_id` vorkommt und die älter als 1 h sind, werden gelöscht. |

### 3.7 Export / Import

- **JSON-Export** (`GET /charaktere/{id}/export`): optional mit eingebettetem Bild unter einem
  reservierten Top-Level-Key:
  ```json
  { "...": "charakter_daten wie bisher",
    "_portraet": { "mime": "image/webp", "fokus_y": 0.2, "daten": "<base64 der Variante gross>" } }
  ```
  Steuerung über den Query-Parameter `?mit_bild=true` (Standard: true). Ohne Bild bleibt die Datei
  Kivy-kompatibel, unbekannte Keys sind dort ohnehin egal.
- **Import:** `_portraet` wird vor `ergaenze_fehlende_eigenschaften` aus dem Dict entfernt
  und durch dieselbe Upload-Pipeline geschickt (mit derselben Validierung, also keine
  ungeprüften Bytes).
- **Gast → Konto:** entfällt, Gäste haben keine Bilder.

---

## 4. Gastmodus (ohne Konto)

**Kein Upload.** Gast-Charaktere zeigen überall den Initialen-Platzhalter. Im Profil-Tab steht an
der Stelle der Upload-Buttons der Hinweis „Porträts gibt es mit Konto“. Damit entfallen
IndexedDB-Speicherung, Browser-seitige Variantenerzeugung und die Bildübernahme beim Login.

## 5. Einbindung im Frontend

### 5.1 Gemeinsame Komponenten

- **`components/charakter/CharakterPortraet.vue`**: Anzeige mit den Props `charakter`,
  `variante` (`gross|karte|avatar`) und `groesse`. Hat kein Charakter ein Bild, zeigt sie einen
  Platzhalter: die **Initialen** des Namens auf einer Farbe, die aus dem Setting-Namen
  gehasht wird. Charaktere eines Settings sehen so gleichfarbig aus, und die Liste wirkt
  auch ohne Bilder ordentlich.
- **`components/charakter/BildHochladenDialog.vue`**: Upload- und Zuschneide-Dialog (siehe 5.3).

### 5.2 Einbindungsorte

| # | Ort | Datei | Variante | Darstellung |
|---|---|---|---|---|
| 1 | **Charakterliste & Ordner-Übersicht**, Karte | `CharakterKarte.vue` | `karte` | Bild links als 72 × 96 px (3:4), Titel/Setting/Chip rechts daneben. Auf schmalen Bildschirmen (< 400 px) 54 × 72 px. Die Karte bleibt so niedrig wie heute, statt ein großes Cover-Bild zu bekommen. |
| 2 | **Ordner-Kopf** (Expansion-Panel-Titel) | `CharakterListeView.vue` | `avatar` | Bis zu 4 überlappende runde Avatare (32 px) der enthaltenen Charaktere, danach „+N“. So erkennt man den Ordner auch zugeklappt. |
| 3 | **Editor-Kopfzeile** | `CharakterEditorView.vue` | `avatar` | Rundes 48-px-Avatar links neben dem Namen. Klick springt zum Profil-Tab. |
| 4 | **Profil-Tab** (Bild pflegen) | `ProfilTab.vue` | `gross` | Eigene Spalte: Porträt 3:4, 200 px breit, darunter die Buttons *Bild hochladen / Ausschnitt ändern / Entfernen*. Drag & Drop auf die Fläche und Einfügen aus der Zwischenablage (Strg+V) öffnen den Upload-Dialog. Layout: `md=3` Bild + `md=9` bestehende Felder (die heutigen zwei Spalten werden zu zwei Spalten innerhalb der 9). Mobil steht das Bild oben und zentriert. |
| 5 | **Übersicht-Tab** | `UebersichtTab.vue` | `gross` | Porträt 160 px breit neben Name, Konzept und Rang im Kopfbereich. |
| 6 | **Charakterbogen HTML** | `services/charakterbogen.py` (`_kopf_sektion`) | `gross` | Rechts im Kopf, 35 × 46,7 mm, 1 px Rahmen in Bandfarbe. **Als Data-URL eingebettet**, weil das HTML als eigenständige Datei heruntergeladen wird. Druckfreundliche Variante: `filter: grayscale(1)`. |
| 7 | **Charakterbogen PDF** | `services/charakterbogen_pdf.py` (`_kopf`) | `gross` | Kopf als zweispaltige Tabelle: links Icons/Name/Untertitel, rechts das Bild (35 × 46,7 mm) mit Rahmen `band_rand`. Druckfreundlich: in Pillow nach Graustufen konvertieren (`ImageOps.grayscale`), spart Toner. Ohne Bild bleibt der Kopf exakt wie heute. |
| 8 | **Kampfsimulator** | `KampfsimulatorView.vue` | `avatar` | Rundes 28-px-Avatar vor dem Namen in Teilnehmerliste und Initiativreihenfolge (`Kaempfer.bildId`), nur für Teilnehmer aus der Quelle „Charakter“. Kreaturen und Archetypen bekommen ein Icon wie bisher. |
| – | Text-Statblock | – | – | Kein Bild (reiner Text). |

### 5.3 Upload- & Zuschneide-Dialog

Ablauf:

1. **Quelle wählen:** Datei auswählen, per Drag & Drop oder aus der Zwischenablage einfügen.
   `accept="image/jpeg,image/png,image/webp,image/gif"`.
2. **Vorprüfung im Browser:** Typ und Größe (≤ 20 MB roh, weil es danach herunterskaliert
   wird). Bei Fehlern gibt es eine verständliche Meldung statt eines Uploads.
3. **Zuschneiden:** fester 3:4-Rahmen, Bild darin verschieben und zoomen (Maus, Mausrad,
   Touch-Pinch, Slider). Eigener Canvas-Cropper, ohne Zusatzbibliothek.
4. **Avatar-Fokus:** Ein gestrichelter Kreis im Zuschnitt zeigt den Avatar-Ausschnitt. Ein Slider
   verschiebt ihn vertikal (`fokus_y`), Live-Vorschau von Karte und Avatar daneben.
5. **Im Browser herunterskalieren:** Der Ausschnitt wird auf max. 1200 × 1600 gebracht und als WebP
   (Qualität 0.9) per `canvas.toBlob` erzeugt. Das spart Upload und Server-CPU auf dem Pi.
6. **Speichern:**
   - `PUT /api/charaktere/{id}/bild` (multipart). Wurde bei „Ausschnitt ändern“ nur der
     Avatar-Fokus bewegt, genügt ein `PATCH`.
7. „Ausschnitt ändern“ öffnet den Dialog erneut mit dem Bild `gross` als Quelle. Das Original
   wird **nicht** aufgehoben, ein Nachzoomen ist dann nur innerhalb von 600 × 800 möglich.
   Dieser Kompromiss spart Speicher.

**Unabhängig von „Speichern“:** Der Bild-Upload wird sofort wirksam, nicht erst beim
`speichereCharakter()`. Er gehört nicht zum Blob und ist nicht Teil von Undo/Redo. Im
Profil-Tab steht ein kleiner Hinweis „Bild wird sofort gespeichert“. Ist der Charakter
noch nie gespeichert worden, gibt es dieses Problem nicht: Server-Charaktere haben ab
Anlage eine ID.

### 5.4 Typen & Store

- `types/charakter.ts`: `bild_id?: string | null` an `CharakterListItem`/`CharakterDetail`.
- `stores/charakter.ts`: `ladeBildHoch(id, blob, fokusY)`, `setzeBildFokus(id, fokusY)` und
  `entferneBild(id)`. Sie aktualisieren `aktuellerCharakter` und den Listeneintrag.
- `api/client.ts`: braucht eine Variante für `FormData`. Dabei **keinen** `Content-Type`
  setzen, die Multipart-Boundary setzt der Browser.

### 5.5 Charakterbogen-Requests (zustandslos bleiben)

`/spiellogik/charakterbogen[/pdf]` arbeiten heute nur auf `charakter_daten`. Erweiterung in
`CharakterbogenRequest`:

```python
bild_id: str | None = None        # Backend liest data/bilder/... selbst
```

Der Endpoint bleibt so ohne DB-Zugriff. `bild_id` ist dieselbe Capability wie die
öffentliche URL, es entsteht also kein zusätzliches Rechteproblem.

---

## 6. Infrastruktur & Betrieb

- **nginx.conf:** `client_max_body_size 10m;` im Block `location /api/` setzen, der
  Nginx-Standard von **1 MB** würde Uploads sonst mit 413 abweisen. Optional ein eigenes
  Limit für den Upload-Pfad (`limit_req zone=upload rate=10r/m`).
- **Cloudflare-Tunnel:** 100-MB-Limit pro Request, also unkritisch. Cloudflare cacht
  `/api/*` standardmäßig nicht. Wer die Bilder am Edge cachen will, braucht eine Cache-Rule
  für `/api/bilder/*`, die `immutable` passt dazu.
- **Backup:** Neben `chargen.db` jetzt auch `data/bilder/` sichern (in `deploy.sh`/README erwähnen).
- **Pi-Last:** Varianten erzeugen kostet bei 1200 × 1600 Eingabe auf einem Pi 4 etwa 0,3–0,5 s.
  Das läuft synchron im Request, eine Queue ist nicht nötig.

## 7. Datenschutz & Recht

- **Datenschutzerklärung** (`DatenschutzView.vue`) ergänzen: Hochgeladene Bilder werden auf dem
  Server gespeichert, EXIF/Metadaten werden entfernt, Löschung mit Charakter bzw. Konto,
  keine Bilder im Gastmodus.
- **Hinweis im Upload-Dialog:** „Lade nur Bilder hoch, an denen du die Rechte hast. Bilder sind
  über einen geheimen Link abrufbar, aber nicht öffentlich gelistet.“
- Es gibt keine öffentliche Galerie und keine Weitergabe. Eine Moderation ist deshalb vorerst
  nicht nötig.

## 8. Tests

- `tests/test_charakterbild.py`:
  - Gültiges JPEG/PNG/WebP → drei Varianten mit den richtigen Maßen, ohne EXIF.
  - SVG, Textdatei mit `.jpg`-Endung, zu große Datei, Decompression-Bomb → 400/413.
  - Fremder Charakter → 404, Kontingent überschritten → 409.
  - Ersetzen löscht die alten Dateien, Charakter/Konto löschen räumt auf.
  - Export mit `_portraet` → Import erzeugt ein neues Bild mit neuer ID.
- PDF/HTML-Bogen mit und ohne Bild (Smoke-Test: Erzeugung wirft nicht, Bild-Tag/Flowable vorhanden).

## 9. Umsetzung (erledigt)

1. Backend-Kern: Config, DB-Spalten `bild_id`/`bild_fokus_y` + Startup-Migration (`main.py`),
   `services/charakterbild.py`, `api/bilder.py`, Bild-Endpunkte in `api/charaktere.py`, Aufräumen
   bei Löschen, `tests/test_charakterbild.py`. Dazu nginx `client_max_body_size 10m`.
2. Frontend-Basis: `CharakterPortraet.vue` (mit Platzhalter), `utils/charakterBild.ts`, Typen,
   Store (`ladeBildHoch`/`setzeBildFokus`/`entferneBild`), `api.putForm`/`api.patch`.
3. Upload-Dialog `BildHochladenDialog.vue` im Profil-Tab.
4. Charakterbogen HTML + PDF (inkl. Graustufen-Variante).
5. Export/Import mit `_portraet`.
6. Ordner-Kopf-Avatare, Übersicht-Tab, Editor-Kopf, Kampfsimulator, Datenschutztext.

## 10. Offene Punkte

- Sollen Archetypen / eigene Settings später Standardbilder mitbringen können (z. B. pro Volk)?
- Soll das Original zusätzlich aufbewahrt werden, damit sich später ohne Qualitätsverlust neu
  zuschneiden lässt? Das kostet etwa das 5- bis 10-fache an Speicher.
- Nginx könnte `data/bilder` direkt ausliefern (Volume auch in den nginx-Container mounten), statt
  über FastAPI zu gehen. Bei der aktuellen Last ist das nicht nötig.
