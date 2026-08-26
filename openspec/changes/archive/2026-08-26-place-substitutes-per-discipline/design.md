## Context

See proposal.md — Why.

Three facts about the current code shape the approach:

**`is_substitute` is already per entry.** It lives on `RegistrationDiscipline`,
and `amend()`, `_demote()` and `admit_substitute()` all write it one entry at a
time. Only `register()` computes a single flag for the whole registration
(`as_substitute = bool(full)`, `registrations.py:454`). There is no data model
work here — only one writer to bring in line with the rest.

**The queue's counting queries encode the all-or-nothing rule as an
optimization.** `queue_position()`, `queue_length()` and `team_queue_length()`
filter on `Registration.state == RESERVED`. That is correct only while a queued
registration can never be paid — which is exactly what `register()`'s bulk flag
guaranteed. `seating-queue` states the invariant explicitly and gives the
optimization as its reason. Remove the rule and the queries are wrong.

**A paid registration holding a substitute entry can already occur.** Register
into a full discipline, get promoted into one of several queued disciplines
(`admit_substitute` requires RESERVED, which holds at that moment), then pay.
The registration is now PAID with a substitute entry still queued — invisible in
`queue_length`, and unpromotable ever after, because promotion will now refuse
it. So the counting defect and the promotion dead-end are already reachable;
per-entry registration turns them from a rare organizer-made accident into the
common path. Squire is pre-launch and holds no real data, so this is an argument
about the rule being wrong, not about records needing repair.

Constraints: no migration is needed — `is_substitute` is already per entry — the
queue must keep holding no money, and `return_to_queue`'s refusal on a paid
registration must survive, since demoting a paid seat would need a refund the
queue is designed never to owe.

## Goals / Non-Goals

**Goals:**

- One placement rule, applied by every writer: an entry is a substitute when its
  own discipline is full at the moment it is placed.
- Queue membership derived from the entry, so a fencer's position and the queue's
  length do not depend on what they have paid for a different discipline.
- Promotion that works on any live registration and asks only for what the new
  placement adds.
- No stored value changes and no backfill; a registration that already holds a
  queued placement becomes correctly counted rather than migrated.

**Non-Goals:**

- Any per-row "only if I get in" opt-in. `wait_for_all` is removed, not replaced.
  The all-or-nothing stance may return later as a deliberate per-discipline
  choice; this change does not design it.
- Changing team placement. `_team_waitlist_flags()` already does the right thing
  and is touched only where it shares the queue-counting predicate.
- Changing what capacity means. `taken_seats()` already counts the right rows.
- Reworking refunds, cancellation, or the seating settlement.

## Decisions

### D1 — One placement helper, used by both writers

`register()` and `amend()` compute the same thing from the same inputs, and
`amend()` already computes it correctly:
`is_substitute = discipline.slug in full`. Extract that into a single helper
returning the per-discipline placement for a set of selected disciplines, and
call it from both.

*Why a shared helper rather than copying the one-liner:* the two paths have
already drifted once, silently, and the drift was invisible because each side
looked reasonable on its own. A helper makes the next divergence a deliberate
edit rather than an omission.

*Alternative rejected — leave `amend()` alone and fix `register()` in place.*
Cheaper by one refactor, but leaves two independent expressions of one rule,
which is what produced this change.

### D2 — `wait_for_all` and the `409 full_disciplines` refusal are removed, not deprecated

The field comes off `RegisterIn`, the branch comes out of `register()`, the type
comes off `api.ts`, and the form stops sending it and drops its catch block.

*Why removal rather than accept-and-ignore:* nothing outside the in-app form
sends it — the importer does not, and `RegisterIn` is shared with amendment,
which has always ignored it. A field that is accepted and ignored is a field the
next reader has to prove is dead. Removing it now is a one-line API break with no
live caller.

*What is lost:* the 409 was also the only signal for the race where a row the
fencer saw as open filled while they were typing. Under per-entry placement they
are queued for it instead, and told so in the response and the confirmation. The
fencer is informed rather than asked — which is the point of the change, applied
consistently.

### D3 — Queue membership is a predicate over live registrations, written once

The three counting queries stop asking `Registration.state == RESERVED` and start
asking whether the registration is **live**: reserved within its validity window,
or paid. That predicate already exists, inline and duplicated, inside
`taken_seats()` and `taken_team_slots()` — the same disjunction spelled out twice.
Extract it into `availability.py` as one reusable SQLAlchemy clause and use it in
all four places plus `queue_position()`.

*Why liveness rather than "not cancelled and not expired":* it is the predicate
capacity already uses, so a seat and a queue place are counted against the same
notion of a registration that still exists. Two different liveness definitions in
one module is how this class of bug starts.

