## 1. Code hardening (five commits, each independently landable)

- [x] 1.1 `backend/app/db.py`: add `apply_sqlite_pragmas(engine)` registering an
      `@event.listens_for(engine, "connect")` listener that issues `PRAGMA journal_mode=WAL`,
      `PRAGMA busy_timeout=5000`, `PRAGMA synchronous=NORMAL`, `PRAGMA foreign_keys=ON`, guarded by
      `settings.database_url.startswith("sqlite")`; call it on the module-level engine. A function
      rather than an inline listener because the test suite builds its own engine and must run under
      the same pragmas — see 1.2. Implemented with `journal_mode` moved out of the per-connect
      listener: it is a property of the file, and SQLite refuses the switch with "database is
      locked" immediately — without consulting `busy_timeout` — while another writer holds a lock,
      which would turn a moment of contention into connections that fail before serving anything.
      It is therefore set once at engine setup; the listener carries only the session pragmas
- [x] 1.2 `backend/tests/conftest.py`: call `apply_sqlite_pragmas` on the `engine` fixture, so the
      whole suite runs with foreign keys enforced and integrity violations surface in CI rather than
      in production. Then add a test: two sessions, one holding an open write transaction, the other
      performing a write — asserts the second waits rather than raising `OperationalError: database
      is locked`; and a FK test asserting an insert referencing a missing parent is rejected.
      Verified ahead of implementation: the 612-test suite already passes with `foreign_keys=ON`, so
      this is a guard against regression, not a cleanup job
- [x] 1.3 `backend/app/config.py`: add `debug: bool = False`; `backend/app/main.py` lifespan:
      raise `RuntimeError` when `settings.secret_key` equals the dev default and `not settings.debug`;
      `dev.sh` exports `HEMA_SQUIRE_DEBUG=1`. `conftest.py` sets `HEMA_SQUIRE_DEBUG=true` beside the
      existing scheduler/HR lines — every API test boots the app through `TestClient`, so without it
      the guard fails the entire suite. Test both branches
- [x] 1.4 `backend/pyproject.toml`: add `slowapi`; `backend/app/main.py`: wire `Limiter` with
      remote-address key; `backend/app/routers/auth.py`: `5/minute` on login, `3/minute` on signup.
      The address must be the real client: every request arrives from Caddy's container address, so
      an unforwarded key throttles the whole internet as one bucket. The Caddyfile overwrites
      `X-Forwarded-For` with the connecting peer and the Dockerfile runs uvicorn with
      `--proxy-headers --forwarded-allow-ips='*'` (safe: the container publishes no ports). Test:
      a sixth login attempt from one forwarded address receives 429, and a request from a different
      forwarded address in the same window still succeeds. Implemented with the limiter in
      `app/ratelimit.py` (both `main` and the auth router import it, which a limiter defined in
      `main` could not be) and a `rate_limit_enabled` setting the suite turns off — the existing
      tests sign up far more than three accounts a minute from one address
- [x] 1.5 New `backend/tests/test_tenant_isolation.py`: create two tournaments with distinct owners;
      parameterize over every console-scoped route (47 discovered) and assert tournament B's
      organizer is refused on tournament A's resources. This test is the standing guard on the
      multitenant boundary — new console endpoints join it by existing. Two deviations from the
      task as written, both forced by what the code actually does:
      (a) discovery cannot walk `app.routes`: this FastAPI version includes routers lazily, so
      `app.routes` holds `_IncludedRouter` wrappers and yields zero endpoints. Discovery recurses
      into the included routers instead, and identifies console scope by finding
      `require_console_access`/`require_tournament_owner` in the handler source.
      (b) refusal is asserted as 403 exactly, not 403-or-404. Verified by neutralizing the checks
      across the app: all 47 routes then answer 404 (the handler runs and fails to find a
      sub-resource) except `DELETE /api/tournaments/{slug}`, which answers 204 and deletes another
      organizer's tournament. Accepting 404 would have left the test green through the removal of
      46 of 47 checks; requiring 403 makes it fail on all 47. Endpoints whose body validation would
      answer 422 before the check runs carry a request body in the test's `BODIES`/`FILES` tables,
      and a new one without an entry fails loudly rather than passing vacuously
- [x] 1.6 `backend/app/mail.py`: add `SmtpMailer` (stdlib `smtplib`, STARTTLS); `get_mailer()`
      returns it when `settings.smtp_host` is set, `OutboxMailer` otherwise; `config.py` gains
      `smtp_host`, `smtp_port=587`, `smtp_user`, `smtp_password`. Test selection logic; send path
      by stubbed SMTP

## 2. Deployment artifacts (in `deploy/`, drafted with this change — review, don't rewrite)

- [x] 2.1 Review `Dockerfile`: three stages (node build of `frontend/`, python backend via `uv sync
      --frozen`, caddy with `dist/` at `/srv`); backend entrypoint runs `alembic upgrade head`
      then `uvicorn --workers 1 --proxy-headers`. The base image tracks
      `backend/pyproject.toml`'s `requires-python` — bump both together or `--frozen` fails.
      Both targets built locally (podman): `uv sync --frozen` installs 63 packages on 3.14, the
      frontend stage emits `dist/`. Base images are fully qualified (`docker.io/library/...`)
      because podman resolves bare names only through short-name aliases, which `caddy` lacks
