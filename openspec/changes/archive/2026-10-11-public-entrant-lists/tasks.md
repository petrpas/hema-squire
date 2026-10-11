## 1. Remove the unpaid-list treatment

- [x] 1.1 Alembic migration dropping `tournaments.unpaid_list_treatment` (downgrade re-adds it as `greyed`)
- [x] 1.2 Remove `UnpaidListTreatment` and the column from `models.py`; remove the field from the tournament schemas in `schemas.py`
- [x] 1.3 `export_json`: drop the key from `_TOURNAMENT_FIELDS`, bump `SCHEMA_VERSION` to 18, drop the key when importing a document of version ≤ 17; test that a v17 document carrying `hidden` imports
- [x] 1.4 Frontend: remove the treatment from `api.ts`, `setup/PaymentModeSection.tsx` and both i18n catalogs; adjust affected Setup tests

## 2. Entrants projection (backend)

- [x] 2.1 Lift the published/not-cancelled not-found check out of `fencer_tournament_detail` into one helper used by the public detail and the entrants endpoint (D5)
- [x] 2.2 New module (e.g. `app/entrants.py`): individual rosters from `base_rows` → `rules.replay` → `exporttables.table_rows`, restricted to live registration ids, seated paid-first then registration order, numbered from 1 (D1)
- [x] 2.3 Paid/faded per the mode: yes/no + faded where Squire collects; yes or empty where it does not; empty on queued rows
- [x] 2.4 Queue rows in automatic mode, not held: placements in `QUEUE_ORDER`, numbered by queue position, with `conditional`; no queue and `line` false in manual mode or on a held tournament (D2, D6)
- [x] 2.5 Team rosters from `Team`/`TeamMember`: live entering registrations, seated in entry order, waitlist below the line by waitlist order in automatic mode, members by `ordinal`, Paid from the entering registration (D3)
- [x] 2.6 `EntrantsOut` / `RosterOut` / `EntrantRowOut` / `TeamRowOut` schemas carrying only the stated values (no email, VS, amounts, ids) (D4)
- [x] 2.7 `GET /api/tournaments/{slug}/entrants`, public, with `as_of` from `_roster_as_of`; remove `/participants` and `ParticipantOut`/`ParticipantListOut`

## 3. Backend tests

- [x] 3.1 Rewrite `tests/test_participants.py` as `tests/test_entrants.py`: no credential answers; draft and cancelled → 404 naming nobody
- [x] 3.2 Replay is honoured: corrected name, deleted row absent, HR club over the fencer's; expired and unissued rows absent
- [x] 3.3 Paid column by mode: unpaid shown faded where Squire collects; hand tick only otherwise; queued row empty for wholly queued, mixed and held-payment cases
- [x] 3.4 Queue: positions equal `queue_position`; conditional mark; none in manual mode (48 over 42, no line); none on a held tournament
- [x] 3.5 Teams: name and members in order, uncomposed team, waitlist below the line in automatic mode only
- [x] 3.6 The payload carries no email, VS or amount
- [x] 3.7 Run `uv run ruff check .` and `uv run basedpyright` clean

## 4. Routing and the Entrants tab (frontend)

- [x] 4.1 `routes.ts`: `entrants(slug, discipline?)`; `App.tsx`: `t/:slug/entrants` and `t/:slug/entrants/:discipline` to `TournamentDetail`
- [x] 4.2 `api.ts`: `EntrantsOut` types and fetch
- [x] 4.3 `TournamentDetail.tsx`: `Entrants` tab after `Tournament`, always on a published tournament; selected from the route; other tabs from an entrants address navigate to `detail(slug)` with `replace` (D7)
- [x] 4.4 `entrants/EntrantsTab.tsx`: one fetch, `as_of` line above the band, discipline band via `useTabBand` with discipline links, empty-roster line, not-found for an unknown discipline
- [x] 4.5 `entrants/IndividualRoster.tsx`: No., Fencer, Nat., Club, HRID (linked to HEMA Ratings), Paid; numbers right-aligned; faded rows; capacity line; queue rows with position and conditional mark
- [x] 4.6 `entrants/TeamRoster.tsx`: team name, members beneath, "members not yet named", waitlist below the line
- [x] 4.7 `TournamentFace.tsx`: discipline counts link to `entrants(slug, discipline)` behind a prop; `SetupPreview` passes it off. Mind the uncommitted work already in this file
- [x] 4.8 i18n cs/en: tab label (Přihlášení / Entrants), headers, yes/no, empty roster, conditional mark, uncomposed team
- [x] 4.9 Narrow screens: band scrolls full width, table does not scroll the page sideways at 360px

## 5. Frontend tests and checks

- [x] 5.1 Tab order and offering (Tournament, Entrants, Register/Registered, Teams) and the fallback when a tab disappears
- [x] 5.2 Entrants address opens the tab at its discipline; leaving returns to `/t/<slug>`; other tabs push no history
- [x] 5.3 Roster rendering: faded row, empty Paid on queued rows, no line when `line` is false, conditional mark, team members
- [x] 5.4 Count links on the information screen; none in the Setup preview
- [x] 5.5 Run `npm run typecheck`, `npm run check`, `npm test` from `frontend/` clean

## 6. Close-out

- [x] 6.1 Measure the entrants endpoint on the largest real tournament; if `base_rows` evidence dominates, skip it on this path (design Risks) — measured ~165 ms on na-duel-2026 (53 registrations), evidence ~60%; owner chose to leave it as is
- [x] 6.2 `openspec validate public-entrant-lists --strict`

## 7. Owner revisions after review (2026-10-11)

- [x] 7.1 Drop the Rank column; the HRID links to the fighter's HEMA Ratings profile (arrow, no underline)
- [x] 7.2 Drop the counts from the discipline band
- [x] 7.3 Counts on the information screen, card and form state `entered` (rows above the line less organizer-removed rows); seats unchanged; removed teams not listed
- [x] 7.4 Side-event rosters: seminars and other actions after the disciplines, no afterparty, own address `/entrants/events/:item`
