# Build from the repository root:  docker build -f deploy/Dockerfile --target <stage> .
# The root .dockerignore is load-bearing: without it `COPY backend/ ./` drops the
# host virtualenv on top of the image's own.
#
# Base images are fully qualified: podman resolves bare names only through
# short-name aliases (`caddy` has none), and an explicit registry is one less
# thing a mirror can reinterpret.

# --- 1. frontend build -------------------------------------------------------
FROM docker.io/library/node:22-slim AS frontend
WORKDIR /build
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# --- 2. backend --------------------------------------------------------------
# The interpreter tracks backend/pyproject.toml's requires-python; uv sync
# --frozen fails outright on an older one.
FROM docker.io/library/python:3.14-slim AS backend
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
WORKDIR /app
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-dev
COPY backend/ ./
ENV PATH="/app/.venv/bin:$PATH" \
    HEMA_SQUIRE_DATABASE_URL="sqlite:////data/hema_squire.sqlite" \
    HEMA_SQUIRE_EMAIL_OUTBOX_DIR="/data/outbox"
# Migrations run before the server; --workers 1 is an invariant, not a tuning
# knob — the in-process scheduler must exist exactly once (design Decision 3).
# --proxy-headers makes the throttle see the real client instead of Caddy's
# container address; trusting every peer is safe because the container
# publishes no ports, so Caddy is the only thing that can reach it, and the
# Caddyfile overwrites X-Forwarded-For rather than appending to it.
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1 --proxy-headers --forwarded-allow-ips='*'"]

# --- 3. caddy with the built SPA --------------------------------------------
FROM docker.io/library/caddy:2-alpine AS web
COPY deploy/Caddyfile /etc/caddy/Caddyfile
COPY --from=frontend /build/dist /srv
