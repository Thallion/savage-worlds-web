#!/usr/bin/env bash
# Deployt den aktuellen Arbeitsstand auf den Raspberry Pi (PlexPi) und baut die
# Container neu. Überträgt per rsync (auch uncommittete Änderungen), lässt DB
# (data/) und Secret (.env) auf dem Pi unangetastet.
#
#   ./deploy.sh                 # Standard: exnef@PlexPi:~/savage-worlds-web
#   REMOTE=pi@host DIR=~/app ./deploy.sh   # Ziel überschreiben
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

REMOTE="${REMOTE:-exnef@PlexPi}"
DIR="${DIR:-~/savage-worlds-web}"

echo "==> Übertrage Code nach $REMOTE:$DIR ..."
rsync -az --delete \
    --exclude node_modules --exclude .venv --exclude dist \
    --exclude __pycache__ --exclude .git --exclude data --exclude .env \
    "$ROOT/" "$REMOTE:$DIR/"

echo "==> Baue und starte Container neu ..."
ssh "$REMOTE" "cd $DIR && sudo docker-compose up -d --build"

echo
echo "==> Fertig. App erreichbar unter: https://sw-char-generator.org"
echo "    Tunnel-Status prüfen: ssh $REMOTE 'cd $DIR && sudo docker-compose logs --tail=20 cloudflared'"
