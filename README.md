# HEMA Squire

An application for HEMA tournament agenda: fencer accounts, registration with
payment lifecycle (VS matching, SPAYD QR, Fio bank integration), an organizer
ETL console with a replayable rules engine, LLM table import and HR matching,
and exports (canonical JSON, Google Sheets in the v1 format).

Specs live in `openspec/specs/`; the project follows the OpenSpec workflow
(`openspec/changes/` for work in flight, archive for history).

## Local run

```bash
./dev.sh            # backend :8000 + frontend :5173
./dev.sh --seed     # …plus a demo tournament to click through
```

Requirements: [uv](https://docs.astral.sh/uv/) and Node 18+. The script
installs dependencies, applies migrations, starts FastAPI (with reload) and
Vite, and stops both on Ctrl+C.

With `--seed` you get the **Na Duel! 2026** demo tournament — organizer login
`petr@example.com` / `demo-heslo-123` at <http://localhost:5173>: a complete
Setup (location, titular organizers, an open registration window, itemized
pricing with extra services across categories, a discipline-count discount,
and an early-bird percent discount), four in-app registrations exercising
that pricing (one paid via a simulated Fio statement), an imported
Google-Form table, and problems to review in the console. Use the picker's
"New tournament" button to try the creation flow and the Setup phase from
scratch. The seed also creates an Admin demo account (`admin@example.com` /
`demo-heslo-123`) — see its printed output for the full set of demo logins
and roles.

## Roles

Every account holds one global role, ranked **Fencer** (default) <
**Organizer** < **Admin**, plus a deployment **Owner** computed from
`HEMA_SQUIRE_OWNER_EMAIL` (never stored — it applies to whichever account
signs up with that address, even after deployment, and outranks everyone
including Admin):

- **Fencer** — every account; can register for open tournaments.
- **Organizer** — can additionally create tournaments; granted and revoked
  by an Admin, or self-requested through an in-app plea that an Admin
  grants or denies.
- **Admin** — manages people: account roles (except Admin itself, which
  only the Owner grants), the plea queue, and admin HR-profile unbinding.
- **Owner** — one per deployment; all capabilities, and the only one who
  can grant or revoke Admin. Set `HEMA_SQUIRE_OWNER_EMAIL` in
  `backend/.env` to the account's e-mail.

Separately, each *tournament* has one **Tournament Owner** (its creator,
transferable to a team member) and a team of **Tournament Organizers** the
owner adds by e-mail — this is what grants console access to a specific
tournament and is independent of the global role above. A deployment Admin
does not automatically get console access to tournaments; Admins manage
people, not tournaments.

**Upgrading an existing deployment:** the migration backfills each
tournament's `owner_id` from its earliest console team member, but grants no
global roles — every existing account starts as a plain Fencer and loses the
ability to create new tournaments until an Admin (or the Owner) grants it
Organizer through the admin panel. Set `HEMA_SQUIRE_OWNER_EMAIL` first so an
Owner account can sign in and start granting roles.

Notes for a full-feature run:

- **HR fighters index** downloads automatically from hemaratings.com on first
  start (~20k fighters); search and matching work right after.
- **LLM features** (table parse, fuzzy HR matching, dedup) need
  `HEMA_SQUIRE_ANTHROPIC_API_KEY` — put it in `backend/.env`. Without it the
  seed backfills parse decisions so the console still shows parsed rows.
- **Google Sheets export** needs `HEMA_SQUIRE_GOOGLE_CREDENTIALS_PATH`
  (service-account JSON) and an output-sheet URL set in the Export phase.
- Outgoing e-mail lands as `.eml` files in `backend/outbox/` (no real
  provider configured yet).

## Tests

```bash
cd backend && uv run pytest     # 177 tests; ruff check . for lint
cd frontend && npm run build    # type-check + build
```

The pilot-replay test (`test_pilot_naduel.py`) runs only where the private
v1 archive exists and is skipped elsewhere.
