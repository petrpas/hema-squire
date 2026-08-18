#!/usr/bin/env bash
# Full local run: backend (FastAPI, :8000) + frontend (Vite, :5173).
#
#   ./dev.sh          start both servers
#   ./dev.sh --seed   also seed a demo tournament (idempotent)
#
# Optional environment (put it in backend/.env or export before running):
#   HEMA_SQUIRE_OWNER_EMAIL           deployment Owner account email (all
#                                      capabilities, incl. granting Admin);
#                                      defaults below to the seeded owner
#                                      account (petr.pascenko@gmail.com)
#   HEMA_SQUIRE_ANTHROPIC_API_KEY     enables LLM table parse / match / dedup
#   HEMA_SQUIRE_GOOGLE_CREDENTIALS_PATH  enables the Google Sheets export
set -euo pipefail
cd "$(dirname "$0")"

export HEMA_SQUIRE_OWNER_EMAIL="${HEMA_SQUIRE_OWNER_EMAIL:-petr.pascenko@gmail.com}"
# local work runs on the repository's published dev signing key, which the app
# otherwise refuses to start on (app.main._refuse_dev_secret_key)
export HEMA_SQUIRE_DEBUG="${HEMA_SQUIRE_DEBUG:-1}"

SEED=false
[[ "${1:-}" == "--seed" ]] && SEED=true

command -v uv >/dev/null || { echo "uv is required — https://docs.astral.sh/uv/"; exit 1; }
command -v npm >/dev/null || { echo "npm is required"; exit 1; }

for port in 8000 5173; do
  if lsof -i ":$port" -sTCP:LISTEN >/dev/null 2>&1; then
    echo "Port $port is already in use — stop that process first (lsof -i :$port)."
    exit 1
  fi
done

echo "== backend: dependencies + migrations"
(cd backend && uv sync --quiet && uv run alembic upgrade head)

echo "== backend: owner account"
(cd backend && uv run python ../scripts/seed_owner.py)

echo "== frontend: dependencies"
(cd frontend && npm install --silent)

trap 'trap - TERM; kill 0 2>/dev/null' INT TERM EXIT

(cd backend && uv run uvicorn app.main:app --port 8000 --reload) &
(cd frontend && npm run dev) &

printf "== waiting for backend"
for _ in $(seq 1 30); do
  curl -fs localhost:8000/api/health >/dev/null 2>&1 && break
  printf "."
  sleep 1
done
echo " up"

if $SEED; then
  echo "== seeding demo tournament"
  (cd backend && uv run python ../scripts/seed_demo.py)
fi

echo
echo "HEMA Squire is running:"
echo "  console    http://localhost:5173"
echo "  API        http://localhost:8000/api/health"
echo "  API docs   http://localhost:8000/docs"
echo "  mail outbox backend/outbox/ (.eml files)"
echo "  owner login: petr.pascenko@gmail.com / swordismylife (Organizer role, deployment Owner)"
$SEED && echo "  organizer login: petr@example.com / demo-heslo-123 (see seed output for admin/fencer logins)"
echo
echo "Ctrl+C stops both servers."
wait
