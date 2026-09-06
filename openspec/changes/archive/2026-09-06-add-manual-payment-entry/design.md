## Context

Money reaches a registration in exactly one way today. `matching._evaluate` (
`matching.py:495`) credits a bank transaction to the registration its variable
symbol names and calls `_settle`, which sets the state, applies the deposit
threshold, records a `PaymentEvent` and sends the mail. Two other paths —
reinstatement and mark-for-refund in `routers/payments.py` — credit directly and
duplicate the parts of that they need. There is no payment table: a credit is an
integer added to `Registration.amount_paid_cents`, and its provenance is the
`BankTransaction` row that carries `matched_registration_id`. Reversal is by the
same arithmetic, and the payment-link rules record the amount they credited
precisely so that removing one subtracts what it did rather than what today's
balance suggests (`matching.py:751`).

`add-manual-paid-marking` put a human verdict beside all of that, and walled it
off: `_require_squire_collects_nothing` (`routers/registrations.py:883`) refuses
the mark wherever `feature_payments` is on. The mark writes state and no amount,
stores nothing, and is deduced on read from a paid registration with empty
counters.

Both asks land inside that wall. One is money with an amount, which the ledger
must carry. One is a waiver, which the ledger must not carry and the roster
must. And the deduction stops working the moment a registration can be both
partly hand-paid and partly waived.

The console's own idiom pulls the other way and has to be resisted twice.
Manual edits there persist as **rules** replayed over a projection, and
`rules.replay` runs only on read paths — so a rule reaches the table and the
export and nothing else. `add-manual-paid-marking` already made this departure
once for the mark. Both actions here are writes to the registration for the same
reason: the state, the mail, the scheduler and the public list all read the
registration, not the projection.

## Goals / Non-Goals

**Goals:**

- An organizer who took money outside the feed can record it, and Squire treats
  it as money: partial, deposit, window, outstanding, mail, all unchanged.
- An organizer can say a registration owes nothing without Squire claiming a
  single haléř arrived.
- Every credit can still answer where it came from, after the fact and in the
  export.
- Removing a hand-recorded payment reverses exactly what it credited.
- One settled-by-hand action, meaning one thing, on every kind of tournament.
- A statement arriving later never silently doubles hand-recorded money.

**Non-Goals:**

- Amounts on a tournament whose payments Squire does not handle. That line
  stands.
- A cash book: takings, drawer reconciliation, receipts, refunds of
  hand-recorded money.
- Editing a recorded payment. Remove it and record the right one; an edited
  credit is two reversals pretending to be none.
- Bulk entry. Each recorded payment is a deliberate act with a mail behind it.

## Decisions

### Decision 1: One counter, provenance on the payment

A hand-recorded payment adds to `amount_paid_cents` (or `amount_paid_eur_cents`)
exactly as a bank credit does. `outstanding_cents`, `_apply_deposit_threshold`,
`scheduler.py:168` and the export need no changes and cannot be forgotten.

The counter's meaning therefore moves, from *money Squire saw in a statement* to
*money credited, by a statement or by a person who said so*. That is a real cost
and it is written into the model's comment, because the old sentence is quoted
in three places.

**Rejected: a second counter.** `amount_paid_cents` keeps its old meaning and
`amount_paid_hand_cents` holds the rest. Every reader must then sum two fields,
and there are five: the outstanding property, the deposit threshold, the
scheduler's expired-holding test, the console's credited amount, the export. The
one that is forgotten is a reservation that expires holding money the organizer
was told had been received. A meaning that must be remembered in five places is
worse than a meaning that changed once.

**Rejected: a synthetic `BankTransaction` with `source="organizer"`.** Nothing
downstream would change at all, which is the attraction. But the transaction
list is the statement ledger — it is what an organizer reads against their bank
account, and what the intake deduplicates against. A row no bank sent would have
to be excluded from every one of those readings by a condition, and the first
one missed is a reconciliation that balances against a figure the bank does not
have. The provenance question is answered by asking a different table, not by
filtering this one.

So provenance lives on a new record rather than on the registration: a
registration may hold a bank credit and a hand-recorded one at once, and the
question "where did this money come from" is asked of the money.

### Decision 2: `ManualPayment` is a sibling of `BankTransaction`

A new table, one row per payment the organizer records:

- `tournament_id`, `registration_id` — always a registration, never a floating
  credit. There is no unmatched queue for money a person entered; they entered
  it against someone.
