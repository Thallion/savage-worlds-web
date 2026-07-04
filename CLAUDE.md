# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Web port of the German Savage Worlds character generator (original Kivy desktop app: https://github.com/Thallion/Savage-Worlds-Charakter-Generator-deutsch). Domain language is **German** throughout — API routes, DB columns, schemas, store methods, and UI text all use German terms (Charakter, Fertigkeit, Talent, Handicap, Volk, Macht, Steigerung). Keep new code consistent with that.

## Commands

### Backend (FastAPI, Python 3.11+)

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000     # dev server, run from backend/
```

- API docs: http://localhost:8000/api/docs (Swagger), health check at `/api/health`.
- SQLite DB is created automatically at `backend/data/chargen.db` on startup (`Base.metadata.create_all`; no Alembic migrations yet — schema changes require deleting the DB or writing a migration).
- Config via env vars with `CHARGEN_` prefix (see `app/config.py`): `CHARGEN_SECRET_KEY`, `CHARGEN_DATABASE_URL`, etc.
- Tests: `pip install -r requirements-dev.txt`, then `python -m pytest tests/` (run from `backend/`). Single test: `python -m pytest tests/test_spiellogik.py -k <name>`. The spiellogik endpoints are stateless dict-transformers, so those tests need no DB.

### Frontend (Vue 3 + Vuetify 3 + Pinia + Vite, TypeScript)

```bash
cd frontend
npm install
npm run dev        # Vite dev server on http://localhost:5173
npm run build      # vue-tsc type-check + production build to frontend/dist
```

- The Vite dev server proxies `/api` to `http://localhost:8000` (see `vite.config.ts`), so both servers must run in development. There is no lint script; `npm run build` is the type-check.

### Docker deployment

`docker-compose up` builds the backend image (Dockerfile is backend-only) and serves a pre-built `frontend/dist` via nginx on port 80. Run `npm run build` first.

## Architecture

The core design decision: **character state lives in one JSON blob, and game rules are stateless.**

- A `Charakter` DB row (`backend/app/db/models.py`) holds metadata plus `charakter_daten`, a JSON column containing the entire character (attribute, fertigkeiten, selected_handicaps, selected_talente, voelker_selected, remaining advancement points, …).
- Game-rule endpoints in `backend/app/api/spiellogik.py` (`/api/spiellogik/{aktion}`, e.g. `attribut/steigern`, `fertigkeit/senken`, `handicap/waehlen`) receive the full `charakter_daten` dict plus an `element_name`, apply the rule, and return the mutated dict in a `SpiellogikResponse {success, message, charakter_daten}`. They read/write nothing in the DB.
- The frontend Pinia store (`frontend/src/stores/charakter.ts`) has a single generic `spiellogikAktion(aktion, elementName)` that posts the current character JSON to the matching endpoint and replaces the local state with the returned dict. Persistence is a separate explicit `speichereCharakter()` PUT to `/api/charaktere/{id}`.

Game content (rules data) is plain JSON, not code:

- `backend/gamelogic/settings/*.json` — one file per campaign setting (SWAE, Deadlands, Hellfrost, …). The filename stem **is** the setting name used in `active_setting_name` and the `/api/settings` endpoints. Each file contains that setting's voelker, talente, handicaps, maechte, etc.
- `backend/gamelogic/config/*.json` — setting-independent base config.
- User-created settings (Setting-Verwaltung: leer/Kopie, Zusammenführung, aus Charakter, Elementauswahl — `app/services/setting_verwaltung.py`, write endpoints on `/api/settings`) are stored as JSON in `backend/data/settings/`; `load_setting` resolves names against the native directory first, then this one.
- `backend/gamelogic/models/*.py` are Python classes ported from the Kivy app but are currently **not imported by the API** — the spiellogik endpoints operate directly on dicts. Check before assuming they are wired in.

Auth: hand-rolled and minimal on purpose. JWT encode/decode is implemented locally in `backend/app/jwt_utils.py` (HS256 via hmac; PyJWT is in requirements but unused), passwords are PBKDF2-hashed in `app/api/auth.py`, and `get_current_user` in `app/api/deps.py` guards all `/api/charaktere` routes (users only see their own characters). The frontend keeps the token in `localStorage` and attaches it in `frontend/src/api/client.ts`, a thin fetch wrapper — no axios.

Frontend structure: `views/CharakterEditorView.vue` hosts the editor tabs in `components/charakter/` (one tab per generation step: Profil, Völker, Eigenschaften, Handicaps, Talente, Übersicht). Types for the character JSON live in `frontend/src/types/charakter.ts` and must stay in sync with what the spiellogik endpoints produce.
