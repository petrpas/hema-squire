#!/usr/bin/env bash
# One-command deploy: pull the current main and rebuild in place.
#   ./deploy/deploy.sh [ssh-host]        default host: hemasquire
# The default is the ~/.ssh/config alias, not squire@hemasquire.eu: the alias
# is what resolves the deploy key, and spelling the host out bypasses it.
# Rollback = git checkout <previous tag> on the server and rerun.
set -euo pipefail

HOST="${1:-hemasquire}"

ssh "$HOST" bash -s <<'REMOTE'
set -euo pipefail
cd /opt/hema-squire

[ -f deploy/.env ] || {
  echo "deploy/.env is missing — see deploy/.env.example (task 2.7)" >&2
  exit 1
}

git pull --ff-only

# Which services to bring up. Litestream joins only once the replica is really
# configured: with REPLICA_ENDPOINT empty it finds nowhere to write, restarts
# forever under `unless-stopped`, and a permanently red container is how you
# train yourself to stop reading `docker compose ps`. Nothing depends on it, so
# the site is identical without it — what is missing is the safety net. This
# reads .env rather than hardcoding the list, so the day 3.1 lands and the
# REPLICA_ variables are filled, the next deploy starts it without an edit here.
replica=$(awk -F= '/^REPLICA_ENDPOINT=/ {
  sub(/^[^=]*=/, ""); sub(/#.*/, ""); gsub(/[[:space:]]/, ""); print; exit
}' deploy/.env)

if [ -n "$replica" ]; then
  services="app web litestream"
else
  services="app web"
  echo "note: REPLICA_ENDPOINT is empty, so litestream stays down (task 3.1)"
fi

echo "starting: $services"
docker compose -f deploy/docker-compose.yml up -d --build $services
docker image prune -f
echo "Deployed $(git rev-parse --short HEAD)"
REMOTE
