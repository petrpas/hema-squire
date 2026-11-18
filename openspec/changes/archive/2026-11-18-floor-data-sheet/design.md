## Context

Floor Data (`frontend/src/floor/data/DataTab.tsx`) reads `GET /floor/roster` and draws
every discipline as a card with its own small table. The table shows name, club,
nationality, rating and paid. The roster port (`app/floor/roster.py`) already carries
`Person.hr_id` and `IndividualEntry.rank`. Neither is shown.

The office's Export phase draws a discipline with `ExportGrid` and `ROSTER_COLUMNS`
(`frontend/src/export/columns.ts`): position, name, nationality, club, HR ID, rating,
rank and paid. A team discipline is drawn by `TeamRosterTable` as teams with their
fighters beneath them. Its rail card `TableOperations` holds the ratings refresh. That
refresh is an icon with a hint, the result line, and the `ratingsState` line, which
reads "staženo <kdy> · N bez ratingu". It calls `POST /ratings/snapshot`, which fetches
every HR id of the tournament and stores one `HRRatingSnapshot`. The office export reads
only the latest snapshot.

Floor state that already exists and is reused here:
- `FloorWithdrawal(entry_key = "<person>@<discipline id>" | "team:<id>")`;
- `FloorLocalPerson`, the `local:<id>` floor-only person, so far a lineup substitute only;
- `people.live / present / entrants`, which read a `Roster` and turn it into entrants;
- `checkin.close`, which freezes `FloorSnapshotEntrant` rows (name, club, nationality,
  hr_id, rating, rank) from `people.present`.

Owner decisions 2026-11-17 (two rounds):
1. Rows come from the floor roster, drawn in the office's columns.
2. The whole sheet is editable. No-shows, walk-ins and corrections are made here, and no
   later tab corrects an entrant.
3. Edits stay in the floor and never reach the office.
4. Removing on Data and withdrawing at the desk are one state.
5. The order is by rating, the order the draw seeds in.
6. The refresh covers the chosen discipline only. It stores into the floor sheet, never
   the office snapshot.
7. A discipline whose check-in is closed has a read-only sheet: the snapshot, with no
   refresh.

## Goals / Non-Goals

**Goals:**
- One per-discipline sheet in the office's columns, editable until check-in closes.
- One overlay that every floor reader goes through, so a correction made on Data is what
  the desk, the snapshot, the draw and the public floor pages read.
- The office's ratings fetch reused, not copied, behind the adapter.

**Non-Goals:**
- Writing anything to the office: rules, registrations or the HR snapshot.
- Merging two floor persons by hand. The identity rule stays the adapter's.
- Editing the paid mark. It is shown and never changed, and an addition's paid cell is
  empty. Money is settled in the office or outside Squire (owner decision 2026-11-17).
- A floor-own table import. The port stays open for one, as before.

## Decisions

### D1. The overlay is a pure function over the port, applied in one place
`app/floor/datasheet.py` holds:
- `Edits`: a frozen dataclass of everything the floor has stored. It holds person field
  edits, entry rating and rank edits, fetched figures, added entries, and the local
  persons those entries name.
- `apply(base: Roster, edits: Edits) -> Roster`: pure. It returns a `Roster` of the same
  shape, so `people`, `checkin`, `pools`, `planning` and `public` need no change.
- `load(session, tid) -> Edits` and `roster(session, tournament) -> Roster`, which is
  `apply(adapters.office.roster(...), load(...))`. `roster_of` is the same for the piste
  screen.

Every floor caller that imports `roster` or `roster_of` from the adapter switches to
`datasheet`. `tests/floor/test_floor_boundary.py` gains a check that only `datasheet.py`
imports the adapter's `roster` or `roster_of`, so a new reader cannot skip the overlay.

*Alternative:* apply the edits inside `people.live`. Rejected because the planner, the
public pages and the desk's person list read `Roster` directly. Correcting in one
consumer would leave the others stating the old value.

### D2. Precedence per cell: hand edit > floor fetch > office replay
A rating or rank cell of an entry resolves in this order:
1. the hand edit for `(entry_key, field)`;
2. the floor's fetched figure for `(discipline_id, hr_id)`, where the effective HR id
   is the edited one if edited;
3. the roster's own value.

A person field (name, club, nationality, hr_id) resolves as hand edit over roster. An
edit storing an empty value deletes the edit row, which returns the cell to what lies
beneath it (spec: "An emptied cell returns the cell to the value beneath it"). The
response marks each edited cell, so the frontend draws the office's `cell-edited` mark.

