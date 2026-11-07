## 1. The server states the teams on the row

- [x] 1.1 ~~Add the sheet row's team field to `backend/app/schemas.py`~~ — no
  change needed: `SheetOut.rows` is `list[dict]` and the sheet row has no
  Pydantic model; its shape is declared by the frontend's `SheetRow` (task 2.1).
- [x] 1.2 In `backend/app/sheet.py`, fill it for a registration row from
  `registration.teams` in entry order, taking the name and `discipline.slug`;
  leave it empty on imported, unparsed and manual rows. Verify with a new test in
  `backend/tests/test_team_disciplines.py` asserting the console sheet states both
  teams, with their discipline slugs, for a registration carrying two teams in two
  disciplines, and an empty list for a registration with only individual entries.
- [x] 1.3 Verify an imported row and a hand-entered row each come back with no
  teams, by extending that test or `backend/tests/test_hand_entry.py`.
- [x] 1.4 Run `uv run pytest tests/test_team_disciplines.py tests/test_hand_entry.py
  -q --maxfail=3 --tb=short --show-capture=no` and `uv run ruff check .`.

## 2. The column, where the tournament has a team discipline

- [x] 2.1 Add the field to `SheetRow` in `frontend/src/api.ts` with a doc comment
  saying it is the teams the row *entered*, not rosters it is named on; verify
  `npm run typecheck`.
- [x] 2.2 In `frontend/src/Console.tsx`, declare the Fencers phase's identity
  column set including `team` after `club` (design D2), and build `columns` from it
  when the team disciplines feature is on and the detail holds at least one
  discipline of kind `team` (design D5). Keep `team` out of `PHASE_COLUMNS`,
  `EDITABLE_COLUMNS` and `IDENTITY_COLUMNS`. Verify with a unit test in
  `frontend/src/consolePhases.test.tsx` covering: column present and directly
  after club on a team tournament; absent with the feature off; absent with the
  feature on and no team discipline.
- [x] 2.3 Render the cell in `CellDisplay` — `name (slug)` per team, one per line,
  a dash where there is none (design D1). Verify with a test in
  `frontend/src/consoleCells.test.tsx` for two teams in two disciplines, two in
  one discipline, and none.
- [x] 2.4 Add `column.team` to the console's own locale files —
  `frontend/src/i18n/cs.json` ("Tým") and `en.json` ("Team") beside
  `column.club`, not the backend's `app/locales/`, which hold the export and
  e-mail wording — and verify `npx vitest run src/i18n/locale-parity.test.ts`.
- [x] 2.5 Verify the cell does not open for editing: `editableHere("team", …)`
  is false on every phase, which is the decision `SheetArea` renders an editable
  cell from — asserted in `consolePhases.test.tsx`.

## 3. Finishing

- [x] 3.1 From `frontend/`: `npm run typecheck`, `npm run check`, and
  `npx vitest run src/consolePhases.test.tsx src/consoleCells.test.tsx` — all
  clean.
- [x] 3.2 From `backend/`: `uv run ruff check .`, `uv run basedpyright`, and
  `uv run pytest tests/test_team_disciplines.py tests/test_api_contract.py -q
  --maxfail=3 --tb=short --show-capture=no` — the contract test confirms the sheet
  row's new field is part of the stated API shape.
- [x] 3.3 Confirm it on the rendered table rather than by eye: the demo seed has
  `feature_teams: False`, so no local tournament has a team discipline to look
  at. `frontend/src/consoleTeamColumn.test.tsx` mounts the console on one and
  asserts the drawn table — Team between Club and Disciplines, a row with two
  teams reading both with their disciplines, a row with none reading a dash, and
  a tournament with no team discipline unwidened.

## 4. The discipline only where it disambiguates (owner decision, 2026-11-07)

- [x] 4.1 `teamsNeedTheirDiscipline(disciplines)` in `Console.tsx` answers whether
  the tournament has more than one team discipline; `CellDisplay` takes it as
  `namesTeamDiscipline` through `SheetArea`, as `hrIdentity` already travels.
  Verified in `consolePhases.test.tsx` (the predicate) and
  `consoleCells.test.tsx` (name alone vs. name with slug).
- [x] 4.2 Verify it on the drawn table: `consoleTeamColumn.test.tsx` asserts the
  cell reads "Rudá růže" on a one-team-discipline tournament and
  "Rudá růže (LS)" where there are two.
