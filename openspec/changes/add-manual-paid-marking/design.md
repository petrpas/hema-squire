## Context

Squire has no human verdict about money anywhere. `PAID` is reached from
`matching.py:258` when credit reaches the total, and from
`routers/payments.py:374` when a rejected transaction is reinstated. Both stand
on a bank transaction. `amount_paid_cents` and `outstanding_cents` are derived
from those transactions, and the participant list, the sheet, the export and the
lifecycle all read the state that follows from them.

That is a coherent design and it should stay coherent where Squire collects. It
leaves nothing at all for the organizer who collects the money themselves, which
`add-external-registration` and `regroup-tournament-settings` have just made a
first-class configuration rather than an oversight: *Platby si řeším sám* is now
an answer the organizer picks, and the surface promises that Squire prices
everything and leaves the money alone.

Three things make this smaller than it sounds. The state field already exists and
already means what is wanted. The sheet row already carries `paid` from
`registration.state` (`sheet.py:178`), so the projection needs nothing. And the
audit trail — `PaymentEvent` — already exists and already records payment
history per registration.

One thing makes it larger. Every manual edit in the console today persists as a
**rule**, replayed over a projection; and `rules.replay` is called only from read
paths, so a rule changes the console table and the export and nothing else. This
mark has to reach the registration itself.

## Goals / Non-Goals

**Goals:**

- The organizer who collects the money can record who has settled, and undo it.
- Squire never claims an amount it did not see.
- Where Squire collects, nothing changes at all: the state keeps standing on
  transactions alone.
- Every mark says who made it.
- The public list shows what a person has asserted, and asserts nothing else.

**Non-Goals:**

- Matching a bank statement where Squire handles no payments. That is the
  machinery, and this is a tick.
- Recording *how* the money arrived, or when, beyond the audit event's own
  timestamp. An organizer who needs that has a spreadsheet; Squire is not
  becoming their cash book.
- Partial settlement. The mark answers a yes/no question. Where amounts matter,
  the tournament wants Squire handling its payments.
- Making the mark survive a switch to Squire-handled payments as though money
  had arrived. It does not, and the switch has to say so.

## Decisions

### Decision 1: The mark writes state, and leaves the money counters alone

`registration.state` becomes `PAID`. `amount_paid_cents` and
`amount_paid_eur_cents` stay exactly as they were, which on such a tournament is
zero.

The alternative — writing the outstanding amount into the paid counter so the
arithmetic comes out at zero — was rejected. Those counters mean *money Squire
saw*: the reconciliation fills them, the export carries them, and
`add-payments-console-ui` added the outstanding column so an organizer can read
what is still owed against them. Filling them from a tick would put a number
Squire invented into the same field as numbers it read off a statement, and
nothing downstream could tell the two apart.

The visible consequence is that a hand-settled registration reads as paid with
an outstanding balance equal to its total. That looks wrong until you know what
the columns mean, and it is the honest reading: the fencer owes nothing, and
Squire received nothing. Where the two can differ, the column that says what
Squire received must keep saying it. The console's own copy carries the
explanation.

### Decision 2: Refused where Squire handles the payments

The endpoint answers 409 on a tournament whose payments setting is on, exactly as
`bank.require_payments_enabled` answers 409 the other way round.

Two routes into `PAID` on one tournament is the failure to avoid. A statement
imported after a hand-mark would find a registration already paid and either
double-credit it or skip it, and an organizer reading the roster could not tell
which entries a machine had verified. The state means one thing per tournament
because only one thing may write it.

This is the mirror of the existing guard rather than a new kind of rule, which is
why the refusal reads the same way: the tournament's payments setting decides who
owns the state.

### Decision 3: A `PaymentEvent`, because the trail already exists

Every consequential thing that happens to money on a registration is already a
`PaymentEvent` with a kind — `reminder_sent`, `reservation_expired`,
`seating_demoted`, `expired_holding_payment`. Two more kinds, for marking and
unmarking, and the actor's identity in the detail.

