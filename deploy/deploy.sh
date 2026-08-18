#!/usr/bin/env bash
# One-command deploy: pull the current main and rebuild in place.
#   ./deploy/deploy.sh [ssh-host]        default host: squire@hemasquire.eu
# Rollback = git checkout <previous tag> on the server and rerun.
set -euo pipefail

HOST="${1:-squire@hemasquire.eu}"

ssh "$HOST" bash -s <<'REMOTE'
set -euo pipefail
cd /opt/hema-squire
git pull --ff-only
docker compose -f deploy/docker-compose.yml up -d --build
docker image prune -f
echo "Deployed $(git rev-parse --short HEAD)"
REMOTE