- [x] 2.2 Review the root `.dockerignore`. Docker does not honour `.gitignore`, and the build
      context is the repository root: without it `COPY backend/ ./` lands the host `.venv` on top of
      the image's own and bakes local databases into the image. Verified in the built image:
      `/app` holds only the venv, `alembic/`, `app/`, `tests/` and the manifests, and
      `/app/.venv/bin/python` resolves to the image's own `/usr/local/bin/python3.14` — a
      host-copied venv would point into `/home/` and fail to import
- [ ] 2.3 Review `docker-compose.yml` (not yet exercised: the local runtime is podman, which has no
      `docker compose` plugin, so the first run of this file is the server): `app` (internal :8000, `/data` volume, `/secrets` read-only,
      healthcheck on `/api/health`), `web` (Caddy, 80/443, cert volume), `litestream` (shares
      `/data`, config mounted read-only); all `restart: unless-stopped`. Only `app` takes the full
      `env_file`; Caddy and Litestream receive the two and five variables they need, so the signing
      key and SMTP password stay in one container. Litestream is pinned to `0.5.16` and
      `restore.sh` uses the same tag: 0.5 replaced the remote format, so a 0.3 binary cannot read a
      0.5 replica
- [x] 2.4 Review `Caddyfile`: site address from `$SITE_ADDRESS`, `/api/*` proxied, SPA fallback,
      `X-Forwarded-For` overwritten rather than appended (a client must not choose the address the
      throttle counts against). `caddy validate` reports the config valid with one warning calling
      that `header_up` unnecessary; the warning assumes passthrough is the intent and is expected
      here — removing the line to silence it reintroduces the appended, client-influenced header,
      and with a single value the address is correct whichever end of the list uvicorn reads
- [ ] 2.5 Review `litestream.yml`: written for Litestream 0.5.x — single `replica`, retention in the
      global `snapshot` block (672h; days are not a valid unit), periodic validation, credentials and
      region from environment. The 0.3-era shape (`replicas:` list with a per-replica `retention:`)
      is silently not read by 0.5, so config and image version move together
- [ ] 2.6 Review `cloud-init.yaml` and fill the SSH public key placeholder. Note the top-level
      `groups: [docker]`: cloud-init creates no groups implicitly and Docker is installed later, so
      removing it makes `useradd` fail — no SSH on a key-only host
- [ ] 2.7 Copy `.env.example` → `.env` on the server (`chmod 600`) and fill: `HEMA_SQUIRE_SECRET_KEY`
      (`openssl rand -hex 32`), `HEMA_SQUIRE_OWNER_EMAIL`, SMTP credentials, R2/B2 endpoint,
      bucket, region and scoped keys, `SITE_ADDRESS=hemasquire.eu`. Store the filled file in the
      password manager at the same time — a new host cannot boot without it

## 3. Provider setup (console clicking, ~30 minutes)

- [ ] 3.1 Create the object-storage bucket (Cloudflare R2 or Backblaze B2), private, with an API
      key scoped to that bucket only. Note the region value the provider expects (`auto` for R2) —
      it goes in `REPLICA_REGION` and into the restore URL
- [ ] 3.2 Create the CX23 (Falkenstein/Nuremberg) with `cloud-init.yaml` as user data
- [ ] 3.3 Attach a Hetzner Cloud Firewall: inbound 22/80/443, nothing else
- [ ] 3.4 Point `hemasquire.eu` A/AAAA records at the server

## 4. First deploy

- [ ] 4.1 Clone the repo to `/opt/hema-squire`, place `.env`, `mkdir -p deploy/secrets` (with the
      Google service-account JSON if the Sheets export is wanted; an empty directory disables it),
      run `docker compose -f deploy/docker-compose.yml up -d --build`
- [ ] 4.2 Run `PRAGMA foreign_key_check` against the production DB once (empty result expected on
      a fresh DB; on any migrated data, resolve findings before proceeding)
- [ ] 4.3 Verify: HTTPS answers on the domain, `/api/tournaments` responds, a signup round-trips,
      a reminder email arrives via SMTP, `litestream snapshots` lists a generation in the bucket.
      Confirm the throttle keys on the client by exceeding the login limit from one address and
      succeeding from another. First boot also populates the fighters index in the background
      (`hr_auto_refresh`), which takes a while and is not a failure

## 5. Restore drill and monitoring (definition of done)

- [ ] 5.1 On a scratch machine (or locally), run `deploy/restore.sh` against the production
      replica and boot the app on the restored file (the script runs a full integrity check as part
      of the restore); verify a known registration is present. Use the
      password-manager copy of `.env`, not the production host's — the drill proves recovery only if
      it uses material that survives the host. Record the date in `deploy/README` — the drill
      repeats when the stack changes materially
- [ ] 5.2 Register `/api/health` with an uptime monitor; add a Hetzner console CPU alert (sustained
      high load on an idle-by-design machine is the compromise signature); and add a replication
      check — a Litestream that dies or meets a rotated key fails silently, and neither uptime nor
      CPU moves. A daily `litestream snapshots` whose newest generation is older than a day, or an
      alert on the container's restart count, is enough
- [ ] 5.3 Add a calendar rule, not a technical control: no deploys during a tournament's opening
      window
