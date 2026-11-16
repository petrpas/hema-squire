## Context

A team discipline's Export tab is one list holding two kinds of row, built by
`exporttables.table_rows` from `team_entries`. A team row carries `_team`, which
states its entering fencer, member count, bounds and waitlist position. Its
fighters' rows follow it and carry no `_team`. The screen (`TeamRosterTable`,
`TEAM_COLUMNS`) draws that well. Each of the tab's three exits reuses the
individual discipline's shape instead:

- **Print.** `roster.ts` maps the mixed rows through `TEAM_PRINT_COLUMNS`, which
  are the seven individual columns with the team's name, entering fencer and
  count folded into the Fencer cell. `export_roster` typesets them with
  `discipline_roster.typ`. The team cell wraps, nothing sets a team apart from
  its fighters, and console-only facts reach a posted sheet.
- **Sheets.** `_team_fighter_values` writes the same composite name cell under
  `DISCIPLINE_COLUMNS`. `merge_grid` identifies a row read back from the grid by
  its name cell, which is that composite. `_roster` identifies the row it is
  about to write by the bare team name. The two never match, so every re-export
  drops each team row and appends it at the bottom. A fighter on two teams has
  the same identity twice and the second is dropped. The position numbers
  every row.
- **Copy.** `toTsv` over `TEAM_COLUMNS` gives the same mixed shape as the screen.

Separately, `data-export` still states that a team discipline produces no
worksheet, and `export-tables`' clipboard requirement says the spreadsheet
carries no position column. Both contradict the code, and this change rewrites
both requirements.

Owner decisions (2026-11-16): flat print with a Team column, team cells on the
team's first row only. Print without the entering fencer or the member count.
Sheets and copy flat, team cells on every row. A team with no fighters is one
row. A worksheet in the old shape is rewritten once.

## Goals / Non-Goals

**Goals:**
- A team roster that reads as a posted list of teams and their fighters.
- A team worksheet that survives re-export with rows and hand-written cells in
  place, and that sorts and filters.
- One flat shape shared by Sheets and the copy.
- Specs that state what the code does.

**Non-Goals:**
- Changing the on-screen team tab, its ordering, its active-only filter or its
  capacity line.
- Team lines in the Summary (`export-summary` keeps none) or the Revenue.
- Per-team identity stable across a team's rename (see Risks).
- Seeding order on a team tab.

## Decisions

### D1 — A second Typst template, chosen by the server from the discipline's kind

Add `backend/app/typst/templates/team_roster.typ` beside `discipline_roster.typ`,
in the same page, font and frame. It takes eight columns and an extra input,
`team_starts`: the 0-based row indices where a new team begins, above each of
which (but the first) it draws a thin rule. `rosterprint.render` gains a `template`
argument (`"discipline" | "team"`). `export_roster` already resolves the
discipline from `body.discipline`, so it picks the template and the headers
(`_TEAM_ROSTER_HEADERS = position, team, name, nat, club, hr_id, rank, paid`)
from `discipline.kind`. It refuses a body whose rows do not have the width the
kind expects, with 422 `roster_width`, so a stale client fails loudly rather
than misprinting.

*Alternative:* one template with an optional team column. That was rejected
because the column widths, alignments and inter-team rule would all branch, and
the individual roster's established look (spec roster-print) is safer left
byte-for-byte alone.

### D2 — The client still formats the rows; it flattens a team tab before sending

Roster-print D1 stands: the printout is the tab as it stands, so the client sends
the rows in the tab's order and filter. For a team tab, `rosterPrint` walks
`teamOrder`'s rows and emits one row per fighter. The team's number, name and
paid go into the first fighter's row and the other rows leave them empty. A team
with no fighter emits one row with empty fighter cells. It sends `team_starts`
alongside the rows and computes `line_after` in flat rows, as the number of flat
rows belonging to teams above the line. The body gains an optional
`team_starts: list[int]`, which is ignored for an individual discipline.

