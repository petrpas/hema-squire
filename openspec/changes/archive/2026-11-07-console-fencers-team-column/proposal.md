## Why

On a tournament with team disciplines the console's fencer list says who registered
and nothing about what they entered a team as. The teams are visible only on the
Teams phase, which is grouped by discipline, so answering "which team is this row
in" means leaving the list and reading another view back to front. The organizer
reads the fencer list as the tournament's register; the team a row entered belongs
beside the club it belongs to.

## What Changes

- The Fencers phase's table gains a **Team** column, directly after Club.
- The column states, per row, every team that row's registration entered: the
  team name followed by its discipline in parentheses, one team per line. A row
  entering two teams in two disciplines reads `Rudá růže (LS)` above
  `Ulice 2 (SB)` — the discipline is what separates two teams that would
  otherwise be two bare names.
- The column is offered only where the tournament has a team discipline: the team
  disciplines feature on **and** at least one team discipline configured. A solo
  tournament's table does not widen.
- The column is read-only, as the Teams view is. A team's name is the entering
  fencer's, corrected in their own roster editor, and a cell edit here would make
  a correction the roster never saw.
- A row with no team — an imported row, a manual row, a fencer who entered only
  individual disciplines — reads a dash, as an empty club does.
- The console sheet's rows carry the teams their registration entered, so the
  column reads a stated fact rather than deriving one.

What does not change: a team's *members* are local roster names and not
registrations, so they do not appear on the fencer list and this column never
claims to show "the team this person fights for" — it shows the teams this row
entered. The Export tables, the public entrants rosters and the Teams view are
untouched.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `etl-console`: the fencer table's columns — the Fencers phase states, after
  Club, the teams each row entered, where the tournament has a team discipline.

## Impact

- `backend/app/sheet.py` — each registration row carries its entered teams
  (name and discipline slug); imported and manual rows carry none.
- `backend/app/schemas.py` — the sheet row's shape gains that field.
- `frontend/src/api.ts` — `SheetRow` gains the field.
- `frontend/src/Console.tsx` — where the column is offered, and how its cell
  renders; the column is not editable.
- `frontend/src/SheetArea.tsx` — the column list is no longer base columns plus
  the phase's own.
- `backend/app/locales/{cs,en}.json` — the column's label.
- No migration: the field is derived from `teams` rows that already exist.
