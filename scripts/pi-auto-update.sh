#!/usr/bin/env bash
# Automatisches Container-Update auf dem Pi (läuft wöchentlich per systemd-Timer,
# siehe scripts/systemd/). Holt neue Basis-Images (python, nginx, node,
# cloudflared), baut neu und startet die Container. Schlägt der Health-Check
# danach fehl (z. B. weil eine ungepinnte Python-Abhängigkeit inkompatibel
# geworden ist), werden die vorherigen Images wiederhergestellt.
#
#   sudo ./scripts/pi-auto-update.sh     # manuell ausführen
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."
PROJEKT="$(basename "$PWD")"
GEBAUT=(backend nginx)

pruefe_gesundheit() {
    local i
    for i in $(seq 1 12); do
        if docker-compose exec -T nginx wget -qO- http://localhost/api/health >/dev/null 2>&1 \
            && docker-compose exec -T nginx wget -qO- http://localhost/ >/dev/null 2>&1; then
            return 0
        fi
        sleep 5
    done
    return 1
}

echo "==> Sichere aktuelle Images als :vorher"
for s in "${GEBAUT[@]}"; do
    docker tag "${PROJEKT}_${s}:latest" "${PROJEKT}_${s}:vorher" 2>/dev/null || true
done

echo "==> Hole neue Images und baue neu"
docker-compose pull cloudflared
docker-compose build --pull
docker-compose up -d

if pruefe_gesundheit; then
    echo "==> Update erfolgreich"
else
    echo "!!! Health-Check fehlgeschlagen — stelle vorherige Images wieder her" >&2
    for s in "${GEBAUT[@]}"; do
        docker tag "${PROJEKT}_${s}:vorher" "${PROJEKT}_${s}:latest" 2>/dev/null || true
    done
    docker-compose up -d
    pruefe_gesundheit && echo "==> Rollback erfolgreich" >&2
    exit 1
fi

docker image prune -f
