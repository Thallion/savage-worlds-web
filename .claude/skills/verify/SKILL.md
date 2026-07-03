---
name: verify
description: Startet Backend + Frontend dieses Repos und verifiziert Änderungen im laufenden Browser (Playwright).
---

# Savage Worlds Web end-to-end verifizieren

## Starten

```bash
cd backend && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt -r requirements-dev.txt
.venv/bin/uvicorn main:app --port 8000 &          # aus backend/ starten
cd ../frontend && npm install && npm run dev &     # Vite auf :5173, proxy't /api -> :8000
curl -s localhost:8000/api/health                  # {"status":"ok"}
```

## Browser-Flow (Playwright, Chromium unter /opt/pw-browsers/chromium)

- `playwright` als devDependency in frontend/ installieren; Skripte außerhalb
  von frontend/ müssen `frontend/node_modules/playwright/index.mjs` absolut importieren.
- Registrieren (`/register`, E-Mail **und** Benutzername müssen unique sein),
  danach bleibt die Seite auf /register → manuell zu `/login` navigieren und anmelden.
- Charakter anlegen: Button „Neuer Charakter“ → Dialog; das Setting-Select per
  `.v-dialog .v-select .v-field__input` klicken (Vuetify-Label fängt Klicks ab),
  Option per `getByRole('option', { name: ... })`.
- Editor-Tabs: Profil / Volk / Eigenschaften / Handicaps / Talente / Übersicht.

## Fallstricke

- **Vite dep-optimize reloadet die Seite** beim ersten Besuch neuer Views
  („optimized dependencies changed. reloading“) — der erste Playwright-Lauf
  kann dadurch die Navigation verlieren. Einfach erneut laufen lassen oder
  vorher jede View einmal aufrufen.
- Vuetify-Selects nie über das Label klicken, immer `.v-field__input`.
- Vuetify-Switches: `.v-switch input[type="checkbox"]` mit `check({ force: true })`
  schalten — Klick auf den Container toggelt nicht zuverlässig.
- Einmal besuchte Editor-Tabs bleiben im DOM gemountet: Locators wie
  `getByLabel('… suchen...')` brauchen `.first()`, sobald mehrere Tabs offen waren.
- SQLite-DB liegt unter `backend/data/chargen.db`; Testnutzer bleiben bestehen.

## Fehlerpfade per curl

`/api/spiellogik/*` ist zustandslos — minimales `charakter_daten`-JSON reicht:

```bash
curl -s localhost:8000/api/spiellogik/volk/wahl -H 'Content-Type: application/json' \
  -d '{"charakter_daten":{...},"element_name":"heimlich:Kämpfen"}'
```
