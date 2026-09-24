## Context

Three paths move a registration below the line for non-payment, all through
`scheduler._demote`: seating settlement (`settle_seating`, reached by the deadline tick
or the organizer's settle action), a lapsed promotion window after settlement
(`promotion_lapsed`), and a lapsed window on a registration that also holds a queued
placement (`seat_lapsed_to_queue`). `_demote` flips `is_substitute`/`waitlisted`, clears
`expires_at` and returns; it sends nothing and leaves `total_amount`/`total_eur` as they
were. The organizer's `return_to_queue` does reprice.

Queue order is `Registration.registered_at` everywhere: `routers.registrations.queue_position`
(what the fencer is shown), `routers.tournaments.console_queue` (a running count over
rows ordered by it), the teams view's waitlist position, and the Export rosters, whose
queued group is simply the rows in arrival order (`export/ordering.rosterOrder`).

Settled is derived (`Registration.settled`, a hybrid): a live waiver, or a lane holding
credit whose outstanding is within tolerance. Overpayment reads as settled, deliberately
(payment-ledger: an amendment down to nothing keeps the payment).

Matching (`matching._evaluate_single_vs`) credits any registration `_is_payable` —
reserved and not settled — with no regard to whether it holds a place.

Owner decisions (explore session 2026-09-24): demotion for non-payment is mailed; the
demoted go to the end of the queue; the organizer's ↓ keeps the original place; money on
a queued registration is held for the organizer (the auto-fill alternative is a later
setting, off by default); a fully-queued registration never reads as paid.

## Goals / Non-Goals

**Goals:**
- A demotion for non-payment leaves the registration priced for what it holds, placed at
  the end of the queue, and its fencer told.
- No money is credited to a registration that holds no place, and none it already held
  makes it read as paid.
- One ordering key that every reader of queue order reads.

**Non-Goals:**
- Paying substitutes filling free places automatically (`paying-substitutes`).
- The Queue phase as rosters with arrows (`queue-rosters`); this change only keeps the
  current panel correct.
- A way back for a waitlisted team. Teams get the ordering key so the rule is uniform,
  and nothing else.
- Changing when an amendment-added queued placement counts from (see Open Questions).

## Decisions

### D1. `queued_since` on the placement, retained across promotion

`RegistrationDiscipline.queued_since` and `Team.waitlisted_since`, both
`DateTime(timezone=True)`, **not null**, set on creation to the registration's
`registered_at` for every placement, seated or queued. The value means "where this
placement's queue place counts from", and the queue orders by
`(queued_since, registered_at, registration id)`.

Promotion does not touch it. A demotion for non-payment sets it to the demotion moment.
The organizer's return leaves it alone — so a placement never queued returns to its
registration time, and one demoted, promoted and returned takes back the end-of-queue
place its demotion gave it, which is exactly the spec's "the place it held before".

*Alternatives.* A nullable column meaning "queued since, only while queued" would need
the previous value stashed somewhere for the organizer's return to restore it. A
per-registration column cannot express a mixed registration whose seated placement goes
to the end while its queued one keeps its place. Deriving the order from audit events
would put a query over the event log inside every queue read.

The tie-break by `registered_at` gives registrations moved by one settlement (which all
share one `queued_since`) the order the spec asks for.

**Teams count from their entry, not the registration** (owner, 2026-09-25). The team
waitlist was always in entry order (`Team.created_at`), so `waitlisted_since` starts as
the moment the team was entered — the registration time at registration, the amendment
moment for a team an amendment adds — the migration backfills it from `created_at`, and
the waitlist orders by `(waitlisted_since, id)`. Starting it at `registered_at` would
reorder existing waitlists on deploy.

An amendment keeps the moment (and the promotion mark, D6b) of every discipline it keeps;
only a newly named discipline counts from the registration time.

### D2. `_demote` owns the moment and the reprice; callers own the mail

`_demote(registration, now)` sets `queued_since`/`waitlisted_since` on exactly the
placements it moves, recomputes totals with `pricing.registration_total` (as
`return_to_queue` does), and returns what it moved — the discipline slugs and team
disciplines — instead of a bare bool. Each of the three call sites mails
`emails.send_demoted` after its commit, with that list, because the mail must be sent
only for a committed demotion and the tick commits per tournament.

The mail is composed with the queue positions *after* the commit, read through
`queue_position`, so it states the position the fencer will see in the app.

`_payment_mail_suppressed` gates it, as every lifecycle mail is gated; a demoted
registration is never dormant, so this only guards a manual tournament's absence of
mail, which the tournament-level exclusion already ensures.

### D3. Fully-queued excludes settled, in both halves of the hybrid

`Registration.settled` becomes: waived, **or** (not fully queued **and** a lane settles
it). "Fully queued" here requires at least one placement, so a registration with no
entries and no teams is not caught by a vacuous `all()`. The Python half reuses
`fully_queued` plus a non-empty check; the SQL half is two `NOT EXISTS` subqueries
(a seated entry; a non-waitlisted team) plus an `EXISTS` of any placement.

Everything that reads settled follows: `_is_payable` (so matching stops treating it as
paid), `wire_state`, the Export active switch and summary, the payments table state,
`_demotable` (unaffected: a fully queued registration has nothing to demote).

A waiver still settles it. A waiver is a person's statement that nothing is owed; it is
not money in the queue.

*Alternative rejected:* not repricing at demotion (owner's choice was to reprice and
exclude). The stale total left the demoted registration stating the seat's price as
debt, which is what this change exists to remove.

### D4. Payment on a fully-queued registration: a flag reason, not a new state

`_evaluate_single_vs` gains a branch before the tolerance comparison: a reserved
registration that is fully queued is flagged `registration_queued`, audited as a
`match_conflict`, and `emails.send_payment_while_queued` is sent (the
`send_payment_after_expiry` pattern). Every automatic crediting path — VS, bare token,
multi-registration split, name-assisted — must reach this check; the natural place is
`_is_payable` or a guard beside it, and implementation verifies each path rather than
assuming they share one. Manual linking by the organizer stays
possible — the organizer deciding is exactly what the flag asks for, and linking is
that decision.

Flagged transactions are already re-evaluated by every pass, so after promotion any pass
credits it. D5 makes that immediate.

### D5. Promotion re-evaluates the registration's flagged transactions before mailing

`admit_substitute`, after seating the placement and repricing, runs the matching
evaluation over transactions flagged `registration_queued` whose VS resolves to this
registration, then composes `send_promoted` from the resulting balance. Where the held
money covers the new total the registration reads paid and the mail confirms the place
instead of asking for payment (a branch in the promoted mail, or `send_payment_received`
— whichever the mail module already composes more naturally; decided in implementation,
spec'd by outcome).

Scoping the re-evaluation to this registration's VS keeps promotion from doing a whole
matching pass inside a request.

### D6. Readers of the order

- `queue_position`: counts live substitute placements with a smaller
  `(queued_since, registered_at, id)`.
- `console_queue`: orders by the same key; `QueueEntryOut` gains `queued_since` and a
  `demoted` flag (`queued_since != registered_at`), which `QueueEntryLine` states
  ("ve frontě od …" vs "registrace …").
- Teams view: waitlist position by `waitlisted_since`.
- `sheet.base_rows`: a `queued_since` map `{slug: iso}` beside `substitute_for`;
  `rosterOrder` sorts the queued group by it (stable, so equal moments keep arrival
  order). The export-tables spec already defers to `seating-queue` for queue order.

### D6b. Promotion marks what it seated; a lapse takes back only that

`RegistrationDiscipline.promoted_unpaid` and `Team.promoted_unpaid` (bool, default false).
`admit_substitute` sets it on what it seats when the registration does not read settled
afterwards. It is cleared on every entry and team of a registration whenever a credit,
recorded payment or waiver leaves the registration reading settled (one hook in the ledger
write path, not in each caller), and by the lapse itself.

The expiry pass, for an overdue registration carrying any mark: return the marked entries
and teams through `_demote`-style moves (end of queue, reprice), audit
`promotion_lapsed`, mail the demotion notice; then, if the repriced registration still
does not read settled, still holds a seat, and what it owes was due within the window
that lapsed, fall through to today's lapse outcome for it. Otherwise it is left seated,
its window closed. Before settlement, a `reservation`-mode seat (owed by the seating
deadline) and a `deposit`-mode seat whose deposit is in (balance owed by the deadline)
were never under that window, so a declined promotion does not cost them their seat
(owner, 2026-09-25); after settlement everything owed is owed now. This replaces the whole-registration demotion of
`promotion_lapsed` after settlement and prevents the whole-registration expiry before it.

*Alternative:* derive "what the window was for" from audit events. Rejected: a query over
the event log on every pass, and fragile against repricing.

### D7. Export document v15

`export_json.SCHEMA_VERSION = 15`; entries and teams carry their moments and promotion marks. Importing
v1–v14 sets each moment to the registration's `registered_at`, which is what every such
placement's order was.

## Risks / Trade-offs

- [The settled carve-out contradicts "a credited registration whose total falls to zero
  stays settled" for one population] → stated as an explicit exception in
  `payment-ledger`, with the amendment-to-zero scenario unchanged (it keeps a seat).
- [A registration demoted before this change keeps a stale total and a registration-time
  queue place] → the owner chose not to deal with existing data; the migration only
  backfills moments. A demoted registration holding credit will now read as reserved
  rather than paid, which is the correct reading, and is the only visible shift.
- [Promotion now does matching work inside the request] → scoped to one registration's
  flagged transactions; nothing else in the pass runs.
- [Mail volume at settlement: one mail per demoted registration in one tick] → the same
  order of magnitude as the expiry pass already sends; no batching needed.
- [A fencer whose payment was held and who is then refunded hears nothing about the
  refund from Squire] → unchanged: refunds are settled by hand and communicated by the
  organizer, as for late payments today.

## Migration Plan

One Alembic revision: add both columns nullable, backfill from `registrations.registered_at`
by join, then set not null. Rollback drops the columns. No queue reorders on deploy,
since every moment equals the time the order used to be read from.

## Open Questions

- An **amendment** that adds a discipline which is full queues it with
  `queued_since = registered_at`, as today — ahead of fencers who registered after the
  original registration but before the amendment. Arguably it should count from the
  amendment. Left as today; worth raising with the owner when `queue-rosters` is done.