No new table, and a roster that says paid can always answer who said so and
when. The alternative — a column on the registration recording who marked it —
would answer only the last question and would lose an unmark entirely.

### Decision 4: The Payments phase is always offered, and boned out where Squire collects nothing

The phase stays. What it holds follows who handles the payments.

Where Squire handles them, it is what it is today: the queues, the intake card,
the tolerance, the transactions, the variable symbols, the windows. Where it does
not, it holds one thing — whether each registration is settled, and the action
that changes it. Nothing else, because nothing else on that phase has any meaning
when no money passes through Squire.

This overturns an earlier draft of this design, which put the column on Fencers
because `etl-console` says the Payments phase is offered only while the payments
setting is on. Keeping the phase and emptying it is better on two counts.

The phase is *already* the place a reader looks for who has paid, whichever way
the tournament is run, so the answer does not move depending on a setting the
reader may not know about. And it keeps the dependence where it belongs: a
phase's **columns** stay a property of the phase alone, and it is the phase's
**content** that varies — which `setup-navigation` and `etl-console` already do
for other settings, rather than being a new kind of thing.

The consequence is that two requirements move: `etl-console`'s rule that the
Payments phase follows the payments setting, and `payments`' own statement that a
tournament Squire collects nothing for offers no Payments phase. Both said the
same thing and both are now half right — no reconciliation, but a phase.

### Decision 5: The public list marks the settled and marks nobody else

`add-external-registration` fixed that where Squire guarantees no payment state,
the list draws no confirmed/unconfirmed distinction, because reading a
registration's state as its attendance was meaningless there. The reason was that
nothing asserted anything. Now something does.

So: an entrant the organizer marked is shown **confirmed**. An entrant not marked
is shown with **no mark at all** — not "unconfirmed". The absence of a tick is not
a claim; it is an organizer who has not got to that row yet, and a public page
that turned it into "has not paid" would be Squire inventing the very assertion
it just stopped making.

The unpaid-list setting (hidden / greyed) stays inapplicable here, for the reason
it was made inapplicable: it is a setting about unpaid *reservations*, and there
are none in the sense it means.

## Risks / Trade-offs

**[A tournament is switched to Squire-handled payments afterwards] → Accepted,
and deliberately unhandled.** It carries registrations marked paid with nothing
behind them: reconciliation finds nothing to match, and the outstanding column
reads the full total against a registration whose state says paid.

Nothing is built for it (owner's decision). The three alternatives each cost more
than the case is worth: clearing the marks silently discards what a person
entered by hand, refusing the switch puts a bar on a setting that is otherwise
always changeable, and counting them in the confirmation is a number nobody has
yet needed. The organizer who switches owns the consequence, and the state is
recoverable by hand in the direction they came from.

**[Paid with a full outstanding balance reads as a bug] → It is the honest
reading, and the copy has to carry it.** Anything else means Squire writing a
number it did not observe. Both the console column and the participant list are
places where a reader could be misled, so both need to say what the mark means.

**[The console's idiom is rules over a projection, and this writes through] →
Stated in the proposal and here, so it is deliberate.** A rule would change the
table and the export and reach neither the public list nor the meaning of the
state. This is the first console action that writes to a registration, and it
should stay the only one until something else earns it.

**[An organizer marks the wrong person] → Unmarking is the same action
reversed**, and both directions are audited, so the roster and the trail
disagree with nobody.

## Migration Plan

No schema change and no data migration: the state, the counters and
`PaymentEvent` all exist. Nothing is written to an existing tournament by
deploying this.

Rollback is the revert. Registrations marked before it would keep their state,
which reads exactly as a reconciled payment would — the audit events are what
distinguish them, and they survive.

## Open Questions

- None outstanding. The one that was here — what the switch to Squire-handled
  payments should do about hand-settled registrations — is answered above:
  nothing. Reopen it if a live tournament ever makes the case concrete.
