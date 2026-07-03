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
- [x] **Handicap-Punkte-Ökonomie** — max. 4 Punkte, korrekte Buchhaltung; Einlösen: 2 P → Attributssteigerung, 1 P → Fertigkeitspunkt; Talente kosten wie im Original direkt 2 P beim Wählen (Zahlungsquellen-Journal `talent_zahlungen` für korrekte Erstattung)
- [x] **Talent-Voraussetzungen + Talent-Ökonomie** (`app/services/talent_voraussetzungen.py`) — Parser für `WIL W8`, `Kämpfen W6`, `Athletik oder Schießen W8`, `AH`, Talent-Namen; Rang-Sperre bei Erschaffung (nur Anfänger); Rang-/Voraussetzungs-Ablehnungen per „Trotzdem auswählen" überspringbar (`ignoriere_pruefungen`, Bestätigungsdialog in Talente-/Mächte-Tab)
- [x] **Mächte** — `macht/waehlen|entfernen`; Slots und Machtpunkte aus AH-Talenten (`neue_maechte`/`machtpunkte`, inkl. „Neue Mächte"/„Machtpunkte"); MaechteTab nur bei arkanem Hintergrund sichtbar
- [x] **Setting-Wechsel** — `setting/wechseln` re-initialisiert Eigenschaften und Auswahl über `initialisiere_charakter_daten`, Profil bleibt erhalten; Bestätigungsdialog im ProfilTab
- [x] **Volk-Wahlmöglichkeiten (Kern)** — `volk/wahl`-Endpoint: freies Attribut (+1 Würfeltyp), Talent-oder-Attribut (Halbelf), Talent-oder-2-Fertigkeitspunkte (Anari), Stärke-oder-Konstitution (Halbork); Wahl wechselbar, Volk-Wechsel nimmt sie zurück; Auswahl-Karte im VoelkerTab
- [x] **Spezial-Handicap-Effekte** (`app/services/handicap_effekte.py`) — „Alt" (schwer) +5 Fertigkeitspunkte, „Jung" reduzierte Steigerungen (delta-basiert aus `handicap_config.json`, ausgegebene Punkte bleiben erhalten); Bewegungsweiten-Mali laufen weiter über `abgeleitete_effekte.json`
- [x] **Talent-Auto-Effekte** (`app/services/talent_effekte.py`) — `auto_handicaps`/`auto_talente`/`auto_maechte` ohne Punkte/Slots (z. B. AH (Verdorbener) → „Verderbnis"), Berserker +1 Stärke-Würfeltyp, `effekt.attribut_bonus` (Deadlands), Rohling/Naturgespür-Attributlink; Snapshot in `talent_effekte`, Auto-Elemente nicht manuell entfernbar
- [x] **Backend-Tests** — pytest, 75 Tests (`backend/tests/`); dabei behobener Regelbug: Fertigkeit über Attribut kostete 1 statt 2 Punkte
- [x] Regelbug behoben: Handicap-Punkte wurden beim Wählen überschrieben statt addiert
- [x] **Doppelkosten-Warnung** — Fertigkeit über dem verknüpften Attribut fragt vor dem Steigern nach („Trotzdem steigern", Original: `needs_confirmation`)
- [x] **Erschaffung abschließen & Aufstiege** (`app/services/aufstiege.py`) — `erschaffung/abschliessen|oeffnen`, `aufstieg/hinzufuegen|entfernen`; danach kosten Attribut 1 / Fertigkeit 0.5 (über Attribut das Doppelte) / Talent 1 Aufstieg; Rang aus ausgegebenen Aufstiegen (4/8/12/16 → F/V/H/L) schaltet höherrangige Talente/Mächte frei; Aufstiegs-Leiste mit Rang im Editor

## Geplante Schritte (nach Nutzwert sortiert)

Abgleich mit der Geschäftslogik des Originals (`functions/`-Module):

### 1. Volk-Wahlmöglichkeiten: Spezialfälle (Original: `volk_wahlmoeglichkeiten.py`)

Kern ist umgesetzt (freies Attribut, Talent-oder-X). Es fehlen: **Magieaffin** (AH-Wahl + arkane Fertigkeit W6, über `spezielle_effekte`), **Attribut-Schwäche** (Malus-Wahl) und settingspezifische Wahlen (`spezialisierung` Androiden, `heimlich` Engro, `tierart_auswahl` Wildling, `freie_verstandsfertigkeit` Gnom u. a.).

### 2. Kompatibilitätsprüfung (Original: `kompatibilitaets_pruefung.py`)

Verbotene Kombinationen (z. B. „Reich" + „Arm") beim Wählen von Talenten/Handicaps ablehnen.

### 3. Export/Import im Frontend

Export-Button (`GET /api/charaktere/{id}/export` existiert); neuer `POST /api/charaktere/import` mit `ergaenze_fehlende_eigenschaften` als Normalisierung — macht auch Kivy-Alt-Exporte importierbar.

### 4. Ausrüstung & Startgeld (Original: `ausruestung_funktionen.py`)

Ausrüstungs-Tab (Daten liegen bereits in `setting["ausruestung"]`), Startgeld pro Setting (`setting["startgeld"]`), Einlösung 1 Handicap-Punkt → Startgeld, Traglast (Stärke × 10 kg), Rüstung fließt in Robustheit ein.

### 5. Setting-Spezialsysteme

Cyberware inkl. Stress (SciFi-Kompendium, `cyberware_funktionen.py` + `cyberware_config.json`), Superkräfte (Superkräfte-Kompendium, `superkraft_funktionen.py`).

### 6. Statblock-Export (Original: `statblock_generator.py`)

Charakter als Text-/PDF-Statblock exportieren.

### Begleitend: Tests ausbauen

Runner: `cd backend && .venv/bin/python -m pytest tests/`. Bei jedem Schritt mitwachsen lassen; offen: Auth-/Charaktere-Endpoints (Test-DB), Frontend-Tests.

## Reihenfolge-Begründung

1–2 machen die Erschaffung regelkonform und vervollständigen die Kern-Geschäftslogik des Originals; 3–4 erweitern den Spielzyklus (Export, Ausrüstung); 5–6 sind settingspezifischer Komfort.
