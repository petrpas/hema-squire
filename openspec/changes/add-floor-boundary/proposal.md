## Why

Squire's next module runs the tournament day: check-in, pools, brackets and
scheduling. We call it the "floor", because that is where the fencing happens.
It will grow faster than anything before it. If it reads `Registration`, `Team`
and the payment tables directly, the office's rules end up stated a second time,
and the two copies drift. The boundary has to exist before the first floor
feature does, so this change builds only that: the module's place in the repo,
the one way it reads entrants, and the checks that keep both in place.

**Context:** floor. This change also touches the office, in the edits listed
under Impact. Without them the floor cannot read the same answer the public
roster gives, so it would have to rebuild it.

## What Changes

- New package `backend/app/floor/`:
  - `roster.py`, the port: frozen dataclasses for persons, individual entries
    and team entries.
  - `adapters/office.py`, the one floor file that reads office modules. It
    builds the port from the replay for a tournament.
  - An empty `engine/` for pure code.
  - `api.py` and `schemas.py`.
- One read-only endpoint, `GET /api/tournaments/{slug}/floor/roster`, behind
  the same console gate as `GET /api/tournaments/{slug}/export/tables`.
  Mounted in `app/main.py`.
- A boundary checker built on `ast`, in `tests/floor/test_floor_boundary.py`.
  Its own tests show each of the four rules failing on a synthetic offender.
- A contract test asserting, per discipline, that the floor roster's entrants
  are the public roster's seated entrants.
- `CLAUDE.md` gains a "Floor module" section, and its test-scope examples name
  directories that exist.
- `openspec/config.yaml` gains `context` and per-artifact `rules` for the two
  contexts.
- Office edits, all additive:
  - `entrants._live_registration_ids` is renamed to the public
    `live_registration_ids`.
  - `exporttables.TeamEntry` gains `registration_id`. The owner approved this
    one outside the brief's list.

Nothing is stored: there are no floor tables and no migration.

## Capabilities

### New Capabilities
- `floor-roster`: what the floor knows about a tournament's entrants (persons,
  individual entries, team entries), how it is derived from the office replay,
  and the read-only endpoint that serves it.

### Modified Capabilities
None. The boundary rules are enforced by a test and stated in `CLAUDE.md`. They
are not a capability.

## Impact

- New: `backend/app/floor/**` and `backend/tests/floor/**`. The tests are the
  suite's first subdirectory, and their basenames are prefixed `test_floor_`,
  because the suite has no `__init__.py`.
- Office edits:
  - `app/main.py`: mounts the router.
  - `app/entrants.py`: one rename, with its one caller.
  - `app/exporttables.py`: one field on `TeamEntry` and one line filling it.
- Docs and config: `CLAUDE.md`, `openspec/config.yaml`.
- API: one new GET endpoint. It falls under the schemathesis contract suite
  automatically, through the existing seed.
- No new dependency, no migration, no frontend.