*Alternative rejected — keep the queue counted from reserved registrations and
forbid a mixed registration from reaching PAID.* It preserves the invariant
verbatim, but calls a fencer unpaid who has paid everything they were asked for,
and re-arms the expiry scheduler against them. It trades a query fix for a lie in
the data.

### D4 — Promotion drops its state guard and follows the amendment's surcharge path

`admit_substitute()` currently refuses anything not RESERVED. It instead refuses
only cancelled and expired registrations, and after seating the placement:

- recomputes `total_amount` / `total_eur` as it already does — the frozen unit
  prices mean this yields the correct new total, not a repriced one;
- lets `outstanding_cents` derive the balance against `amount_paid_cents`, which
  is what "bill the difference" means in this codebase — no separate surcharge
  figure is stored;
- opens a fresh window via `_promotion_expires_at()`;
- leaves the state alone. A PAID registration that now owes more stays PAID and
  owes, exactly as `amend()` leaves it (`registrations.py:748`).

*Why mirror amendment:* it is the same event — a paid registration gains a priced
row — and it already has a settled answer, including `send_surcharge_due` and the
`registration_amended` audit event. Inventing a second answer for promotion would
put two rules on one situation.

*Consequence, accepted:* a paid registration owing a promotion surcharge is never
expired, because the expiry pass only selects RESERVED rows. The fencer keeps the
promoted seat while owing for it, and the organizer's route is cancellation —
identical to a fencer who amends a paid registration and never pays the
difference. See Risks.

### D5 — A registration holding a substitute placement is demoted, never expired

The expiry pass currently branches on whether *seating has settled*. It gains a
second reason to demote rather than expire: the registration holds a substitute
placement. `_demote()` already does exactly the right thing — every seated entry
becomes a substitute, every seated team is waitlisted, the window closes, the
registration stays RESERVED in its original order — so this is a branch, not new
machinery.

*Why:* the queue place was never what the money was for. Expiring it makes an
unpaid rapier seat cost a longsword queue position the fencer owed nothing for.
The system already refuses to make that trade one step later, when a lapsed
promotion after settlement returns to the queue instead of expiring; this applies
the same reasoning before settlement, where mixed registrations now live.

*Alternative rejected — expire the whole registration.* One fewer branch and
simpler to explain ("you didn't pay, you're out"), but it silently punishes a
queue place for an unrelated debt, and the fencer has no way to see the link.

*Audit:* a distinct `PaymentEvent` kind from `promotion_lapsed`, since the cause
differs — an unpaid seat rather than an unpaid promotion.

### D6 — The promotion notice is its own mail

Promotion currently sends `send_registration_confirmation`, which states the
registration's total. For a fencer who has already paid, that reads as a demand
for money they have sent. The new mail names the discipline whose place opened,
states the amount now due, and states its due date — modelled on
`send_surcharge_due`, which already renders an outstanding amount per currency.

*Why not just call `send_surcharge_due`:* it says nothing about which discipline
opened, and the fencer's news is that they got in. A promotion that opens no
window (payments off) also has to say the same thing with no amount due, which
the surcharge mail has no shape for.

*Scope:* one new template in both locale bundles, following the existing mail
conventions.

## Risks / Trade-offs

**A paid registration can hold a promoted seat it has not paid the surcharge for,
indefinitely** → The expiry pass only touches RESERVED rows, so nothing reclaims
it on a clock. This is not new: an amendment that adds a priced row to a paid
registration behaves identically today. The organizer's route is cancellation, and
the surcharge is visible on the registration and chased by the reminder pass.
Making promotion expire a paid registration would be a new and larger rule about
paid registrations generally, and belongs to its own change if it is wanted.

**More fencers now owe money earlier.** Under all-or-nothing, a fencer with any
full selection owed nothing until an organizer acted. Now they owe for their
seated disciplines immediately. That is the intended behaviour — they hold a
seat — but it will increase the number of small reservations under a payment
window, and with it the expiry-and-demote traffic.

**`RegisterIn.wait_for_all` is a breaking API change** → Nominally. There is no
caller outside the in-app form, which ships in the same change, and no third-party
client exists to break. Recorded for the API's history rather than as a risk to
manage.

## Migration Plan

No schema change and no backfill. `is_substitute` and every state value keep
their meaning; only the code that writes and counts them changes.

Squire is pre-launch with no real data, so there is nothing to sequence and
nothing to roll back to. Backend and frontend ship together because the form
sends `wait_for_all` until it is updated, and both are in this change; if they
are ever split, the frontend goes first, since dropping a field the backend still
accepts is harmless.
