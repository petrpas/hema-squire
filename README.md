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
scratch.

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
cd backend && uv run pytest     # 137 tests; ruff check . for lint
cd frontend && npm run build    # type-check + build
```

The pilot-replay test (`test_pilot_naduel.py`) runs only where the private
v1 archive exists and is skipped elsewhere.
