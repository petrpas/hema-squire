## Why

An organizer who takes the money themselves — cash at the door, their own QR
code, a club account — has no way to record who has settled. Squire knows what
everyone owes; it has nowhere to put the answer.

Marking a registration paid by hand exists nowhere in the product today, in any
configuration. `PAID` is reached from exactly two places, and both stand on a
credited bank transaction: `matching.py:258`, where credit reaches the total,
and `routers/payments.py:374`, where a rejected transaction is reinstated. Even
on a tournament Squire collects for, the state is a consequence of money it saw.
There is no human verdict anywhere in it.

That is right where Squire collects — a state asserted without money would be a
claim the reconciliation could contradict on the next statement. It is wrong
where Squire collects nothing. There the organizer is the only one who knows,
and the roster is the thing they need it written on.

The gap became visible while writing the settings surface. The payments setting
now reads *Platby si řeším sám* — "I handle the payments myself" — and states
that Squire still prices everything and leaves the money alone. Which is true,
and leaves the organizer with a priced roster and a pen.

## What Changes

- **An organizer can mark a registration paid by hand**, and unmark it, on a
  tournament whose payments Squire does not handle.
- **The mark records the verdict, not an amount.** The registration becomes
  paid; `amount_paid_cents` stays at zero, because no money passed through
  Squire and it will not claim otherwise. What the tournament is owed remains
  computed from its prices; what has been *received* is a number Squire only
  ever fills from a transaction it saw.
- **It is refused where Squire handles the payments**, so the state there keeps
  standing on transactions alone. Two routes into `PAID` would mean a later
  statement could contradict a human, and neither would know it had.
- **Every mark is audited**, naming the organizer who made it, so a roster that
  says paid can always say who said so.
- **The public participant list shows a marked entrant as confirmed.** This
  narrows a rule `add-external-registration` has just set: that no
  confirmed/unconfirmed distinction is drawn where Squire guarantees no payment
  state. The reason it set that rule was that nothing was asserting anything —
  now something is, and by a person who knows. An entrant *not* marked SHALL
  carry no mark at all rather than being called unconfirmed: the absence of a
  tick is not a claim that someone has not paid, and the organizer marks their
  roster in the order they get to it.
- **The Payments phase is offered on every tournament, and boned out where
  Squire collects nothing** — holding whether each registration is settled and
  the action that changes it, and nothing else. It stops being a phase that
  disappears with a setting and becomes one whose contents follow it, so that
  "who has paid" is answered in the same place however the tournament is run.

Not in scope: matching a bank statement on a tournament whose payments Squire
does not handle. That was the question this one grew out of and it is a
different, larger thing — the intake, the parser, the queues and the tolerance
all belong to the machinery that is switched off. A tick needs none of them.

## Capabilities

### Modified Capabilities
- `payments`: gains what an organizer may assert by hand where Squire handles no
  payments, what such a mark records and does not record, and that it is refused
  where Squire does handle them.
- `registration`: the public participant list marks a hand-settled entrant as
  confirmed, and marks nobody unconfirmed.
- `etl-console`: the Payments phase is offered whatever the payments setting and
  carries only the settled mark where Squire collects nothing; the mark is a
  write to the registration rather than a rule over the projection.

## Impact

**Backend** (`backend/app/`): an endpoint on the registrations router — not the
payments router, every path of which is gated on the payments setting being on,
which is exactly the case this serves; a `PaymentEvent` for the audit; the
participant list's confirmed rule; `sheet.py`'s row already carries `paid` from
`registration.state`, so the projection needs nothing.

**Frontend** (`frontend/src/`): `offeredPhases` stops removing the Payments
phase; the phase's own body branches on who handles the payments, showing its
present contents or the settled column alone. `PHASE_COLUMNS` gains a second
entry for the boned-out phase rather than a condition inside the existing one.

**This is a write to the registration, not a rule.** Every other manual edit in
the console persists as a rule replayed over a projection, and `rules.replay` is
called only from read paths — so a rule would change the table and the export
and nothing else. The public list, and the meaning of the mark, need the
registration itself. Stated here because the console's whole idiom is the other
way round, and the departure should be deliberate rather than discovered.

**Risk, accepted and unhandled**: a tournament switched from "I handle the
payments" to "Squire handles the payments" afterwards carries registrations
marked paid with no money behind them, which reconciliation will not match.
Nothing is built for it — clearing the marks discards what a person entered,
refusing the switch bars a setting that is otherwise always changeable, and
warning about it is a number nobody has needed. The organizer who switches owns
it.

**Verification**: `pytest` for the endpoint, its refusal, the audit and the
participant list under each configuration; `vitest` for the column appearing
only where it should and the toggle; and a look at the Fencers phase on a
tournament that collects nothing, since a column that appears conditionally is
a layout claim.
