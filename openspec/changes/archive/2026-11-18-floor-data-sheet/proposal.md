## Why

The floor's Data tab is a read-only list of every discipline stacked on one page. It
states a rating but no rank and no HEMA Ratings id, and its columns are not the
office's. On the day of the tournament the list is also where the organizer needs to
act. Someone does not come, someone else turns up, a club or an identifier is wrong,
or a rating is stale. Today none of that can be done on the floor. Owner decision
2026-11-17: Data becomes the floor's working sheet. The day's manual corrections are
made there and nowhere else, and they stay in the floor.

This change belongs to the floor context (`app/floor`, `frontend/src/floor`). It
reaches the office in one place only, the floor's office adapter. The adapter fetches
HEMA Ratings figures for the sheet with the office's own fetch code, and nothing in the
office changes.

## What Changes

- Data chooses its discipline from the discipline strip, as Skupiny does, and joins the
  step tabs. The chosen discipline is kept across the console.
- One discipline's sheet is drawn with the office Export's discipline columns: #, name,
  nationality, club, HR ID, rating, rank and paid. It is ordered by rating, which is
  the order the pool draw seeds in. A team discipline is drawn as the office draws it,
  as teams with their members beneath them.
- The sheet is editable until the discipline's check-in closes:
  - a cell correction (name, club, nationality, HR ID, rating, rank);
  - an added entrant, either a floor-only person or someone already on the floor, and
    on a team discipline an added team with its members;
  - a removed entrant, which is the check-in withdrawal, one state shown in both tabs.

  The paid mark is shown and never changed on the floor. An addition's paid cell is
  empty.

  The corrections live in new `floor_` tables as a layer over the floor roster. Every
  floor reader works with the edited sheet: check-in, the snapshot, the planner's N, the
  draw and the public pages. The office is never written.
- The operations panel gains "Obnovit ratingy" for the chosen discipline, taken over
  from the office's Export card: the same icon, hint and state line. It fetches the
  discipline's entrants' ratings and ranks into the floor sheet, never into the office
  snapshot. A hand correction stands over a fetched figure.
- Once the discipline's check-in is closed, the sheet shows the snapshot, read-only.
  The panel offers neither editing nor the refresh, and says that a change needs the
  check-in reopened.
- **BREAKING (floor-only):** `GET /floor/roster` and every floor endpoint built on it
  answer with the edited sheet, not the raw office roster.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `floor-data`: Data becomes a per-discipline, editable sheet in the office's columns,
  with a per-discipline ratings refresh, read-only after check-in closes. Entrants still
  come from the office, and the floor's own edits now lie over them.
- `floor-console`: Data joins the tabs that choose their discipline from the strip and
  keep the choice. It is no longer a detour tab.
- `floor-roster`: a team entry also states each member's rating and rank, so the team
  sheet can show them as the office's team tab does.
- `floor-checkin`: a withdrawal can also be made from Data, and the snapshot freezes the
  sheet's values (edited ones included) rather than the raw roster's.

## Impact

- Backend: a new `app/floor/datasheet.py` (overlay and edits) and new tables
  `floor_sheet_edits`, `floor_sheet_entries`, `floor_sheet_teams`, `floor_sheet_fetches` and
  `floor_sheet_ratings`, plus `floor_local_persons.hr_id`, in Alembic migration
  `floor_0010`. `TeamEntry` in the roster port gains its members' ratings. New endpoints under `/api/tournaments/{slug}/floor/sheet`.
  `app/floor/adapters/office.py` gains `fetch_ratings`. `app/hr_sync.py` splits
  `take_snapshot` into a fetch and a store so that both callers share the fetch, with
  no behavior change for the office.
- Every floor caller of the adapter's `roster()` switches to the overlaid sheet.
- Frontend: `floor/data/` is rewritten into a per-discipline sheet. `DataTab` joins
  `STEP_TABS`. The office's `ExportGrid` becomes generic over its row type. The ratings
  refresh card part of `TableOperations` is extracted into a shared component used by
  both consoles.
- Office behavior is unchanged. The office export, snapshot and rules are not touched.
