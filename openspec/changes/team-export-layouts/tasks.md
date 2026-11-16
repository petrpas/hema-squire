## 1. Sheets: flat team worksheet (backend)

- [ ] 1.1 `exporttables.py`: add `team_fighter_rows(table)` turning a team tab's mixed
      rows into flat rows (design D3). One row per fighter, or one empty row for a
      team with no fighters, each with `_team_cells` = number, name, paid. Teams are
      numbered in `team_entries` order straight across the line
- [ ] 1.2 `sheets_export.py`: add `TEAM = Column("team", refreshed=True)` and
      `TEAM_DISCIPLINE_COLUMNS`, and replace `_team_fighter_values` with `_team_values`
      filling them from the flat rows. No entering fencer, no member count
- [ ] 1.3 `merge_grid`: take an identity function and a per-worksheet `refreshed` set
      (D4). The team worksheet uses team+fighter identity, refreshes position, team
      and paid, and skips the 1..n renumbering. Every other worksheet keeps today's
      behaviour
- [ ] 1.4 Old-shape detection (D5): an existing team grid without a `TEAM` label in
      any locale is discarded and written whole
- [ ] 1.5 Backend catalog: `export.column.team` (`Tým` / `Team`) and
      `export.roster.team`
- [ ] 1.6 Tests in `tests/test_sheets_export*.py` (or the existing team export test
      file): a re-export leaves team rows in place and keeps a hand-typed club; a
      fighter on two teams keeps two rows across two exports; an empty team is one
      row; team cells stand on every row; an old-shape worksheet is rewritten once;
      an individual worksheet is unaffected (still renumbered 1..n, paid not
      refreshed)

## 2. Print: team roster template (backend)

- [ ] 2.1 `typst/templates/team_roster.typ`: eight columns (No., Team, Fencer, Nat.,
      Club, HRID, Rank, Paid), same page, font and frame as `discipline_roster.typ`,
      a thin rule above each `team_starts` index but the first, the heavier rule
      under `last_in`. All text read from `sys.inputs`
- [ ] 2.2 `rosterprint.render`: a `template` argument and `team_starts` passed
      through. `ExportRosterIn` gains optional `team_starts: list[int]`
- [ ] 2.3 `export_roster`: choose the template and headers by `discipline.kind`;
      answer 422 `roster_width` when a row's width does not match the kind
- [ ] 2.4 Tests: a team roster renders to PDF and PNG with eight English headers
      under the English tick; Typst syntax in a team name prints as text; a
      seven-cell body for a team discipline is refused with 422; the individual
      roster is unchanged

## 3. Print and copy: flat team rows (frontend)

- [ ] 3.1 `export/roster.ts`: for `tab.teams`, flatten `teamOrder`'s rows into one
      row per fighter, with team cells on the first fighter's row only and an empty
      team as one row. Send `team_starts` and a `line_after` counted in flat rows.
      Retire `TEAM_PRINT_COLUMNS`
- [ ] 3.2 `export/columns.ts`: `TEAM_COPY_COLUMNS` (position = team number, team,
      name, nat, club, hr_id, rating, rank, paid) over flat rows with team cells on
      every row. `ExportTables.tsx` uses them for the copy on a team tab.
      `TEAM_COLUMNS` keep their columns (the team row's name cell is 4.1)
- [ ] 3.3 `api.ts`: `RosterPrint.team_starts?: number[]`. i18n
      `export.column.team` in `cs.json` and `en.json`
- [ ] 3.4 Tests in `roster.test.tsx` / `exportTables.test.tsx`: the print body has
      eight cells per row, team cells only on first rows, `team_starts` and
      `line_after` in flat rows; the copy of a team tab is flat with team cells on
      every row and follows active-only; no entering fencer or count in either

## 4. Console team tab and the ratings statement

- [ ] 4.1 `TeamRosterTable.tsx`: a team row's name cell is the bold team name under
      the console's hint element stating who entered it (D7). No member count.
      Remove `export.team.members` if nothing else reads it
- [ ] 4.2 Alembic migration adding nullable JSON `hr_rating_snapshots.hr_ids`;
      `take_snapshot` writes the identifiers it asked for (D8)
- [ ] 4.3 `export_table`: `ratings_fetched_at` and `ratings_missing` for a
      discipline tab, counted over its unfiltered fighter rows. Handle no
      snapshot and an old snapshot with `hr_ids` null as D8 says
- [ ] 4.4 Rail card of a discipline tab: the statement beside the refresh, in `cs`
      and `en`, with plural forms
- [ ] 4.5 Tests: backend — no snapshot counts every bound fighter; a member bound
      after the snapshot is missing; a fighter asked but unrated is not; an old
      snapshot falls back. Frontend — the team row shows no "entered by" or
      count, the hint names the entering fencer, and the card states the moment
      and the count

## 5. Finish

- [ ] 5.1 `backend/`: `uv run ruff check .`, `uv run basedpyright`, scoped `pytest`
- [ ] 5.2 `frontend/`: `npm run typecheck`, `npm run check`, `npm test`
- [ ] 5.3 Render a sample team roster PNG and look at it; export a team discipline
      to a scratch spreadsheet twice and confirm the rows stay put
- [ ] 5.4 Sync the delta specs into `openspec/specs/` and archive
