# Savage Worlds Web — Roadmap

Stand: 2026-07-02 · Abgleich mit dem Original (Kivy): https://github.com/Thallion/Savage-Worlds-Charakter-Generator-deutsch

## Status quo

Web-Port des Kivy-Charakter-Generators. Architektur:

- **Backend:** FastAPI + SQLAlchemy + SQLite. Der komplette Charakter liegt als JSON-Dokument (`charakter_daten`) auf der `Charakter`-Zeile. Die Spielregeln sind **zustandslose** Endpoints unter `/api/spiellogik/...`: Charakter-JSON rein, Regel anwenden, geändertes JSON zurück. Gespeichert wird separat über `PUT /api/charaktere/{id}`.
- **Spieldaten:** `backend/gamelogic/settings/*.json` (ein File pro Setting, Dateiname = Setting-Name) und `backend/gamelogic/config/*.json` (settingunabhängige Basis).
- **Frontend:** Vue 3 + Vuetify 3 + Pinia. Editor-Tabs unter `frontend/src/components/charakter/`, generische Store-Methode `spiellogikAktion(aktion, elementName)`.

## Erledigt

- [x] Registrierung / Login (JWT), Charakterliste, Charakter anlegen/speichern/löschen
- [x] Editor-Tabs: Profil, Volk, Eigenschaften, Handicaps, Talente, Mächte, Übersicht
- [x] **Eigenschaften-Initialisierung** — Attribute, Fertigkeiten und Punkte aus Setting + `eigenschaften_config.json` (`app/services/charakter_init.py`); Lazy-Init für Bestandscharaktere
- [x] **Abgeleitete Werte über `/spiellogik/berechne`** — Talent-/Handicap-Effekte aus `abgeleitete_effekte.json` (additiv, `nicht_kumulativ_gruppe` = Maximum, Stufen-Suffixe `_leicht`/`_schwer`), Volk-Boni, Größe, Bennys, Machtpunkte; Parade regelkonform 2 bei ungelerntem Kämpfen
- [x] **Volk-Effekte** (`app/services/volk_effekte.py`) — Attribut-Boni, Fertigkeits-Startboni, Auto-Talente/-Handicaps, freies Talent (als Talent-Slot); Snapshot macht Volk-Wechsel exakt rückgängig
- [x] **Handicap-Punkte-Ökonomie** — max. 4 Punkte, korrekte Buchhaltung; Einlösen: 2 P → Attributssteigerung, 1 P → Fertigkeitspunkt, 2 P → Talent-Slot
- [x] **Talent-Voraussetzungen + Talent-Ökonomie** (`app/services/talent_voraussetzungen.py`) — Parser für `WIL W8`, `Kämpfen W6`, `Athletik oder Schießen W8`, `AH`, Talent-Namen; Rang-Sperre bei Erschaffung (nur Anfänger); Talente kosten einen Slot (Handicap-Punkte oder freies Volks-Talent)
- [x] **Mächte** — `macht/waehlen|entfernen`; Slots und Machtpunkte aus AH-Talenten (`neue_maechte`/`machtpunkte`, inkl. „Neue Mächte"/„Machtpunkte"); MaechteTab nur bei arkanem Hintergrund sichtbar
- [x] **Setting-Wechsel** — `setting/wechseln` re-initialisiert Eigenschaften und Auswahl über `initialisiere_charakter_daten`, Profil bleibt erhalten; Bestätigungsdialog im ProfilTab
- [x] **Backend-Tests** — pytest, 44 Tests (`backend/tests/`); dabei behobener Regelbug: Fertigkeit über Attribut kostete 1 statt 2 Punkte
- [x] Regelbug behoben: Handicap-Punkte wurden beim Wählen überschrieben statt addiert

## Geplante Schritte (nach Nutzwert sortiert)

Abgleich mit der Geschäftslogik des Originals (`functions/`-Module):

### 1. Volk-Wahlmöglichkeiten vervollständigen (Original: `volk_wahlmoeglichkeiten.py`)

Freies Talent ist als Slot umgesetzt; es fehlen: **freies Attribut** (`wahlmoeglichkeiten.freies_attribut` → W4→W6 nach Wahl), **Attribut-Schwäche** (Malus-Wahl) und **Magieaffin** (AH-Wahl + Fertigkeits-Boost). Benötigt UI-Dialog nach Volk-Auswahl im VoelkerTab.

### 2. Spezial-Handicap-Effekte (Original: `handicap_funktionen.py`)

„Alt" (schwer): +5 Fertigkeitspunkte; „Jung": reduzierte Attributs-/Fertigkeitspunkte (4/10 bzw. 3/10); „Arm": halbes Startgeld. Datengetrieben analog `abgeleitete_effekte.json` umsetzen (neue Config oder Erweiterung).

### 3. Talent-Auto-Effekte (Original: `talent_funktionen.py`)

Talente tragen `auto_handicaps`/`auto_talente`/`auto_maechte` (z. B. AH (Gaben) → Auto-Handicap); Spezialfälle wie „Berserker" (+1 Stärke-Stufe). Beim Wählen anwenden, beim Entfernen zurücknehmen (Snapshot-Muster von `volk_effekte.py` wiederverwenden).

### 4. Kompatibilitätsprüfung (Original: `kompatibilitaets_pruefung.py`)

Verbotene Kombinationen (z. B. „Reich" + „Arm") beim Wählen von Talenten/Handicaps ablehnen.

### 5. Export/Import im Frontend

Export-Button (`GET /api/charaktere/{id}/export` existiert); neuer `POST /api/charaktere/import` mit `ergaenze_fehlende_eigenschaften` als Normalisierung — macht auch Kivy-Alt-Exporte importierbar.

### 6. Ausrüstung & Startgeld (Original: `ausruestung_funktionen.py`)

Ausrüstungs-Tab (Daten liegen bereits in `setting["ausruestung"]`), Startgeld pro Setting (`setting["startgeld"]`), Einlösung 1 Handicap-Punkt → Startgeld, Traglast (Stärke × 10 kg), Rüstung fließt in Robustheit ein.

### 7. Aufstiege & Rang nach der Erschaffung (Original: `character_advancement.py`)

`char_gen_completed` abschließen; Aufstiege kaufen (1 Aufstieg = Attribut/Fertigkeit×2/Talent/Macht), Rang aus ausgegebenen Aufstiegen (Anfänger→Legendär) — schaltet höherrangige Talente/Mächte frei (Rang-Prüfung existiert bereits).

### 8. Setting-Spezialsysteme

Cyberware inkl. Stress (SciFi-Kompendium, `cyberware_funktionen.py` + `cyberware_config.json`), Superkräfte (Superkräfte-Kompendium, `superkraft_funktionen.py`).

### 9. Statblock-Export (Original: `statblock_generator.py`)

Charakter als Text-/PDF-Statblock exportieren.

### Begleitend: Tests ausbauen

Runner: `cd backend && .venv/bin/python -m pytest tests/`. Bei jedem Schritt mitwachsen lassen; offen: Auth-/Charaktere-Endpoints (Test-DB), Frontend-Tests.

## Reihenfolge-Begründung

1–4 machen die Erschaffung regelkonform und vervollständigen die Kern-Geschäftslogik des Originals; 5–7 erweitern den Spielzyklus (Export, Ausrüstung, Aufstiege); 8–9 sind settingspezifischer Komfort.
