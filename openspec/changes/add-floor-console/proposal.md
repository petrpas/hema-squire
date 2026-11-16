## Why

The tournament day needs a workplace of its own. The office console already has nine
phases, and adding eight tournament-day steps to it would bury both. The two owner
documents "HEMA Squire: formalizace plánovače turnaje" and "HEMA Squire: UX konzole pro
den turnaje" (2026-11-16) describe a second console beside the office one. Every later
floor change needs two things from it: its shell, and the facts the planner reads.
- **The shell:** the address, the fixed tab order and the tab badges.
- **The facts the planner reads:** days, pistes, discipline formats, officials and the
  organizer's parameters.

This change builds both. It plans nothing yet.

**Context:** floor. It touches the office in four places:
- `tournament_delete.py`, so a tournament's floor rows go with it;
- `account_deletion.py`, so floor columns are classified;
- the office console's header, which gets a link to the floor;
- `alembic/env.py`, so the floor tables are registered.

None of these imports `app.floor`. Without them a floor table would block a tournament's
deletion and break the classification test.

## What Changes

- **A second console** at `/organizer/:slug/floor/:phase` with eight tabs in a fixed
  order: `setup`, `data`, `plan`, `today`, `checkin`, `pools`, `bracket`, `results`.
  - All eight tabs are always present, and they are never reordered. What varies is
    their content: team sections appear only on a tournament with a team discipline.
  - A badge on a tab means "something here is waiting for you".
  - The tabs after `data` are placeholders until their changes land.
  - On a wide screen a schedule panel stands beside the work. On a narrow screen it
    becomes the last tab.
- **Floor Setup (`setup`)** stores:
  - the tournament's days: date, start, end, fixed breaks;
  - its pistes: name, availability per day, `reserve` mark, optional tag;
  - per discipline, its format: pool size range, the advancing count (always set,
    default all), bracket kind, third-place bout, piste staffing template, slot
    lengths;
  - its officials: name, optional link to a roster person, roles, disciplines they may
    officiate, availability per day;
  - the organizer's parameters: preferences and estimate constants, each with a
    default.

  One field, one editor: these parameters are edited here and nowhere else.
- **Data (`data`)** shows the floor roster live, per discipline. Entrants come from the
  office only. A tournament whose list is kept by the organizer gets a link to the
  office Import phase (decision 2026-11-16). This change adds no import of the floor's
  own.
- **The floor roster gains two facts.** It states each discipline's stable id and the
  tournament's date and timezone. Floor tables refer to a discipline by its id, not by
  its slug, because a slug is editable until someone enters the discipline.
- **First floor tables**, in `app/floor/models.py` with migration `floor_0001`:
  `floor_days`, `floor_pistes`, `floor_piste_days`, `floor_formats`, `floor_officials`,
  `floor_official_days`, `floor_settings`.
- **A "Den turnaje" link** in the office console's header. It is shown to the
  organizer of a tournament that has at least one discipline. A discipline-less event
  has no floor.

## Capabilities

### New Capabilities
- `floor-console`: the tournament-day console's address, tab set and order, badges,
  the schedule panel slot, and who may open it.
- `floor-setup`: days, pistes, discipline formats, officials and parameters. Covers
  what each holds, its defaults, and how it is validated.
- `floor-data`: the Data tab, which shows the live floor roster and points to where
  entrants come from.

### Modified Capabilities
- `floor-roster`: adds each discipline's id and the tournament's date and timezone to
  the roster. It also adopts the office's identity rule for team members: one person
  by equal HEMA Ratings identifier, or by folded name where either has none (owner
  decision 2026-11-16). This replaces the confirmed-identifier-only join of
  `add-floor-boundary`.

## Impact

- **New backend files:**
  - `app/floor/models.py`;
  - `app/floor/setup.py` (the setup service);
  - additions to `app/floor/api.py` and `schemas.py`;
  - migration `alembic/versions/floor_0001_*`.
- **Office edits:**
  - `app/tournament_delete.py`: deletes every table whose name starts with `floor_` by
    metadata. No import of `app.floor`.
  - `app/account_deletion.py`: string classifications for the floor columns.
  - `alembic/env.py`: registers `app.floor.models`.
  - `app/floor/adapters/office.py`: the two new roster facts.
- **Frontend:**
  - new `frontend/src/floor/` with `FloorConsole.tsx` and one directory per tab;
  - `routes.ts` gains `floorPath(slug, phase?)`;
  - `App.tsx` gains two routes;
  - the office console header gains the link.
- **API:** `GET/PUT /api/tournaments/{slug}/floor/setup/*`, all behind the console gate.
- **Out of scope:** no planner, check-in, pools or results.
