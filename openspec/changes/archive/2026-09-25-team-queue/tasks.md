## 0. Precondition

- [x] 0.1 Confirm `demotion-hardening`, `queue-rosters` and `participation-condition` are archived

## 1. Backend

- [x] 1.1 Factor reprice / window / promotion-mark steps out of `admit_substitute` for reuse
- [x] 1.2 `POST .../teams/{tid}/admit` and `.../return-to-waitlist` per design D2; audit events; worded refusal codes
- [x] 1.3 `emails.send_team_promoted` (team, discipline, amount due, date; suppressed where Squire sends nothing); cs + en
- [x] 1.4 `GET /{slug}/queue/teams/{discipline_slug}` per D1; `/queue` summary adds team disciplines' capacity, taken, free
- [x] 1.5 `console_teams`: live registrations only, waitlist order by `(waitlisted_since, created_at, id)`
- [x] 1.6 Tests: admit with a free slot bills and mails; admit refused when full; return refused when paid; an unpaid admission lapsing returns the team alone and keeps a paid individual seat; dead registrations' teams not listed or counted

## 2. Frontend

- [x] 2.1 Queue band lists team disciplines after individual ones while `feature_teams` is on
- [x] 2.2 `queue/TeamRoster.tsx` and its columns: name, entering fencer, members vs min/max, money or position and moment, action
- [x] 2.3 Arrow cell team predicates; refusal texts
- [x] 2.4 Teams phase: a waitlisted team's row states that admission is on the Queue phase
- [x] 2.5 i18n cs + en

## 3. Checks

- [x] 3.1 Backend: `uv run ruff check .`, `uv run basedpyright`, scoped `pytest`
- [x] 3.2 Frontend: `npm run typecheck`, `npm run check`, `npm test`
