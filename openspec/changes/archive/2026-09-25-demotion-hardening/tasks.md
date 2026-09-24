## 1. Queue moment in storage

- [x] 1.1 Add `RegistrationDiscipline.queued_since` and `Team.waitlisted_since` (timezone-aware, not null) to `models.py`; every construction site sets them to the registration's `registered_at` (registration, amendment, re-registration after expiry, issuing, JSON import)
- [x] 1.2 Alembic revision: add nullable, backfill from `registrations.registered_at`, set not null; downgrade drops them
- [x] 1.3 `export_json`: `SCHEMA_VERSION = 15`, entries and teams carry their moments; v1–v14 imports default each moment to `registered_at`

## 2. Queue order readers

- [x] 2.1 `routers.registrations.queue_position` ranks by `(queued_since, registered_at, id)` over live substitute placements
- [x] 2.2 `routers.tournaments.console_queue` orders by the same key; `QueueEntryOut` gains `queued_since` and `demoted`; teams view's waitlist position reads `waitlisted_since`
- [x] 2.3 `sheet.base_rows` carries a `queued_since` map beside `substitute_for`; `export/ordering.rosterOrder` sorts the queued group by it (stable)
- [x] 2.4 `QueueEntryLine` states the queue moment, distinguishing a demotion moment from a registration time; `api.ts` types; i18n labels (cs, en)

## 3. Demotion

- [x] 3.1 `scheduler._demote(registration, now)` sets the moment on exactly the placements it moves, recomputes totals via `pricing.registration_total`, and returns what it moved
- [x] 3.2 `emails.send_demoted`: disciplines and teams moved, position in each (read after commit), nothing owed / do not pay / promotion opens a window, held credit stated without a refund promise; backend catalogs cs + en
- [x] 3.3 Mail after commit at all three sites: `settle_seating`, `promotion_lapsed`, `seat_lapsed_to_queue`; audit alongside each demotion event; nothing sent when nothing moved
- [x] 3.4 Confirm `return_to_queue` leaves the moment untouched and sends no demotion mail

## 4. Settled excludes fully-queued

- [x] 4.1 `Registration.settled` Python half: waived, or (not fully queued with ≥1 placement, and a lane settles)
- [x] 4.2 SQL expression: the same, via `EXISTS`/`NOT EXISTS` over entries and teams; check every query filtering on `settled` still plans and returns the same rows outside the new case

## 5. Money on a queued registration

- [x] 5.1 Matching flags a fully-queued reserved registration `registration_queued` (audited `match_conflict`) instead of crediting; verify VS, bare token, multi-registration split and name-assisted paths each reach the check
- [x] 5.2 `emails.send_payment_while_queued` (arrived, you are queued and hold no place, the organizer will be in contact); cs + en
- [x] 5.3 `admit_substitute` re-evaluates this registration's `registration_queued` transactions after seating and repricing, then composes the promotion mail from the resulting balance (confirms the place when covered)
- [x] 5.4 Frontend label for the `registration_queued` flag reason (cs, en)

## 5b. A lapse takes back only what promotion seated

- [x] 5b.1 `promoted_unpaid` on entries and teams (same migration as 1.2); set by `admit_substitute` when the registration is left unsettled
- [x] 5b.2 Clear every mark when a credit, recorded payment or waiver leaves the registration settled — one hook in the ledger write path
- [x] 5b.3 Expiry pass: an overdue registration with marks returns the marked placements/teams (end of queue, reprice, audit, mail), then applies today's lapse outcome only if it still owes and still holds a seat
- [x] 5b.4 Tests: paid Longsword + promoted Sabre lapsing before and after settlement keeps Longsword seated and paid; a promoted team lapsing likewise; a fully queued registration promoted and lapsing before settlement returns to the queue instead of expiring; marks cleared once paid

## 6. Tests

- [x] 6.1 Settlement: demoted placements rank after an already-queued later registrant; registrations demoted together rank by registration time; totals exclude the seat; one mail each; none when nothing moved
- [x] 6.2 Lapsed promotion and lapsed mixed window: end of queue for the moved placement, the already-queued placement keeps its place, mail sent
- [x] 6.3 Organizer return after demote → promote restores the demotion moment; a never-queued return takes its registration time; no mail
- [x] 6.4 Settled: forfeited deposit on a fully-queued registration reads reserved (Python and SQL agree); waiver still settles; amendment-to-zero with a seat still reads paid
- [x] 6.5 Matching: a payment on a fully-queued registration is flagged and mailed, not credited; a mixed registration is credited as before; promotion credits the held transaction and the mail reflects it
- [x] 6.6 Export JSON v15 round-trip keeps moments; a v14 document imports with moments equal to registration times
- [x] 6.7 Frontend: `rosterOrder` orders the queued group by moment; `QueueEntryLine` shows the demotion moment

## 7. Checks

- [x] 7.1 Backend: `uv run ruff check .`, `uv run basedpyright`, scoped `pytest`
- [x] 7.2 Frontend: `npm run typecheck`, `npm run check`, `npm test`