- `amount_cents`, `currency` — one of the tournament's two currencies, chosen by
  the organizer, credited to that currency's lane. The lanes are never summed
  (`models.py:686`) and this does not start.
- `received_on` — the date the organizer says the money arrived, which is not
  the date they typed it in. Reminders and expiry read `expires_at`, not this,
  so it is provenance rather than a clock.
- `method` — cash, transfer, card, other. A short closed set with an `other` and
  a note, because "how did it arrive" is the first question asked of a payment
  nobody can look up.
- `note` — free text.
- `recorded_by`, `created_at` — who said so and when.
- `removed_at` — soft delete, so the record of a wrong entry and its reversal
  both survive. The rules journal already works this way.

The credited amount is the row's own `amount_cents`, so removal subtracts
exactly it. There is no need for the payment-link rules' separate
applied-amount field: a hand-recorded payment credits one registration and
distributes nothing.

### Decision 3: `_settle` is reached from both routes, not copied

`matching._settle` is the one place that knows what happens after a credit: the
partial-versus-full test against tolerance, the deposit threshold, the
`PaymentEvent`, the overpayment's refund state, and which mail goes out. It
takes a `BankTransaction` today, and uses it only to hang events off.

Its transaction parameter becomes optional, and the events it writes carry the
`ManualPayment` id in their detail where there is no transaction. Recording a
payment then credits and calls it, and every consequence follows identically.

**Rejected: a parallel settle for hand-recorded payments.** It would be forty
lines that must stay in step with the original through every future change to
tolerance, deposits or mail, and the first drift is a deposit that closes a
window on one route and not the other.

**Tolerance applies unchanged.** A hand-typed figure needs no tolerance for bank
rounding, but tolerance here is what decides *settled versus partial*, and a
registration must not be settled by one route and partial by the other at the
same number.

**The confirmation mail is sent.** The fencer's inbox should not know which
route their money took; they paid, and Squire tells them it has them down as
paid. The case against is backfilling an already-run tournament, where a
handful of stale confirmations go out — the action is one row at a time and the
organizer sees what they are doing.

### Decision 4: The mark is stored, and it is one action

`Registration` gains `settled_by_hand_at` and `settled_by_hand_reason`. The
existing endpoint writes them and drops `_require_squire_collects_nothing`.

Stored rather than deduced, because the deduction — paid with empty counters —
was sound only while a paid registration on such a tournament could have no
other cause. It now can: a waived registration may also hold a recorded partial
payment, and a hand-paid one may hold a full one. What a person asserted is a
fact about the registration and belongs written down.

One action rather than two, because it is one thing in both places: *settled
with nothing passing through Squire*. Where Squire collects nothing, that is
every settled registration, and it reads as the organizer's word that they were
paid — exactly today's meaning. Where Squire collects, that is the waiver, and
it reads as: this one owes nothing and nothing arrived.

**The reason is required where Squire collects and optional where it does not.**
Not an inconsistency: where the ledger is live, a paid row holding zero beside
rows holding real credits is a puzzle a reader will otherwise try to solve as an
error, and the answer is one short phrase — *volná účast*, *sponzor*. Where
there is no ledger at all, every row is that row and the phrase would be
ceremony.

### Decision 5: A waiver writes no amount, and the balance reads waived

Both counters stay untouched, so nothing that sums received money moves — which
is the whole of the second ask. `outstanding_cents` therefore still returns the
full total, and every surface showing it must read the mark and present *waived*
rather than a debt.

**Rejected: crediting the total as a non-money line.** The arithmetic would come
out at zero with no surface changed, and every sum of received money would then
have to subtract waiver credits — the same five-readers problem as Decision 1,
except now failing in the direction that invents money.

`paid_at` is stamped as it is today. `refund_state` is untouched: nothing
arrived, so nothing is refundable.

### Decision 5b: One balance, decided in one place

Decision 5 sends every surface showing a balance to read the mark first. Doing
that revealed that those surfaces were already reading the balance wrongly, for
a reason that predates this change: they each took `outstanding_cents` and
`outstanding_eur_cents` and printed them as `X (Y)`. The two are alternative
prices for one place, so once either lane is credited the other still holds its
full total while nothing is owed in it. On the pilot tournament no EUR lane had
ever been credited — a euro transfer arrives through a Czech bank already
converted, so it lands in the local lane — and so 51 of 53 registrations were
stating a euro debt, including every one that had paid in full.

