## Why

A team discipline leaves the Export phase through the shape built for an
individual one, and every exit shows it. The printed roster crams the team, the
fencer who entered it and its member count into the Fencer column of the
seven-column individual template, and puts console-only facts on a sheet meant
for the noticeboard. The spreadsheet write merges team rows by an identity that
never matches what it wrote, so every re-export moves the team rows to the
bottom of the worksheet, away from their fighters, and drops whatever staff
wrote into them. It numbers fighters as though they were teams, and drops a
fighter named on two teams as a duplicate. The `data-export` spec meanwhile
still says a team discipline writes no worksheet at all, so spec and code
disagree.

## What Changes

- A team discipline's roster prints from its own Typst template: a flat table
  headed No. | Team | Fencer | Nat. | Club | HRID | Rank | Paid, one row per
  fighter. The team's number, name and paid stand on the team's first row only,
  and a rule separates one team from the next. The entering fencer and the
  member count against the bounds are not printed; the console keeps them.
- A team discipline's worksheet in Google Sheets and its clipboard copy become
  flat: one row per fighter, the team's number, name and paid repeated on every
  row, so the sheet filters and sorts without breaking a team apart.
  **BREAKING** for a worksheet already written in the mixed team-row/fighter-row
  shape: its first export in the new shape rewrites it whole, and what staff had
  typed into it is lost once.
- A worksheet row of a team discipline is identified by its team and its
  fighter, so a re-export keeps each row and its hand-written cells. A fighter
  on two teams has a row under each.
- A team with no fighter on its roster yet is one row, its fighter cells empty.
- The `data-export` spec states the team worksheet instead of denying it.
- The console's team tab on screen is unchanged: teams with their fighters
  beneath them, the entering fencer and the member count in the team's row.

## Capabilities

### New Capabilities
<!-- none -->

### Modified Capabilities
- `roster-print`: a team discipline prints from its own template, with its own
  columns, and without the entering fencer or the member count.
- `export-tables`: a team discipline tab's clipboard copy is flat, one row per
  fighter with the team's cells repeated. The screen keeps its team rows.
- `data-export`: the Sheets export writes a team discipline's worksheet, flat
  and identified by team and fighter. A worksheet still in the mixed shape is
  rewritten once.

## Impact

- `backend/app/typst/templates/`: a new `team_roster.typ` beside
  `discipline_roster.typ`. `backend/app/rosterprint.py` and the
  `export/roster.{fmt}` route in `backend/app/routers/export_api.py` choose the
  template by the discipline's kind, with eight headers for a team.
- `backend/app/sheets_export.py`: team worksheet columns, values, identity and
  the one-time rewrite of an old-shape worksheet.
  `backend/app/exporttables.py` gets a flat team-fighter row view.
- `frontend/src/export/roster.ts` and `frontend/src/export/columns.ts`: the
  team print columns and the flat team copy columns. `TeamRosterTable` and the
  on-screen `TEAM_COLUMNS` are unchanged.
- i18n: a `Team` header in `cs`/`en` for both the frontend and the backend
  catalog.
- No migration, no API shape change beyond the roster print body's row width
  for a team discipline.
