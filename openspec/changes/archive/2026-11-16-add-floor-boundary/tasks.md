## 1. Instructions and config

- [x] 1.1 Add the "Floor module (tournament day)" section to `CLAUDE.md`, verbatim from the brief.
- [x] 1.2 In `CLAUDE.md` "Running tests", replace the `tests/payments` and `tests/registration` examples with scopes that exist, and add `tests/floor`.
- [x] 1.3 Add `context` and `rules` (`proposal`, `specs`, `design`) to `openspec/config.yaml`. The keys match the `spec-driven` artifact ids, so none is renamed. Confirm that `openspec instructions proposal --change add-floor-boundary --json` shows them.

## 2. Boundary check (written first, so the skeleton is built against it)

- [x] 2.1 `tests/floor/test_floor_boundary.py`: write an `ast` checker, `violations(paths, root) -> list[str]`, that resolves relative imports and `from app import x`, with rules 1–4 and their exceptions (`adapters/office.py`, `main.py`).
- [x] 2.2 Add a test that runs the checker over the real `app/` tree and expects none.
- [x] 2.3 Add tests that feed it synthetic offenders in `tmp_path`, one per rule, each in the `import app.x`, `from app import x` and relative forms, and assert each is reported. Add one test showing the two exceptions are not reported.

## 3. Office edits (only these)

- [x] 3.1 `app/entrants.py`: rename `_live_registration_ids` to `live_registration_ids` and update its callers.
- [x] 3.2 `app/exporttables.py`: add `registration_id: int` to `TeamEntry` and fill it in `team_entries` (owner-approved, design D6).

## 4. Package skeleton and port

- [x] 4.1 Create `app/floor/__init__.py`, `adapters/__init__.py` and `engine/__init__.py` (empty).
- [x] 4.2 `app/floor/roster.py`: frozen dataclasses `FloorDiscipline`, `Person`, `IndividualEntry`, `TeamEntry` and `Roster`, with tuple fields and no `app` imports (design D5).

## 5. Office adapter

- [x] 5.1 `app/floor/adapters/office.py`: write `roster(session, tournament) -> Roster`. It replays as `rosters()` does, then:
  - takes seated individuals from `table_rows` + `live_registration_ids` + `disciplines`;
  - takes seated teams from `team_entries`, less those in `removed_registration_ids`;
  - sets ratings and ranks per slug and paid from settled.
- [x] 5.2 Build persons by the D2 rule: confirmed `hr_id` joins across populations, the anchor is the registration-backed row or the lowest member id, two registration-backed rows sharing an id block the join, and only persons holding an entry are listed.
- [x] 5.3 Re-export `SessionDep`, `FencerDep` and `TournamentDep` for `api.py`.

## 6. Endpoint

- [x] 6.1 `app/floor/schemas.py`: response models mirroring the port.
- [x] 6.2 `app/floor/api.py`: `GET /api/tournaments/{slug}/floor/roster`, gated by `require_console_access` + `require_published`.
- [x] 6.3 Mount the router in `app/main.py`.

## 7. Roster and API tests

- [x] 7.1 `tests/floor/test_floor_roster.py`: per discipline, the floor entrants equal `rosters()`'s seated entrants, over the `contract_seed` tournament.
- [x] 7.2 Repeat the 7.1 equality over fixtures for organizer-kept mode, queued fencers and a waitlisted team, a console correction, an unpaid seated fencer, and a removed registration's team.
- [x] 7.3 Add identity tests: one fencer in two disciplines; individual + member with confirmed `hr_id` joined; a proposed `hr_id` not joined; two registrations sharing an `hr_id` not joined.
- [x] 7.4 Add a test that building the roster writes nothing (rule, registration and row-number counts unchanged).
- [x] 7.5 `tests/floor/test_floor_api.py`: 200 for an organizer with the schema serialized, 403 for a stranger, 404 for an unknown slug, 409 for a draft.

## 8. Acceptance

- [x] 8.1 `pytest tests/floor -q` passes on its own; the contract suite still passes with the new endpoint.
- [x] 8.2 `uv run ruff check .` and `uv run basedpyright` pass.
- [x] 8.3 `openspec validate add-floor-boundary` passes.
- [x] 8.4 `git diff --stat` shows no file outside the allowed office edits, `app/floor/`, `tests/floor/`, `CLAUDE.md`, `openspec/config.yaml` and this change.
