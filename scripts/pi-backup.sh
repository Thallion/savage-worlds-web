#!/usr/bin/env bash
# Nächtliches Backup von data/ (SQLite-DB, eigene Settings, Porträts) auf die
# externe Platte. Läuft per systemd-Timer (scripts/systemd/sw-chargen-backup.*).
#
# Die DB wird über die SQLite-Backup-API kopiert — konsistent auch dann, wenn
# das Backend gerade schreibt (ein einfaches cp könnte eine halbe DB sichern).
#
#   sudo ./scripts/pi-backup.sh                       # manuell
#   BACKUP_ZIEL=/pfad BEHALTEN_TAGE=30 ./scripts/pi-backup.sh
#
# Wiederherstellen:
#   sudo docker-compose stop backend
#   sudo tar -xzf <archiv> -C ~/savage-worlds-web     # legt data/ neu an
#   sudo chown -R 1000:1000 ~/savage-worlds-web/data && sudo docker-compose start backend
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."
MOUNT="${BACKUP_MOUNT:-/media/plex2}"
ZIEL="${BACKUP_ZIEL:-$MOUNT/backups/sw-chargen}"
BEHALTEN_TAGE="${BEHALTEN_TAGE:-30}"

# nofail-Mount: fehlt die Platte, darf nichts auf die SD-Karte geschrieben werden
if ! mountpoint -q "$MOUNT"; then
    echo "!!! $MOUNT ist nicht eingehängt — Backup abgebrochen" >&2
    exit 1
fi

umask 077
mkdir -p "$ZIEL"
chmod 700 "$ZIEL"

ARBEIT="$(mktemp -d)"
trap 'rm -rf "$ARBEIT"' EXIT
mkdir -p "$ARBEIT/data"

python3 - "data/chargen.db" "$ARBEIT/data/chargen.db" <<'EOF'
import sqlite3, sys
quelle = sqlite3.connect(f"file:{sys.argv[1]}?mode=ro", uri=True)
ziel = sqlite3.connect(sys.argv[2])
quelle.backup(ziel)
ok = ziel.execute("PRAGMA integrity_check").fetchone()[0]
if ok != "ok":
    sys.exit(f"Integritätsprüfung fehlgeschlagen: {ok}")
EOF

for verzeichnis in settings bilder; do
    [ -d "data/$verzeichnis" ] && cp -a "data/$verzeichnis" "$ARBEIT/data/"
done

ARCHIV="$ZIEL/chargen-$(date +%F_%H%M).tar.gz"
tar -czf "$ARCHIV.tmp" -C "$ARBEIT" data
mv "$ARCHIV.tmp" "$ARCHIV"
echo "==> Backup erstellt: $ARCHIV ($(du -h "$ARCHIV" | cut -f1))"

find "$ZIEL" -maxdepth 1 -name 'chargen-*.tar.gz' -mtime +"$BEHALTEN_TAGE" -print -delete
