## Why

On a tournament Squire collects for, money has exactly one way in. A credited
bank transaction is the only thing that reaches `PAID` (`matching.py:495`,
`routers/payments.py:633`), and `amount_paid_cents` means, strictly, what a
statement told Squire had arrived. Everything downstream leans on that: the
outstanding column, the deposit threshold (`matching.py:228`), the
expired-holding-money queue (`scheduler.py:168`), the export.

Two ordinary things at a real tournament fall straight through it.

Someone pays in a way the feed does not reach — cash at the desk, a transfer to
the club's other account, a card terminal, a euro note. The money exists, the
organizer holds it, and Squire has no way to be told. The registration stays
reserved and eventually expires for non-payment.

And someone owes nothing: a guest instructor, a sponsor's entrant, a
volunteer's free place. The organizer needs them to read as settled — they
belong on the list, they will not be chased, they must not expire — while not
adding a haléř to any figure that answers *how much money came in*.

The hand tick added in `add-manual-paid-marking` serves neither, because it is
refused wherever Squire collects, on the reasoning that a second writer to
`PAID` could be contradicted by the next statement with neither knowing. That
reasoning was right about *silent* writers. Both of these are loud: one names
an amount and a person who says it arrived, the other names a person who says
nothing is owed.

## What Changes

- **An organizer may record a payment Squire never saw**, on a tournament whose
  payments Squire handles: an amount in one of the tournament's currencies, the
  date it arrived, how it arrived, and a note. It is credited exactly as a bank
  transaction is credited — the same counter, the same settle test, the same
  deposit threshold, the same confirmation mail — so partial payments,
  deposits, windows and the outstanding column all behave as they already do.
- **Every credit records where it came from**, a statement or a person, so that
  a reader who needs *what arrived in the account* can still have it and is not
  quietly handed *what was collected altogether* instead. Recorded on the
  payment, not on the registration: a registration may hold both kinds.
- **A recorded payment is removable**, and reverses exactly the amount it
  credited — not what the balance would suggest today, which is the mistake the
  payment-link rules were built to avoid (`payments`, Manual matching).
- **The hand tick becomes one action offered everywhere**: settled with no money
  through Squire. Where Squire collects, it is the waiver — the free place, the
  comped entrant — and it SHALL state a reason, because a paid row holding zero
  next to a live ledger is otherwise a puzzle. Where Squire collects nothing it
  is what it is today, the organizer's word that they were paid, and the reason
  stays optional. **BREAKING** for `payments`: the mark is no longer refused
  where Squire handles the payments.
- **A registration has one outstanding balance, not one per currency.** The
  local and EUR totals are two prices for one place; crediting either settles
  the registration, and the other lane's untouched total is then not a debt.
  Printed side by side the second read as a conversion of the first, so every
  fully paid fencer on a two-currency tournament was shown a demand — on the
  console's column, on their own registration page, and in the test that
  decides whether an amended registration is sent a surcharge mail. One figure
  now, in the lane the money arrived in, and zero wherever the registration is
  settled: what the tolerance forgave is not owed. **BREAKING** on the wire —
  `outstanding_eur_amount` is gone from the sheet row and from the
  registration, replaced by `outstanding_currency` beside the one amount.
- **A waived registration owes nothing and holds nothing.** Both counters stay
  at zero, and the outstanding column reads as waived rather than as a debt, so
  no total of received money moves and no reader takes the row for an error.
- **The mark is stored, not inferred.** A registration carries when it was
  settled by hand and why, rather than the surfaces deducing it from a paid
  state with empty counters — which stops being a sound deduction the moment a
  waived registration can also hold a recorded payment.
- **A statement arriving afterwards is not silently doubled.** The matcher
  already flags a transaction landing on a registration that is no longer
  reserved (`matching.py:449`) and credits nothing, so the collision surfaces in
  the flagged queue where the organizer decides which money it is. Where the
  hand-recorded payment was partial, the bank row credits normally and an
  overpayment flags itself. Both paths exist; this change adds the reasons to
  the queue's reading rather than new machinery.

Not in scope: recording payments on a tournament whose payments Squire does not
handle. There Squire tracks no amounts at all, and a tournament that needs them
tracked wants Squire handling its payments — the line `add-manual-paid-marking`
drew, and this change keeps.

Not in scope either: refunds of hand-recorded money, cash-drawer totals, or any
report of takings. Removing a recorded payment reverses the credit; what the
organizer does with the cash is theirs.

## Capabilities

### Modified Capabilities
- `payments`: gains the rule that a registration has one outstanding balance,
  in the lane its money arrived in, reading zero wherever it is settled; gains
  what an organizer may record by hand where Squire collects —
  an amount with a stated origin, credited and reversible; and rewrites **An
  organizer may mark a registration settled by hand** so that the mark is
  offered on every tournament, carries a reason, is stored on the registration,
  and means *settled with nothing through Squire* rather than *Squire collects
  nothing here*.
- `payments-console`: the Payments phase gains the action that records a payment
  and the list of payments recorded by hand, alongside the four queues; the
  settled mark appears in the full phase, not only the boned-out one; and the
  flagged queue states the two collision reasons in words an organizer can act
  on.
- `etl-console`: the Payments phase's columns — the settled mark is no longer
  the boned-out phase's alone, the outstanding column reads *waived* on a
  waived registration rather than a balance nobody owes, and it states one
  balance in one currency instead of a figure per currency lane.
- `data-export`: the canonical document carries hand-recorded payments and the
  settled-by-hand mark with its reason, so a restore reconstructs a payment
  state that no transaction can explain.

## Impact

**Backend** (`backend/app/`): a `ManualPayment` table — a sibling of
`BankTransaction`, not a row inside it: a record in the statement ledger that no
bank ever sent would be a lie told to every reader of that table for the
convenience of one writer. Endpoints on the payments router to record, list and
remove; `matching`'s settle path factored so the credit, the state, the deposit
threshold and the confirmation mail are reached from both routes rather than
copied into the second. `Registration` gains `settled_by_hand_at` and
`settled_by_hand_reason`; the existing mark endpoint in `routers/registrations.py`
writes them and loses `_require_squire_collects_nothing`. `sheet.py` carries the
mark and the waived reading; `export_json.py` carries both new shapes and its
version rises.

**Frontend** (`frontend/src/`): a panel under `frontend/src/payments/` for the
recorded payments and the dialog that records one, in the same idiom as
`LinkDialog`; `SettledCell` gains the reason where one is required; the Payments
phase's column list gains the mark. `PHASE_COLUMNS.payments` and
`BONED_PAYMENTS_COLUMNS` converge on the mark and stay separate everywhere else.

**The invariant this change moves.** `amount_paid_cents` has meant *money Squire
saw in a statement* since it was written, and it will now mean *money credited,
by a statement or by a person who said so*. That is the whole cost of the
change, paid deliberately: the alternative — a second counter — leaves every one
of its five readers to remember to sum two fields, and the one that forgets is a
reservation that expires holding money.

**Verification**: `pytest` over crediting, partial credit, the deposit
threshold, removal reversing exactly what was credited, the waiver's counters,
the reason's requirement on each kind of tournament, both collision paths, and
the export round-trip. `vitest` over the dialog, the panel, the mark in the full
phase, and the waived reading of the outstanding column. And the Payments phase
on screen, because a phase that now carries five panels and two new columns is a
layout claim.
