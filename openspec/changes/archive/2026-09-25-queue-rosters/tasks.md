## 0. Precondition

- [x] 0.1 Confirm `demotion-hardening` is implemented and archived (queue moment on rows, `seating-queue` text this delta builds on)

## 1. Backend

- [x] 1.1 `scheduler.pending_demotions` returns registrations and seated teams from the one `_demotable` selection
- [x] 1.2 `GET /{slug}/queue` returns deadline, settled moment, pending demotions, pending team waitlistings, and per discipline slug, capacity, taken, free; remove `QueueEntryOut` and the seated/queued lists; update `schemas.py`
- [x] 1.3 Tests: the team count equals what settlement then waitlists; free places use `taken_seats`

## 2. Phase placement

- [x] 2.1 `Console.PHASES` order: payments, queue, export, teams; comment updated
- [x] 2.2 `offeredPhases` drops `queue` on `registrations_kept_by === "organizer"`; the flags type carries the mode where it is called
- [x] 2.3 Tests: order; manual tournament has no Queue; its URL lands on the default phase

## 3. Queue phase frontend

- [x] 3.1 `queue/QueuePhase.tsx`: discipline tabs from `exportTabs` (discipline kind only), rows via `exportTable`, summary via `queue`, `act()` with reloads and `onChanged`, rail via `renderRail`
- [x] 3.2 `queue/queueColumns.ts` + `queue/QueueRoster.tsx`: `ExportGrid` with position, name, club, rating (read-only), money on seated / position and queue moment on queued, action column; `rosterOrder(..., "queue", false)`
- [x] 3.3 `queue/ArrowCell.tsx`: ↑ when queued with a registration and free > 0; ↓ when seated with a registration and unpaid; a no-registration row states it holds no seat yet
- [x] 3.4 `queue/SeatingCard.tsx`: deadline, settled state, open discipline's free places, settle action with `Modal` confirmation counting registrations and teams; hidden action once settled
- [x] 3.5 Refusal codes → `queue.refused.*` texts with a fallback; delete `QueuePanel.tsx` and `QueueEntryLine.tsx`; wire the phase in `Console.tsx`
- [x] 3.6 i18n cs + en for the card, arrows, hints, money cell, refusals; drop unused `queue.*` keys

## 4. Tests

- [x] 4.1 The Queue roster and the Export roster of one discipline list the same rows in the same order with the line in the same place
- [x] 4.2 Arrow availability: full discipline → no ↑; paid seated → no ↓; no-registration row → no arrows
- [x] 4.3 A refused action shows the Czech text, not the code
- [x] 4.4 Settlement confirmation states registrations and teams; rail after settlement offers no action
- [x] 4.5 Export discipline tab offers no arrows

## 5. Checks

- [x] 5.1 Backend: `uv run ruff check .`, `uv run basedpyright`, scoped `pytest`
- [x] 5.2 Frontend: `npm run typecheck`, `npm run check`, `npm test`
