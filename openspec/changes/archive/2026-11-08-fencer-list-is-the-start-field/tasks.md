## 0. Order of work

- [x] 0.1 Confirm `roster-identity-and-history` is implemented and archived before
  starting: a `mem:<id>` row id is only durable once the roster save is a diff.
  If it is not, stop — this change's rules would point at rows the next roster
  save destroys.

## 1. The fourth population

- [x] 1.1 Project roster members as `mem:<member_id>` rows in `sheet.py`: name,
  nationality, club, claimed `hr_id`, the evidence register, the match verdict,
  the team and its discipline, and the team's registration moment as the row's
  moment with roster order breaking ties (design D1, D2). Money, seat and queue
  fields absent. Verify with a test asserting a tournament with 18 team
  registrations and 67 members projects 67 fighter rows and no money on any of
  them.
- [x] 1.2 A registration holding no individual entry is not projected as a fencer
  row, while remaining present for Payments and the Queue. Verify with a test on
  a team-only registration whose holder is on no roster: absent from the list,
  present in the payment queues.
- [x] 1.3 Allocate a number when a member is added, in the roster diff
  (design D3). Verify the number survives a removal and a restore and is never
  reissued.
- [x] 1.4 Verify the list's order: a team entered between two individual
  registrations stands together, in roster order, between them.

## 2. Matching, the snapshot, and deduplication

- [x] 2.1 Verify matching reaches member rows with no change to `matching.py`
  beyond what the projection gives it: a test asserting a member row carries a
  proposal, takes a verdict, and that the verdict is a rule on its row id which
  survives a later roster save that does not touch that member.
- [x] 2.2 Verify the ratings snapshot's identifier set includes matched member
  rows (`routers/hr_api.py` reads the replayed projection; confirm rather than
  assume). A test on a tournament offering the same weapon individually and in
  teams, asserting a member's identifier is fetched.
- [x] 2.3 Exclude member rows from deduplication candidates in `dedup.py`
  (design D4). Verify two rosters naming one matched person produce no candidate
  group, and that a member row and its entrant's registration row produce none
  either — while two imported rows of one person still do.

## 3. What a row offers

- [x] 3.1 `rowAction` returns nothing for a member row; neither cancellation, nor
  deletion, nor handing over a registration is offered (design D5). Verify per
  action with a test over a member row on every phase that shows the table.
- [x] 3.2 The disciplines and rentals cells do not open on a member row: it bought
  nothing. Verify `editableHere`/the cell rendering leaves them closed while the
  identity cells stay open.
- [x] 3.3 The Team column states a member row's own team and a registration row's
  entered teams, and never reads a dash on a member row. Verify in
  `consoleTeamColumn.test.tsx`, which already covers the registration side.
- [x] 3.4 `paidCount` and the phase summaries count only rows with a payment state
  (design D6). Verify a tournament of 67 fighters and 18 contracts states 18 in
  the payment summary, not 67.

## 4. Teams becomes a table, after Fencers

- [x] 4.1 Move Teams to immediately after Fencers in `PHASES` (design D7). Verify
  the offered-phase tests still pass and that an automatic tournament reads
  Setup, Fencers, Teams as its first three tabs.
- [x] 4.2 Rebuild `TeamsPanel.tsx` as a table — team, discipline, entering fencer,
  member count against min/max, waitlist position, the entering registration's
  payment standing — with the roster and its log reachable from the row. Keep it
  one component per file and split along its seams.
- [x] 4.3 Verify the view still offers no admission and says admission is the
  Queue phase's.

## 5. Cancelling one team

- [x] 5.1 Add the organizer's cancellation of a single team as an amendment of its
  registration (design D9): the fee leaves the total, the registration is
  repriced on its frozen prices, the place is freed, nobody is promoted, the
  roster goes with the team, and its members leave the fencer list.
- [x] 5.2 Verify with tests: one team of two cancelled leaves the other and the
  registration standing; a seated team's cancellation frees a place and promotes
  nobody; the four members are gone from the list; a cancelled or expired
  registration refuses it.
- [x] 5.3 The entering fencer is told, naming the team and the discipline and
  stating the resulting balance; a registration Squire sends nothing to is not
  written to. Verify with a mailbox test in both languages.

## 6. The public roster states the settled identifier

- [x] 6.1 `entrants.py` reads a team member's identity from the projection, as it
  already does for individual rows (design, Context). Verify a member entered
  with one identifier and bound by the organizer to another is published with the
  organizer's, and that an unmatched member is published as claimed.

## 6b. A team discipline carries a rating category

