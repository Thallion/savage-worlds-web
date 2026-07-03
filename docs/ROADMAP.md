# Savage Worlds Web — Roadmap

Stand: 2026-07-03 · Abgleich mit dem Original (Kivy): https://github.com/Thallion/Savage-Worlds-Charakter-Generator-deutsch

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
- [x] **Backend-Tests** — pytest, 77 Tests (`backend/tests/`); dabei behobener Regelbug: Fertigkeit über Attribut kostete 1 statt 2 Punkte
- [x] Regelbug behoben: Handicap-Punkte wurden beim Wählen überschrieben statt addiert
- [x] **Doppelkosten-Warnung** — Fertigkeit über dem verknüpften Attribut fragt vor dem Steigern nach („Trotzdem steigern", Original: `needs_confirmation`)
- [x] **Kompatibilitätsprüfung** (`app/services/kompatibilitaet.py`) — verbotene Kombinationen (Reich/Stinkreich ↔ Arm) beim Wählen in beide Richtungen abgelehnt, nicht überspringbar
- [x] **Export/Import** — Export-Button (JSON-Download) und Import-Button (Datei-Upload) in der Charakterliste; `POST /api/charaktere/import` normalisiert über `ergaenze_fehlende_eigenschaften` (auch Kivy-Alt-Exporte), Namenskollisionen werden nummeriert
- [x] **Erschaffung abschließen & Aufstiege** (`app/services/aufstiege.py`) — `erschaffung/abschliessen|oeffnen`, `aufstieg/hinzufuegen|entfernen`; danach kosten Attribut 1 / Fertigkeit 0.5 (über Attribut das Doppelte) / Talent 1 Aufstieg; Rang aus ausgegebenen Aufstiegen (4/8/12/16 → F/V/H/L) schaltet höherrangige Talente/Mächte frei; Aufstiegs-Leiste mit Rang im Editor
- [x] **Volk-Wahlmöglichkeiten: Spezialfälle** (`app/services/volk_wahlen.py`) — `volk/wahl` mit `wahl_id:auswahl`-Format; Fertigkeits-Wahlen auf W6 (`heimlich` Engro, `freie_verstandsfertigkeit` Gnom, `handwerks_wissen` Zwerg/Sundered Skies, `spezialisierung` Androiden), **Magieaffin** (AH-Wahl, Talent frei als Volks-Talent, Arkane Fertigkeit W4-2 → W4 wie im Original), **Attribut-Schwäche** (Malus-Wahl über `effects.attribut_malus`/`attribut_malus_wert`, greift bei Custom-Völkern), `outsider_statt_trennungsangst` (Insektoide, Handicap-Verzicht), beschreibende Wahlen `pflanzenerbe_auswahl`/`tierart_auswahl` (Optionen in `config/volk_wahl_config.json`, Tierart Freitext — Regel-Effekte je Tierart fehlen auch im Original als Daten); Snapshots in `volk_effekte.wahlen`, Volk-Wechsel nimmt alles zurück; Spezialwahl-Karten im VoelkerTab

## Geplante Schritte (nach Nutzwert sortiert)

Abgleich mit der Geschäftslogik des Originals (`functions/`-Module):

### 1. Ausrüstung & Startgeld (Original: `ausruestung_funktionen.py`)

Ausrüstungs-Tab (Daten liegen bereits in `setting["ausruestung"]`), Startgeld pro Setting (`setting["startgeld"]`), Einlösung 1 Handicap-Punkt → Startgeld, Traglast (Stärke × 10 kg), Rüstung fließt in Robustheit ein.

### 2. Setting-Spezialsysteme

Cyberware inkl. Stress (SciFi-Kompendium, `cyberware_funktionen.py` + `cyberware_config.json`), Superkräfte (Superkräfte-Kompendium, `superkraft_funktionen.py`).

### 3. Statblock-Export (Original: `statblock_generator.py`)

Charakter als Text-/PDF-Statblock exportieren.

### Begleitend: Tests ausbauen

Runner: `cd backend && .venv/bin/python -m pytest tests/`. Bei jedem Schritt mitwachsen lassen; offen: Auth-/Charaktere-Endpoints (Test-DB), Frontend-Tests.

## Reihenfolge-Begründung

1 erweitert den Spielzyklus (Ausrüstung, Startgeld, Rüstung); 2–3 sind settingspezifischer Komfort.
