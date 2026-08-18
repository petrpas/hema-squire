# Deployment design

## Decision 1: One VPS, not a platform

Hetzner CX23 (2 shared vCPU, 4 GB, 40 GB NVMe, ~€6/mo) over returning to Fly.io. The deciding
observation is that the platform's main economic feature — scale-to-zero — is unusable here: the
scheduler runs in the FastAPI lifespan, so a sleeping machine stops polling Fio, matching payments
and sending reminders. Once the machine must run continuously, Fly is a VPS at a premium with less
control, and its volume is the same single point of failure as a VPS disk. Fly remains a valid
fallback: nothing in this change is Fly-specific except `cloud-init.yaml`, and the Litestream-beside-
the-app pattern is identical there.

Capacity is not a consideration either way. The peak — tens of registrations in the first minutes —
is single-digit requests/second against a machine that serves hundreds; the most expensive single
operation in the system is one scrypt hash (~100 ms). The honest constraint of €6 is availability,
not performance: host death means downtime until migration or rebuild, and the restore drill (group 5)
is what makes that an inconvenience instead of a loss.

## Decision 2: SQLite stays; Litestream is the backup

The single-worker invariant (Decision 3) removes every concurrency argument for Postgres, and the
codebase is already built to switch later (`native_enum=False`, `render_as_batch`, generic `JSON`,
no PG-specific code). The realistic trigger for Postgres is wanting a second process or managed
backups — not load. Until then, migration would be pure overhead.

Backups are continuous WAL replication (Litestream 0.5, the maintained line — it reads SQLite's WAL
and stores it remotely in its own LTX format) to S3-compatible object storage, not periodic
dumps: data loss on failure is measured in seconds, restore is point-in-time, and the cost at ~1 GB
is zero. This is why the WAL pragma commit is a prerequisite, not a nicety — Litestream works by
reading the WAL. Retention is 28 days, deliberately short: point-in-time history retains deleted
rows, so backup retention is part of the data-deletion story, not just the disaster story.

A `PRAGMA foreign_key_check` runs once before enabling `foreign_keys=ON` in production, so any
orphan rows accumulated under non-enforcement surface now, on our schedule, rather than during a
future Postgres migration. The pragmas are applied through a function the test fixtures call too:
enforcement that holds only in production is enforcement discovered in production.

Within that function the journal mode sits apart from the rest. `busy_timeout`, `synchronous` and
`foreign_keys` are per-connection settings, so they belong in a connect listener. `journal_mode` is
a property of the database file, and switching it needs an exclusive lock that SQLite refuses
outright — returning "database is locked" without consulting `busy_timeout` — when another writer
holds one. Re-asserting it per connection would therefore convert a moment of write contention into
connections that fail before serving a request, which is the failure this decision exists to
prevent. It is set once, at engine setup.

One coincidence worth recording so it is not tidied away: `alembic/env.py` builds its own engine
via `engine_from_config` rather than importing `app.db.engine`, so migrations run without
`foreign_keys=ON`. That is what keeps `render_as_batch=True` safe — SQLite rebuilds a table by
renaming it, and under FK enforcement the rename rewrites references in other tables, which is
exactly what batch migrations must not do. Reusing the application engine in `env.py` would look
like a simplification and would silently corrupt the next batch migration.

## Decision 3: Exactly one uvicorn worker — an invariant, not a tuning choice

`--workers 2` would run the scheduler twice: duplicate Fio polls and, worse, duplicate reminder
emails. The Dockerfile pins `--workers 1` and this document records why, so the flag is never
"optimized" away. The same invariant will bind the future Discord poller — whatever process polls,
there is exactly one of it.

## Decision 4: Caddy serves the SPA and terminates TLS; the backend image stays pure

The frontend calls relative `/api/*` paths, so the split is clean: a Caddy image with the Vite
`dist/` baked in serves static files (with `try_files … /index.html` for client-side routing) and
proxies `/api/*` to the app container. No `StaticFiles` mount enters the backend, certificates are
Caddy's problem, and the app container never faces the internet directly.

## Decision 5: Security posture — close the perimeter by construction, then trust only tested code

Threat model: untargeted scanning and opportunistic compromise (cryptominers, credential stuffing),
not directed attack. Accordingly:

- The Hetzner Cloud Firewall (external to the host) admits only 22/80/443. External placement
  matters because Docker's published ports bypass host-level ufw by rewriting iptables; an external
  firewall is immune to that class of surprise.
- SSH is key-only, no root login, via cloud-init — misconfiguration is prevented, not remembered.
- `unattended-upgrades` patches the OS; image versions are bumped at deploy time.
- Inside the application, the two realistic leak vectors get systemic guards: the published dev
  `secret_key` cannot boot in production (startup refusal), and the multitenant boundary is held by
  a parameterized test rather than per-router discipline.
- Login throttling lives in the app (slowapi), keeping Caddy a stock binary rather than an xcaddy
  build for one plugin. This puts the throttle behind a proxy, which decides what "per address"
  means: unforwarded, every request carries Caddy's container address and the limit becomes one
  global bucket — a single scanner locks out an entire tournament. So Caddy overwrites
  `X-Forwarded-For` with the connecting peer (overwrites, not appends: otherwise a client picks the
  address it is counted against) and uvicorn runs with `--proxy-headers`, trusting every peer
  because the app container publishes no ports and Caddy is the only thing that can reach it.
- Secrets are scoped per container rather than per host: only the app reads the full environment
  file, while Caddy gets a hostname and Litestream gets bucket credentials. A stock reverse proxy
  has no business holding the token-signing key.

Detection is proportionate: an uptime monitor on the public endpoint and a CPU alert (a miner's
signature is sustained load on a machine that idles 95% of the time).

## Decision 6: Email becomes real, minimally

`OutboxMailer` remains the default so `dev.sh` behaviour is unchanged; production sets SMTP
variables and gets `SmtpMailer`. Selection is by configuration presence, not a mode flag — if
`HEMA_SQUIRE_SMTP_HOST` is set, mail is real. Any EU transactional SMTP endpoint works; the app
knows nothing but host, port, credentials and STARTTLS.

## Decision 7: The restore is only rehearsed if it uses off-host material

Continuous replication covers the database, but a new host also needs `deploy/.env` — signing key,
SMTP and replica credentials — and that file exists nowhere else. So the filled `.env` lives in a
password manager, and the drill (task 5.1) restores using that copy rather than the production
host's. Otherwise the rehearsal quietly depends on the thing whose loss it is rehearsing.

The same reasoning applies to detection: a Litestream that dies, or meets a rotated key, fails
silently — the app keeps serving and the host keeps idling, so neither the uptime monitor nor the
CPU alert moves, and "loss bounded by seconds" degrades to "loss bounded by whenever someone last
looked". Replication therefore gets its own check on the age of the newest generation.

## Deploys and rollback

`deploy.sh` is `git pull && docker compose up -d --build` over SSH: reproducible, seconds of
downtime, rollback = check out the previous tag and rerun. Alembic migrations run in the app
container entrypoint before uvicorn starts, so a deploy is atomic from the operator's view. The
one operational rule this imposes: don't deploy during a tournament's opening minutes — which is a
calendar entry, not a technology.