So the decision moves off the surfaces and onto the registration:
`Registration.balance_cents(tournament)` returns one signed amount and the
currency it is in. The lane the money arrived in decides; the local lane
decides where none has. A settled registration reads zero unless the figure is
past tolerance, which keeps a surcharge (`registration`, amendment upward) while
dropping what the settle forgave — the same tolerance, asked the same way, in
both signs.

**Why not leave the pair and fix the readers.** There were four, and two were
wrong in ways nobody had noticed: the fencer's own page showed the euro lane to
every paid fencer, and `underpaid` in the amend endpoint `or`-ed the two lanes,
so it was true for every registration and every amendment of a paid one sent a
surcharge demand. A shape that four readers got wrong in three different ways
is the wrong shape, not four bugs.

**Kept as a pair: the price and the payment instructions.** Both currencies on
a total are correct — that is what the place costs — and a reminder offering
both prices is an offer, not a conversion. Only the *balance* collapses.

### Decision 6: The collision is already handled; name it, do not build it

A hand-recorded payment settles a registration. A statement carrying that same
money lands later on the same VS. The matcher reaches
`elif registration.state != RegistrationState.RESERVED` (`matching.py:449`),
flags the transaction `registration_paid`, credits nothing, and writes a
`match_conflict` event. The organizer resolves it in the flagged queue: reinstate
if it is more money, mark for refund if it is the same money twice, or remove
the hand-recorded payment if theirs was the mistaken one.

Where the hand-recorded payment was partial, the registration is still
`RESERVED`, the bank row credits normally, and the sum overshoots — `_settle`
flags the overpayment and sets `refund_state` to pending, which is the same
queue by the other door.

So no new machinery. What is new is that the flagged queue must say *why* in
words that name the possibility: this registration was settled by hand, and
here is the payment that did it.

**Rejected: refusing to credit a transaction against a hand-settled
registration, or warning at entry time against an existing credit.** The first
is what already happens; the second guesses. An organizer recording a second
payment against a part-paid registration is the normal case, not a mistake.

### Decision 7: Where the actions live

Recording and removing a payment go on the **payments** router, gated by
`bank.require_payments_enabled` as its neighbours are: they mean nothing where
the machinery is off, and the gate is the statement of that.

The mark stays on the **registrations** router where it already is, and its gate
is deleted rather than moved. It is the one payment action that has to work with
the payment machinery switched off, which is why it was put there.

## Risks / Trade-offs

**The counter's meaning changes under existing readers** → All five are read and
updated in this change, and the model comment carries the new sentence. The
export's meaning changes with it: `amount_paid_cents` in a document produced
after this may include money no statement backs, which is why the document also
carries the payments that explain it.

**A tournament could hand-record everything and never import a statement** →
Not prevented, and arguably fine — but it produces a ledger that balances
against nothing. Accepted; the transaction list stays the statement ledger and
says so by holding only statement rows.

**Stale confirmation mails on a backfill** → Accepted (Decision 3). One row at a
time, and the organizer is looking at the row.

**Two writers to `PAID` on a collecting tournament, which
`add-manual-paid-marking` D2 forbade** → The forbidden thing was a *silent*
second writer that a statement could contradict unknowingly. Both writers here
leave a record naming a person, and the contradiction case has a queue
(Decision 6). Stated in the spec as an amendment to that requirement rather than
left as a quiet reversal.

**A waived registration switched to a paid one by a later statement** → The
statement flags rather than credits (Decision 6), and the organizer decides.
Removing the waiver first is the honest order; nothing enforces it.

## Migration Plan

Two additive migrations: the `manual_payments` table, and two nullable columns
on `registrations`. Both back-fill to nothing — every existing registration has
`settled_by_hand_at` null, and the marks made under the old endpoint on
payments-off tournaments have no stored timestamp to recover. They keep working:
they are `PAID` with empty counters, which is what they were, and the console
reads the column where it exists and the state where it does not.

Rolling back means dropping the table and the columns, after which
hand-recorded credits remain in `amount_paid_cents` with nothing explaining
them. Worth knowing before the first tournament uses it.

## Open Questions

- Should the recorded-payments panel show the tournament's hand-collected total
  alongside its bank-credited one? It is the first report anyone will ask for,
  and it is not in this change.
- A waived registration that later cancels: nothing to refund, and
  `refund_state` stays not-applicable. Believed right, unverified against a real
  case.