### D3 — One flat row view for Sheets and copy, built where each already builds rows

- **Backend (Sheets).** `exporttables.team_fighter_rows(table)` turns the mixed
  team-tab rows into flat rows. Each flat row is the fighter's row, or an empty
  row for a team with no fighters, plus a `_team_cells` value carrying
  `number`, `name` and `paid`. Teams are numbered in the order `team_entries`
  lists them, seated then waitlisted, straight across the line as the tab
  numbers them. `export_to_sheets` uses `TEAM_DISCIPLINE_COLUMNS =
  [POSITION, TEAM, NAME, NATIONALITY, CLUB, HR_ID, RATING, RANK, PAID]` for a
  team tab, with `_team_values` filling them.
- **Frontend (copy).** `TEAM_COPY_COLUMNS` in `columns.ts` produces the same nine
  columns over a flat row list made by the same walk as D2, but with the team
  cells on every row. The copy action picks them for `tab.teams`. `TEAM_COLUMNS`
  stays the screen's.

The two implementations are deliberately parallel rather than shared: the
backend never sees the client's filter, and the Sheets export has always rebuilt
its rows server-side.

### D4 — Team worksheet identity is team name plus fighter

A new `TEAM = Column("team", refreshed=True)`. `merge_grid` takes an identity
function instead of the hard-wired `_identity(name, hr_id)`. For a team
worksheet the identity is `team:{fold(team)}|` + `_identity(name, hr_id)`, read
from the grid's team, name and HRID cells and computed the same way for the rows
about to be written. An empty team's row identifies as
`team:{fold(team)}|empty`. Every other worksheet keeps its current identity.

On a team worksheet, `POSITION` (now the team's number), `TEAM` and `PAID` are
refreshed. They describe the team, which the console owns, and a stale paid cell
is exactly what a re-export must not preserve. Because `PAID` is shared by every
worksheet, refreshing is decided per worksheet: `merge_grid` takes a
`refreshed: set[str]` of column ids, defaulting to the columns' own flags. This
replaces the bare `Column.refreshed` read, so no other worksheet changes
behaviour.

The final pass that renumbers `POSITION` 1..n is skipped for a team worksheet,
whose position is the team number written by the export.

### D5 — An old-shape team worksheet is detected by its missing team column

Before merging a team worksheet, if the existing grid is non-empty and its header
carries no label of `TEAM` in any locale (`_labels`), the grid is discarded and
the worksheet is written whole. That is the one-time rewrite the owner chose. It
needs no flag or stored state: once written, the header carries the column and
later exports merge.

### D6 — i18n

New keys: `export.column.team` (`Tým` / `Team`) in the backend catalog for Sheets
and for the print headers via `export.roster.team`, and `export.column.team` in
`frontend/src/i18n/{cs,en}.json` for the copy header. `export.team.enteredBy` and
`export.team.members` remain in use only by the screen.

## Risks / Trade-offs

- [A team renamed between exports loses its rows' hand-written cells, since its
  identity changes] → Accepted. A rename is rare after seeding begins. The rows
  are rewritten under the new name with current values, and nothing else is lost.
- [Two teams of one name in one discipline (allowed, team-disciplines D9) naming
  the same fighter collapse into one row on the sheet] → Accepted as vanishingly
  rare. The print and the copy are unaffected because they do not merge.
- [The one-time rewrite discards notes staff typed into an existing team
  worksheet] → Owner-accepted. It is stated in the change summary for organizers,
  and only team worksheets are touched.
- [A client and server out of step print the wrong shape] → The width check in D1
  answers 422 rather than misprinting.

## Migration Plan

No data migration. Deploying the backend and frontend together is the normal
path, and the width check covers a cached old client. Rollback is a plain revert.
A team worksheet already rewritten flat would then be merged by the old code,
which would append its rows. That is acceptable for a rollback.

## Open Questions

None. The owner's decisions above settle the shapes.