- [x] 6b.1 Stop refusing a team discipline's taxonomy code in the category map
  (`routers/tournaments.py:807-815`) and offer it for configuration. Verify the
  map accepts and stores an entry for a team-only tournament, and that an
  individual and a team discipline classified alike still share one entry.
- [x] 6b.2 Stop filtering the snapshot's taxonomy codes by the discipline's kind
  (`hr_sync.py:280`). Verify a team-only tournament with a configured category
  fetches a rating for every matched roster member, and that a team discipline
  whose weapon is outside the taxonomy is skipped without a failure.
- [x] 6b.3 Verify no team carries a rating or a rank of its own (design D10) — a
  test asserting the ratings a snapshot stores are per fighter and that nothing
  derives a team's.
- [x] 6b.4 Build the band's tab per team discipline (`exporttables.py:82`):
  teams ordered by paid then entry moment, numbered as teams, each with its
  fighters beneath in roster order stating rating and rank, the team's paid cell
  on the team row, no seeding tick, and the capacity line in teams with the
  waitlisted below it. Verify against the modified `export-tables` requirements.
- [x] 6b.5 Verify roster print needs no change by printing a team discipline's tab
  and reading the PDF's rows.
- [x] 6b.6 Add the Czech and English wording the new tab needs, and verify
  `npx vitest run src/i18n/locale-parity.test.ts`.

## 6c. What the organizer asked for after reading it

- [x] 6c.1 Add the counting column left of the fencer's number, so the list can be
  counted without reading numbers that skip (spec etl-console, Position in the
  list). A removed row takes no position. Verify in `consoleRowCount.test.tsx`.
- [x] 6c.2 State a team's member count as the number alone and mark a count the
  bounds do not admit. Verify in `consoleTeamsPanel.test.tsx` both ways round.
- [x] 6c.3 Rewrite the cancellation dialog's copy in both languages: say it cannot
  be undone, and drop the repricing vocabulary. Delete the orphaned
  `teams/TeamRow.tsx`, which the table replaced.

## 6d. What confirming it on the running app turned up

- [x] 6d.1 Number the roster members that were already on a roster when member
  numbering arrived: `alembic/versions/d4a7c2e8b015_*`, which allocates in
  `rownumbers.arrival_order`'s order. Without it a team tournament's fencer list
  read a dash in the number column for every fighter — 67 of 67 on `ttt-2027`.
- [x] 6d.2 A member row's state cell reads a dash, not the raw `member`
  identifier the projection names the population with. Verify in
  `consoleCells.test.tsx`.

## 7. Finishing

- [x] 7.1 From `backend/`: `uv run ruff check .`, `uv run basedpyright`, and
  `uv run pytest tests/test_team_disciplines.py tests/test_matching.py
  tests/test_dedup.py tests/test_entrants.py tests/test_export_tables.py
  tests/test_row_numbers.py tests/test_sheet_order.py tests/test_hr_integration.py
  tests/test_taxonomy.py tests/test_roster_print.py -q --maxfail=3 --tb=short
  --show-capture=no`.
- [x] 7.2 From `frontend/`: `npm run typecheck`, `npm run check`, `npm test`.
- [x] 7.3 Measure the projection on a tournament of ~70 fighters before calling it
  done (design, Risks): time `GET /sheet` and record it in the change, so the next
  change has a number rather than an assumption.
- [x] 7.4 Confirm end to end on the running app with `ttt-2027`-shaped data: the
  fencer list states every fighter, Matching offers each a verdict, Teams reads as
  a table of eighteen rows after Fencers, and a team-only entrant appears in
  Teams and Payments but not among the fencers.
- [x] 7.5 Confirm the purpose is served, which is the whole point of the line of
  work: configure the category for the team discipline, take a snapshot, open the
  discipline's export tab, and read a rating for every matched fighter.

  **Confirmed** (2026-11-08, local app, `ttt-2027`: 18 registrations, 18 teams,
  67 fighters). 7.4: the fencer list states 67 fighters and none of the 18
  contracts; Matching states a confirmed verdict on all 67; the tabs read
  Nastavení, Šermíři, Týmy, Párování, Deduplikace, Platby, Fronta, Export, so
  Teams stands after Fencers; Teams is 18 rows with two waitlisted stating
  position and the Queue phase; Payments lists all 85 rows and counts 18
  registrations unpaid. 7.5: the team discipline's code was accepted into
  `hr_category_map` (a 422 before 6b.1); the snapshot fetched 67 fighter pages
  from hemaratings.com and stored 67 ratings with nothing missing; the export tab
  numbers the 18 teams, puts each team's fighters beneath it in roster order with
  a rating and a rank for all 67, carries the capacity line in teams after the
  sixteenth, and gives no team a rating of its own.
