## 1. Backend reader

- [x] 1.1 Add `lapsed_teams(session, discipline)` to `backend/app/availability.py`: teams on expired or cancelled registrations, each with reason and moment (D2: `cancelled_at`; latest `reservation_expired`/`expired_holding_payment` event, else `expires_at`), most recent first; `live_teams` untouched
- [x] 1.2 Tests in `tests/` for the reader: expired and cancelled both returned, live never, a team cancelled alone never, moment from the latest expiry event after a reinstate-and-re-expire, fallback to `expires_at`

## 2. Teams view and Queue responses

- [x] 2.1 Add one `LapsedTeamOut` to `schemas.py` (D3), a `lapsed` list on `ConsoleTeamDisciplineOut`, and `GET /queue/teams/{slug}/lapsed` for the Queue
- [x] 2.2 Fill them in `console_teams` and `console_queue_lapsed_teams` (`routers/tournaments.py`), held money from `credited_in` per lane as `sheet.py` does
- [x] 2.3 Tests: a lapsed team is listed apart and changes no count, free slot or waitlist position; held money stated; reinstated registration's team back among the live

## 3. Fencer list

- [x] 3.1 In `sheet.py`, collect roster members only for live registrations (D5); the registration row stays
- [x] 3.2 Tests: an expired registration's members leave the projection, its own row stays stating expired; reinstated, members return under their fixed numbers

## 4. Frontend

- [x] 4.1 `api.ts` types for the `lapsed` lists
- [x] 4.2 Teams view (`frontend/src/teams/`): a lapsed section component below the table body, its own labelled line, faded rows, no gutter number, reason + day + held money cell, read-only roster disclosure, no actions; nothing drawn when empty
- [x] 4.3 Queue (`frontend/src/queue/TeamRoster.tsx`): the same section below the waitlist, no arrows, no position
- [x] 4.4 i18n `cs.json` / `en.json`: line label, "propadla {{day}}" / "zrušena {{day}}", held money; sentence case, no exclamation
- [x] 4.5 Component tests for both sections (listed, read-only, absent when empty)

## 5. Checks

- [x] 5.1 Backend: `uv run ruff check .`, `uv run basedpyright`, scoped pytest
- [x] 5.2 Frontend: `npm run typecheck`, `npm run check`, `npm test`
- [x] 5.3 Browser check in the console: an expired team in Teams and Queue, its members gone from Fencers
