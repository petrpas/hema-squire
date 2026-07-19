## 1. Data model and pricing

- [x] 1.1 Add Tournament columns `location`, `organizer_names` (JSON list), `discounts` (ordered JSON list), `registration_opens`, `registration_closes`; new `extra_items` and `registration_extras` tables in `models.py` with an Alembic revision (nullable/defaulted; existing rows stay valid)
- [x] 1.2 Extend `schemas.py`: setup fields on `TournamentUpdate`/`TournamentOut`, extra-item and discount shape validation (known category/condition/effect kinds, fees ≥ 0, percent ≤ 100, `max_qty` ≥ 1), `setup_missing` on the detail payload
- [x] 1.3 Rewrite `pricing.py` around itemized computation: item sum → scoped fixed discounts (floor 0) → sequential scoped percent discounts → single half-up rounding; legacy path when no items and no discounts; unit tests for count discount, early-bird percent, scope grouping, rounding, quantity extras, and legacy-path equivalence
- [x] 1.4 Implement `setup_missing(tournament)` helper with stable item keys (location, organizers, disciplines, discipline_prices); unit tests for each missing item

## 2. Backend gating and endpoints

- [x] 2.1 Gate registration submission: setup complete → window open (opens ≤ today ≤ closes-or-tournament-date); distinct 4xx reasons for not-published / not-yet-open / closed
- [x] 2.2 Registration endpoint accepts per-item extras selections (`extra_item_id`, `qty`), validates `qty ≤ max_qty`, persists `registration_extras`; legacy tournaments keep the fixed weapon-rental/afterparty inputs
- [x] 2.3 Expose setup data in tournament detail (including `setup_missing`, extra items, discounts) and accept the new fields via PATCH + extra-item CRUD; keep `POST /api/tournaments` unchanged and verify slug-collision 409 surfaces cleanly
- [x] 2.4 Itemize confirmation email summary from selections (`emails.py`); extend canonical JSON export; map `rental`/`afterparty` category items to the v1 sheet columns in `sheets_export.py` (others to a summary column)
- [x] 2.5 Backend tests: gating matrix (incomplete/complete × before/inside/after window), PATCH round-trip of setup fields, extras selection validation, legacy tournaments unaffected end-to-end

## 3. Frontend — creation and Setup phase

- [x] 3.1 "New tournament" dialog on `TournamentPicker`: name + date, slug auto-derived and editable, create then enter console on Setup
- [x] 3.2 Add `setup` as first phase in the console rail; Setup renders configuration panels instead of the fencer table
- [x] 3.3 Setup identity section: display name, date, location, language, registration opens/closes
- [x] 3.4 Titular organizers table (freetext rows, add/remove) saving `organizer_names`
- [x] 3.5 Disciplines table: taxonomy dropdown + capacity + unit price, add/remove rows against the existing discipline endpoints
- [x] 3.6 Extra-services table: freetext name, category dropdown, price, quantity limit, add/remove rows
- [x] 3.7 Discounts table: name, condition (count N / before date), effect (fixed / percent), add/remove rows; no scope picker (scope stored with default); warn when editing pricing on a tournament with registrations
- [x] 3.8 Descoped by owner decision (2026-07-19): fencer-facing registration form deferred to a follow-up change (`add-public-registration`) — this repo has no fencer-facing UI and registration has always been API-only. Backend support (gating, extras selection/validation, itemized email) implemented and tested in 2.1/2.2/2.5.
- [x] 3.9 Completeness checklist bound to `setup_missing`
- [x] 3.10 i18n: cs + en catalogue entries for all new UI

## 4. Seed, docs, verification

- [x] 4.1 Seed: demo tournament gets location, titular organizers, an open registration window, and itemized pricing (extras across categories, count discount, early-bird percent discount); pilot replay fixture stays per-discipline (legacy-path regression)
- [x] 4.2 Full-suite verification: backend pytest (incl. determinism/pilot replay), ruff, frontend type-check/build; click through create → setup → register with extras in the dev app
- [x] 4.3 Update README notes if the demo flow changes
