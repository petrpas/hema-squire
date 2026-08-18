## Why

The application has no production form: the only way to run it is `dev.sh`, which assumes a laptop. v1 ran on Fly.io; for v2 the deployment target is a single Hetzner CX23 VPS with SQLite kept as the production database — the load profile (a burst of a few dozen registrations in the first minutes after a tournament opens, near-silence otherwise) sits several orders of magnitude below what one small machine handles, and the in-process scheduler already pins the app to exactly one worker, which is precisely the shape SQLite wants.

Getting there surfaced five gaps in the code itself, each of which is a production incident waiting to happen rather than a style preference:

- The SQLite engine runs on defaults — no WAL, foreign keys unenforced, and a busy timeout that is whatever the driver happens to apply. Litestream (the backup mechanism) requires WAL to exist at all, and FK non-enforcement lets orphan rows accumulate silently until the eventual Postgres migration rejects them. (An earlier draft of this proposal claimed the default busy timeout is 0, so contending writers fail instantly; that is wrong — Python's `sqlite3` applies 5 s of its own. Stating `busy_timeout=5000` explicitly still earns its place: it makes the value part of the schema's definition rather than a driver default that a driver change can move.)
- `settings.secret_key` defaults to a string published in this repository and signs every JWT. A deployment that forgets to set it hands token forgery — any user, including the Owner — to anyone who can read GitHub.
- `/api/auth/login` costs ~100 ms of scrypt per call by design, making it simultaneously the cheapest CPU-exhaustion target and a credential-stuffing surface, with no throttle.
- The multitenant boundary (per-tournament console access) is designed correctly in `auth.py` but enforced only by the discipline of each router; no test sweeps the console surface with a foreign tournament and asserts refusal.
- `get_mailer()` always returns `OutboxMailer` — in production, payment reminders and expiry notices are serialized into a directory nobody reads. Email delivery does not exist.

## What Changes

- **New `deploy/` directory** with the complete production definition: a multi-stage `Dockerfile` (frontend build → backend image → Caddy image with the built SPA baked in), `docker-compose.yml` (app + Caddy + Litestream), `Caddyfile` (TLS, static SPA with client-routing fallback, `/api/*` proxied), `litestream.yml` (continuous WAL replication to S3-compatible storage, 28-day retention), `cloud-init.yaml` (server bootstrap: SSH hardening, Docker, unattended upgrades), `deploy.sh`, `restore.sh`, `.env.example`, `README` (file map and restore-drill log), plus a repository-root `.dockerignore` — Docker ignores `.gitignore`, and the build context is the repository root.
- **SQLite pragmas on connect** in `db.py`: WAL, `busy_timeout=5000`, `synchronous=NORMAL`, `foreign_keys=ON`.
- **Startup guard** refusing to boot with the dev `secret_key` outside explicit debug mode.
- **Login/signup throttling** in the app layer (Caddy stays a stock build), keyed on the client address the proxy establishes rather than on the proxy's own — otherwise the limit is one global bucket and a single scanner locks out a tournament.
- **Tenant-isolation test** sweeping console endpoints with a foreign tournament.
- **SMTP mailer** selected by configuration, `OutboxMailer` remaining the dev default.

Not in scope: photo storage (object storage, its own change when it comes), the Discord importer channel, any Postgres migration, CI-driven deployment (deploys are `deploy.sh` over SSH; a pipeline can wrap it later without changing the shape).

## Capabilities

### New Capabilities
- `deployment`: the production posture of the system — single-process invariant, durable continuously-replicated backups with a rehearsed restore, secret hygiene, authentication throttling, tenant isolation under test, real email delivery, and a closed network perimeter.

## Impact

**New** (`deploy/`): `Dockerfile`, `docker-compose.yml`, `Caddyfile`, `litestream.yml`, `cloud-init.yaml`, `deploy.sh`, `restore.sh`, `.env.example`.

**Backend** (`backend/app/`): `db.py` (`apply_sqlite_pragmas`, applied to the application engine and to the test fixtures so enforcement is not production-only), `main.py` (startup guard, limiter wiring), `routers/auth.py` (throttle on login/signup), `mail.py` (`SmtpMailer`, config-selected), `config.py` (SMTP settings, `debug` flag); `tests/conftest.py` (pragmas on the fixture engine, debug flag so the new startup guard does not fail the suite); new `backend/tests/test_tenant_isolation.py`.

**Operational cost**: ~€6/month for the CX23; backup storage rides a free object-storage tier at this database size. The fixed setup cost is one afternoon; steady-state attention is near zero by construction — every control in this change is a standing constraint, not a routine.

**Verification**: `pytest` covers the pragma behaviour, the startup guard, the throttle (including that throttling one address leaves others served), and tenant isolation; the existing 612-test suite has been confirmed to pass under `foreign_keys=ON`, so that pragma is a regression guard rather than a cleanup. The deployment itself is verified by the restore drill in tasks group 5, which is deliberately part of the definition of done and uses the off-host copy of `deploy/.env` — an untested restore is a hypothesis, and a restore rehearsed with material from the host being replaced is not a rehearsal.
