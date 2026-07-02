# Savage Worlds Charakter-Generator (Web)

Web-Version des deutschen [Savage-Worlds-Charakter-Generators](https://github.com/Thallion/Savage-Worlds-Charakter-Generator-deutsch) (Original: Kivy-Desktop-App). Charaktere für Savage Worlds (SWAE) und diverse Settings (Deadlands, Hellfrost, Savage Pathfinder, …) im Browser erstellen und verwalten.

**Stack:** FastAPI + SQLAlchemy + SQLite (Backend) · Vue 3 + Vuetify 3 + Pinia + Vite (Frontend, TypeScript)

## Voraussetzungen

- Python 3.11+
- Node.js 20+

## Setup & Entwicklung

Für die Entwicklung laufen zwei Server parallel: das Backend auf Port 8000 und der Vite-Dev-Server auf Port 5173 (leitet `/api`-Anfragen ans Backend weiter).

### 1. Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Beim ersten Start wird automatisch eine SQLite-Datenbank unter `backend/data/chargen.db` angelegt.

- Health-Check: http://localhost:8000/api/health
- API-Dokumentation (Swagger): http://localhost:8000/api/docs

### 2. Frontend

In einem zweiten Terminal:

```bash
cd frontend
npm install
npm run dev
```

Danach läuft die App unter **http://localhost:5173** — dort zuerst einen Account registrieren, dann einloggen und Charaktere anlegen.

## Konfiguration

Das Backend liest Umgebungsvariablen mit dem Präfix `CHARGEN_` (siehe `backend/app/config.py`):

| Variable | Default | Beschreibung |
|---|---|---|
| `CHARGEN_SECRET_KEY` | Unsicherer Platzhalter | JWT-Signaturschlüssel — in Produktion setzen (`openssl rand -hex 32`) |
| `CHARGEN_DATABASE_URL` | `sqlite:///./data/chargen.db` | SQLAlchemy-Datenbank-URL |
| `CHARGEN_ACCESS_TOKEN_EXPIRE_MINUTES` | `1440` | Token-Gültigkeit (24 h) |

## Produktion / Docker

Das Frontend wird statisch gebaut und von nginx ausgeliefert, das Backend läuft im Container:

```bash
cd frontend && npm install && npm run build && cd ..
CHARGEN_SECRET_KEY=$(openssl rand -hex 32) docker compose up -d
```

Die App ist dann unter Port 80 erreichbar. Die Datenbank liegt persistent im Volume `./data`.

## Projektstruktur

```
backend/
  main.py               # FastAPI-App, Router-Registrierung
  app/
    api/                # Endpunkte: auth, charaktere, einstellungen, spiellogik
    db/                 # SQLAlchemy-Modelle (User, Charakter)
    schemas/            # Pydantic-Schemas
  gamelogic/
    settings/*.json     # Spieldaten pro Setting (Dateiname = Setting-Name)
    config/*.json       # Setting-unabhängige Basiskonfiguration
frontend/
  src/
    views/              # Login, Registrierung, Charakterliste, Editor
    components/charakter/  # Editor-Tabs (Profil, Völker, Eigenschaften, …)
    stores/             # Pinia-Stores (auth, charakter, einstellungen)
    api/client.ts       # Fetch-Wrapper mit JWT-Header
```

Die Spiellogik ist zustandslos: Die Endpunkte unter `/api/spiellogik/...` erhalten den kompletten Charakter als JSON, wenden eine Regel an (z. B. Attribut steigern) und geben den geänderten Charakter zurück. Gespeichert wird explizit über `PUT /api/charaktere/{id}`.