Editing a floor-only person's fields edits the `FloorLocalPerson` row itself. There is
nothing beneath it.

### D3. Tables (migration `floor_0010_data_sheet`)
- `floor_sheet_edits`: id, tournament_id, `subject` (a person key, or an entry key
  `<person>@<discipline id>`), `field` (name | club | nationality | hr_id | rating |
  rank), `value` JSON, at, by. Unique (tournament_id, subject, field).
- `floor_sheet_entries`: id, tournament_id, person_key, discipline_id (FK disciplines,
  `ondelete=CASCADE`), at, by. Unique (tournament_id, person_key, discipline_id). An
  added individual entry is paid=False and carries no rating until one is fetched or
  typed.
- `floor_sheet_teams`: id, tournament_id, discipline_id (FK disciplines,
  `ondelete=CASCADE`), name, at, by. Keyed `floorteam:<id>`, a prefix the office never
  issues. Its members are `FloorLineup` rows under that team key, so the desk's lineup
  editor and `people.lineup_of` work on it unchanged. The overlay adds a `TeamEntry`
  with paid=False and the members' figures resolved by D2. The member count is
  checked with `checkin.lineup_errors` against the discipline's bounds (owner decision
  2026-11-17).
- `floor_sheet_fetches`: id, tournament_id, discipline_id, fetched_at, `asked` JSON
  (the HR ids asked). One row per discipline is replaced on each refresh.
  `floor_sheet_ratings` holds fetch_id, hr_id, rating, rank.

`FloorLocalPerson` gains a nullable `hr_id`, so a walk-in named with an HR id can be
fetched.

Removal of an office entry is a `FloorWithdrawal` (decision 4). Removal of a
floor-added entry deletes its `floor_sheet_entries` row together with any withdrawal of
it.

*Alternative:* one generic JSON blob per tournament. Rejected because it gives no
uniqueness, no per-cell undo and no CASCADE on a deleted discipline.

### D4. The refresh reuses the office fetch through the adapter
`hr_sync.take_snapshot` is split:
- `fetch_ratings(tournament, fetcher, hr_ids, codes) -> FetchOutcome` does the page
  loop, the category match and the drift rejection, with no session writes;
- `take_snapshot` calls it and stores, exactly as now.

The office's behavior and tests are unchanged.

`adapters/office.py` gains `fetch_discipline_ratings(session, tournament, discipline_id,
hr_ids, fetcher) -> dict[int, tuple[float | None, int | None]] | None`. It resolves the
discipline's `taxonomy_code`, calls `hr_sync.fetch_ratings`, and returns None on a
rejected fetch. It also re-exports `get_hr_fetcher` for the endpoint's dependency.
`datasheet.refresh(...)` stores the outcome in `floor_sheet_fetches/ratings`. A team
discipline asks for its members' HR ids, under the team discipline's code, as the office
does (spec team-disciplines).

The refresh is refused with 409 `checkin_closed` on a closed discipline. The office's
15-minute brake is for the global fighters index and does not apply here: a per-fighter
fetch was never braked in the office either.

### D5. Team members' ratings ride on `TeamEntry`
`TeamEntry` gains `ratings: tuple[tuple[float | None, int | None], ...]`, parallel to
`members`, read by the adapter from each member row's `ratings[slug]` and `ranks[slug]`.
This is the floor-roster delta. The overlay applies D2 to them with the entry key
`<person>@<discipline id>`, exactly as for an individual entry. `people.Entrant` of a
team stays rating-less, since seeding a team is the bracket's rule (average pool place).

### D6. Endpoints
All endpoints sit under `/api/tournaments/{slug}/floor/sheet`, with console access as
the rest of the floor:
- `GET /{discipline_id}`: the sheet. Rows in seeding order, with person and entry
  fields, `edited` flags, `withdrawn`, `added` and paid. It also carries `closed`
  (closed_at or null), `fetched_at` and `missing` for the state line. For a closed
  discipline the rows are the snapshot's, with paid read from the live sheet.
- `PUT /cells`: `{subject, field, value | null}`. A rating is validated as the office
  validates one (`validateRating` bounds). An HR ID must be a positive int. A name
  must be non-empty.
- `POST /{discipline_id}/entries`: `{person_key}` or `{name, club, nationality, hr_id}`.
  A new person is created as a `FloorLocalPerson`.
