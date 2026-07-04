#!/usr/bin/env bash
# Startet Backend (FastAPI, Port 8000) und Frontend (Vite, Port 5173).
# Beenden mit Strg+C stoppt beide Server.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Backend-venv anlegen und Abhängigkeiten installieren, falls nötig
if [ ! -x "$ROOT/backend/.venv/bin/uvicorn" ]; then
    echo "==> Erstelle venv und installiere Backend-Abhängigkeiten..."
    python3 -m venv "$ROOT/backend/.venv"
    "$ROOT/backend/.venv/bin/pip" install -r "$ROOT/backend/requirements.txt"
fi

# Frontend-Abhängigkeiten installieren, falls nötig
if [ ! -d "$ROOT/frontend/node_modules" ]; then
    echo "==> Installiere Frontend-Abhängigkeiten..."
    (cd "$ROOT/frontend" && npm install)
fi

echo "==> Starte Backend auf http://localhost:8000 ..."
(cd "$ROOT/backend" && .venv/bin/uvicorn main:app --reload --port 8000) &
BACKEND_PID=$!

echo "==> Starte Frontend auf http://localhost:5173 ..."
(cd "$ROOT/frontend" && npm run dev) &
FRONTEND_PID=$!

trap 'echo; echo "==> Stoppe Server..."; kill "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null; wait' INT TERM

echo
echo "App läuft: http://localhost:5173  (API-Docs: http://localhost:8000/api/docs)"
echo "Beenden mit Strg+C"
wait
