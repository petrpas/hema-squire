#!/usr/bin/env bash
# One-command deploy: pull the current main and rebuild in place.
#   ./deploy/deploy.sh [ssh-host]        default host: hemasquire
# The default is the ~/.ssh/config alias, not squire@hemasquire.eu: the alias
# is what resolves the deploy key, and spelling the host out bypasses it.
# Exits non-zero if the app does not come up healthy, so a failed deploy is
# a failed command rather than a cheerful message over a crash loop.
# Rollback = git checkout <previous tag> on the server and rerun.
set -euo pipefail

HOST="${1:-hemasquire}"

ssh "$HOST" bash -s <<'REMOTE'
set -euo pipefail
cd /opt/hema-squire

compose="docker compose -f deploy/docker-compose.yml"

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
$compose up -d --build $services

# Compose returns once the containers are *started*, which is before alembic
# has migrated and uvicorn has answered anything. Reporting a deploy at that
# moment announces success over a container that may already be crash-looping,
# so wait for the healthcheck the compose file already defines. Only `app`
# has one; web and litestream are judged by app coming up behind them.
# The compose healthcheck allows a 60s start_period, so the ceiling is well
# clear of a cold start that has migrations to run.
cid=$($compose ps -q app)
[ -n "$cid" ] || { echo "app: no container after up" >&2; exit 1; }

started=$SECONDS
deadline=$((SECONDS + 240))
while :; do
  state=$(docker inspect -f '{{.State.Status}}' "$cid" 2>/dev/null || echo gone)
  health=$(docker inspect \
    -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' \
    "$cid" 2>/dev/null || echo gone)

  if [ "$health" = healthy ]; then
    echo "app: healthy after $((SECONDS - started))s"
    break
  fi

  # A container with no healthcheck can never report healthy; treat running as
  # the best available answer rather than looping to the deadline.
  if [ "$health" = none ] && [ "$state" = running ]; then
    echo "app: running (no healthcheck defined)"
    break
  fi

  if [ "$health" = unhealthy ] || [ "$state" != running ]; then
    echo "app: $state/$health — deploy failed" >&2
    $compose logs --tail 40 app >&2
    exit 1
  fi

  if [ "$SECONDS" -ge "$deadline" ]; then
    echo "app: still '$health' after $((SECONDS - started))s — giving up" >&2
    $compose logs --tail 40 app >&2
    exit 1
  fi

  sleep 3
done

docker image prune -f
echo "Deployed $(git rev-parse --short HEAD)"
REMOTE