- `POST /{discipline_id}/teams`: `{name, members: [{person_key} | {name, club,
  nationality, hr_id}]}`, which creates the local persons, the team and its lineup.
  `DELETE /{discipline_id}/teams/{team_key}` removes a `floorteam:` addition with its
  lineup and any withdrawal.
- `DELETE /{discipline_id}/entries/{person_key}`: deletes an addition. An office entry
  is removed through the existing withdrawal endpoints, which the sheet calls.
- `POST /{discipline_id}/ratings`: the refresh. It answers `{ratings, fencers}` for
  the office's result line.

Every write is refused with 409 `checkin_closed` when the discipline's check-in is
closed (spec: A closed discipline's sheet is the snapshot). A cell write on a person
holds across disciplines, so it is refused only if *every* discipline the person entered
is closed. The edit then reaches the open ones, and the snapshots of the closed ones keep
their frozen values.

### D7. Frontend: the office's grid and refresh, shared, not copied
- `ExportGrid` becomes generic: `ExportGrid<Row>`, with `ExportColumn<Row>`. The office
  passes `SheetRow` and behaves as before. `floor/data/columns.ts` declares the floor
  sheet's columns with the same ids, so the headings are `export.column.*`.
- The refresh icon, hint, result line and `ratingsState` line move out of
  `TableOperations` into `export/RatingsRefresh.tsx`. `TableOperations` renders it, and
  so does the floor Data panel.
- `floor/data/` is split into `DataTab.tsx` (orchestrator: strip, load, panel),
  `SheetTable.tsx` (individual), `TeamSheetTable.tsx` (teams), `AddEntrant.tsx` (the
  panel's control, a `Modal` with a person picker; the picker leaves out
  whoever already stands in the discipline, on a team of it too; a newcomer is
  named through the registrant's `RosterMemberDialog`, looked up in HEMA
  Ratings or taken as typed)
  and `DataPanel.tsx`.
- `data` joins `STEP_TABS`. `FloorConsole` passes `discipline` and `fallback` as it
  does for `pools`. The strip has no "Všichni".
- Withdrawn rows are struck through with `text-decoration` and carry "Vrátit". No
  colour carries the state alone.

### D8. Seeding order lives in one place per side
The backend sorts the sheet rows with the same key `pools.py` uses for the draw:
`-rating`, rank, then key. For display the unrated come after, by name. This is
factored into one `seeding_key` in `app/floor/people.py`, which both read, so the
sheet's order and the draw's cannot drift.

## Boundary imports (every import crossing the floor boundary)

- `app/floor/adapters/office.py` adds `from app import hr_sync` (`fetch_ratings`,
  `get_hr_fetcher`, `HRFetcher`). The adapter is the one floor file allowed to read
  office modules.
- `app/floor/datasheet.py` imports `app.db`, `app.floor.models`, `app.floor.roster`,
  `app.floor.people`, `app.floor.checkin` (closed state), and from the adapter only
  `roster`, `roster_of` and `fetch_discipline_ratings`.
- `app/floor/api.py` imports `get_hr_fetcher` and `HRFetcher` through the adapter, never
  from `app.hr_sync`.
- `app/hr_sync.py` (office) imports nothing from the floor.

## Risks / Trade-offs

- [Risk] The floor and the office now state different ratings for the same fencer.
  → This is intended (decisions 3 and 6). The Data panel's state line names the floor
  fetch's own moment, never the office's, so neither claims to be the other.
- [Risk] A hand-edited HR id makes a person look like someone else to the identity rule.
  → Identity is decided by the adapter over office data before the overlay. An edit
  changes figures, never who is one person.
- [Risk] An office person whose registration is cancelled after an edit leaves orphan
  edit rows. → The overlay ignores subjects not on the base roster. They do no harm, and
  they come back to life if the entry returns, which is the expected behavior.
- [Risk] Switching every reader to `datasheet.roster` costs one extra query per request.
  → It is a handful of small indexed selects, and the replay itself dominates.
- [Risk] An added team's member can also stand on an office team of the same
  discipline. → The same lineup rule as at the desk applies: a person fences for one
  team in a discipline, and `lineup_errors` refuses the second.

## Migration Plan

`floor_0010_data_sheet` creates the five tables and adds `floor_local_persons.hr_id`.
No data needs moving: an empty overlay is the identity function. Rollback drops them.
The office is untouched.

## Resolved questions (owner, 2026-11-17)

- Paid is shown and never changed on the floor. An addition's paid cell is empty.
- A whole team can be added on a team discipline's sheet (D3 `floor_sheet_teams`).
