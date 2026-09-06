## Context

The disciplines cell opens only for a row with no registration behind it. That
condition was written when issuing was a button the organizer pressed when they
were ready; it is now a step of payment intake, so every imported row has a
registration within seconds of arriving. The guard now closes the cell always,
and the organizer meets a feature that appears broken.

The guard was protecting something real. An issued registration's disciplines
are its `RegistrationDiscipline` entries, and those decide what it is billed and
where it is seated. Console cell edits are `field_edit` rules, and `field_edit`
writes the **projected row** (`rules.py`, `_apply_field_edit`), not the
registration. Letting it through unchanged would have made the table disagree
with the money.

What has changed since is that Squire already knows how to move both together.
`routers/registrations.amend_registration` replaces entries, recomputes the
total through `pricing.registration_total`, re-places against capacity, records
a `PaymentEvent`, and mails the fencer. The organizer needs that operation, not
a new one.

## Goals / Non-Goals

**Goals**

- The disciplines cell opens on the fencer list for every row.
- An edit to a row with a registration changes the registration, priced by the
  same call the fencer's amendment uses.
- The edit is withdrawable from the manual-edits log, and withdrawing it prices
  back.
- The organizer is not bound by the fencer's amendment window.

**Non-Goals**

- Editing extras, weapon rentals or the afterparty from a cell. They have the
  same shape and could follow later; this change is scoped to the column the
  organizer cannot use.
- Changing the fencer's own amendment: its window, its confirmation mail and its
  refusal outside RESERVED/PAID stay exactly as they are.
- Team disciplines. A team is entered through the tournament's team handling
  (`etl-console`, Manual entry fields follow the tournament's structure), and
  the cell offers individual disciplines only, as it does today.

## Decisions

### Decision 1 — One amendment core, reached from two sides

`amend_registration` currently holds both the HTTP concerns (the window, the
fencer's own registration, the response) and the amendment itself (drop the
selection, re-place, re-price, event, mail). The amendment itself moves to a
function both callers use.

The alternative — the console calling the fencer's endpoint, or reimplementing
the steps — was rejected on the same ground `_settle` is shared between the two
routes money takes: the second copy is where the drift starts. A discipline
correction that priced differently from the fencer's own amendment would be a
defect nobody could see from either side alone.

The core takes what differs as parameters rather than sniffing at the caller:
whether to seat unconditionally, and which notice (if any) to send.

### Decision 2 — Placement follows the registration's origin, not the actor

This is the decision that most nearly went wrong. The fencer's amendment joins a
full discipline as a substitute placement in place. Applying that to an issued
registration would contradict `imported-registrations`, **Capacity does not
apply to an issued registration**, which is normative and well argued: a
substitute placement is not billed, so queueing a correction to an imported
roster would make that fencer free. An organizer fixing a typo would silently
stop charging them.

So placement follows what the registration *is*:

| Registration | A newly named discipline that is full |
| --- | --- |
| Issued (clocks dormant by origin) | seated, and billed |
| Made in the application | substitute placement in place |

Both branches are the rule already written for that kind of registration; the
console reaches them, it does not invent a third. `registration.clocks_dormant`
is the discriminator, because it is what already records the origin — read
directly rather than through `setup.dormancy_cause`, which also answers for
tournament-wide causes that say nothing about where this registration came from.

**Where a different call is defensible:** one could argue an organizer's hand
should always seat, whatever the registration's origin, on the ground that the
organizer is stating who competes. That would be a one-line change to the table
above and a sentence in the spec. It is not taken here because it would let the
console seat a fencer over the heads of a queue the fencer's own amendment
respects, and nothing in the reported problem asks for it.

### Decision 3 — Mail only where the correction costs the fencer

The fencer's own amendment always writes: a surcharge demand where they now owe
more, a confirmation otherwise. The organizer's correction sends the surcharge
notice on the same condition and sends nothing otherwise.

The asymmetry is the point. The fencer amending their own entry expects an
acknowledgement. The organizer straightening forty imported rows is correcting a
record, and a confirmation per row would make the correction cost more than the
error — while the surcharge notice carries information the fencer cannot get any
other way and must act on.

Dormancy does not suppress it. What dormancy suspends is the passage of time —
reminders and expiry — not a statement about money that has just changed.

### Decision 4 — A rule kind whose subject is the registration

The amendment persists as a rule of a new kind, so it appears in the phase's
manual-edits log and can be withdrawn there like every other console decision.
Rules being withdrawable is what makes the console safe to work in; an edit that
moved money and could not be taken back would be the one exception, and it would
be the one most worth taking back.

The kind departs from every existing one in that its handler does not write
`rows[target][field]`. That is stated in the spec rather than left as an
implementation quirk, because a future editor reading `HANDLERS` will otherwise
assume the projection is the only subject a rule has.

The rule carries the discipline slugs it names, validated against the
tournament's offered individual disciplines when it is created — the same
validation `field_edit` already applies to `disciplines` (`rules.py`), and for
the same stated reason: an unknown slug would otherwise be met later as a row
that mysteriously will not bill.

### Decision 5 — The organizer's edit is not gated by the amendment window

`setup.amendment_availability` and the registration's dormancy govern the
fencer. The organizer's correction is gated only by console access and by the
registration still describing a competitor: expired and cancelled are refused,
as they are for the fencer, because those return through re-registration with a
new symbol.

This follows what the team roster save already does — never gated by
`amendment_availability` (`routers/registrations.py`) — so the console has one
answer about windows rather than two.

## Risks / Trade-offs

**A correction can silently change what a fencer owes.** → The load-bearing
test is not that the total changed but that it changed *by the right amount at
the right moment*: a registration made before an early-bird deadline, corrected
after it, must be repriced at early-bird prices. A test asserting only that the
total moved would pass against an implementation that repriced at today's fees,
which is the defect `imported-registrations` explicitly forbids.

**Withdrawal has to price back, and pricing is not obviously invertible.** →
Withdrawal is not an inverse operation but a replay: the remaining rules are
re-applied over the registration's issued selection, exactly as **Rule
lifecycle** already requires of every other kind. The test that matters is two
amendments with the first withdrawn, which a naive "undo the last thing" gets
wrong.

**The two placement branches can be tested into agreement by accident.** → Both
branches need a test with a genuinely full discipline. A test whose discipline
has spare capacity passes under either rule and proves nothing about the one it
names.

**Factoring the amendment core can change the fencer's path.** → The fencer's
existing amendment tests are the guard, and they run unchanged. The refactor is
correct only if none of them is touched.

## Migration Plan

None. No schema change: the amendment writes rows that already exist
(`RegistrationDiscipline`, `Registration.total_amount`, `PaymentEvent`) and the
new rule kind is a value in an existing column. Existing `field_edit` rules on
`disciplines` continue to replay as they do today, since they belong to rows
that had no registration when they were made.

## Open Questions

None outstanding. The placement question raised in Decision 2 is decided there;
it is recorded as the one point where a different call would be defensible if
the organizer's hand should outrank a queue.
