## Why

The Payments phase presents the organizer's work as seven views behind a tab
strip, and the same fact appears on up to three of them at once. A transaction
an organizer linked by hand shows on *Přiřazení plateb* as a pairing, on
*Připsané transakce* as a credit, and — if the pairing credited nothing —
nowhere at all, while the money sits on the account and the console reads as
done. The views were built one decision at a time, each answering a real
question, and the result is seven tables an organizer has to hold in their head
to know whether a payment has landed.

Underneath, the database already answers this in two rows: `payment_credits`
says what has been credited, to whom, and why (`origin`), and `bank_transactions`
says what arrived. Every one of the seven views is one of those two questions
with a filter on it.

## What Changes

- The payments phase presents **two tables** instead of seven queues, behind two
  tab bands: `[Šermíři | Platby]` and, under Platby, `[Připsané n | Nepřipsané n]`.
- **Připsané** replaces *Připsané transakce*, *Přiřazení plateb* and *Ručně
  zadané platby*. One row is one payment — a bank transaction or a hand-recorded
  one — naming the fencers it credited in a single cell, with why it was credited.
- **Nepřipsané** replaces *Navržené shody*, *Nepřiřazené platby* and *Nevyřešené
  platby*, and is defined as **a transaction holding no live credit**, asked of
  the credit journal rather than of `BankTransaction.status`. One column carries
  what is to be done: the resolver's proposal, or the reason nothing was
  credited. **BREAKING** for the console's own reading of `status`, which stops
  deciding which table a transaction belongs to.
- A payment whose link credited nothing **stops reading as done**. Today
  `apply_payment_links` sets `status = "matched"` even when it credits nothing,
  so such a payment appears in no work queue; under the journal-derived
  definition it surfaces in Nepřipsané with its reason and leaves again by
  itself once a credit exists.
- *Vypršelé s platbou* ceases to be a queue and becomes a state the fencer table
  already carries — an expired registration holding credit.
- The **space beside the tab band** carries one line about the table being read:
  how many of the uncredited payments are proposals, or what has been credited
  in total. Not a second count, not a filter.
- The sheet heading over the payments phase reads **Správa plateb** rather than
  *Registrovaní šermíři*.
- **Money leaving the account is never ingested as a payment, on every path.**
  The requirement exists for a foreign bank's statement and is enforced only
  there; the two Fio fast paths ingest a debit as a negative transaction, which
  can never be credited and so sits in the console forever. The drop moves to
  `bank.ingest`, where all three paths meet.

Out of scope, deliberately: the negative transactions already stored. The test
environment is being wiped and re-imported (`scripts/wipe_payments.py`) rather
than swept, and `payments-clearing`'s refusal to clear while any transaction
holds a live credit stays exactly as it is.

## Capabilities

### New Capabilities

None. Both tables are the existing capability restated over the same data.

### Modified Capabilities

- `payments-console`: **Payment resolution views** becomes two journal-derived
  tables instead of six stacked views — which also brings the requirement level
  with the tab strip already shipped, that it still describes as a stack. The
  unmatched queue, the expired-holding list, the payment-links view and the
  recorded-payments list are absorbed into the two tables and cease to be
  requirements of their own; the line beside the tab band is new.
- `payments-intake`: the promise that a statement's **credits** are ingested is
  stated for every path — the Fio API poll and the Fio export upload as well as
  a statement no exact reader recognises — rather than for the last only.
- `name-assisted-matching`: proposals stop being a queue of their own and become
  a state of an uncredited payment; what confirming and rejecting do is
  unchanged.

## Impact

- **Backend**: `app/bank.py` (the ingest gate, and `IngestResult`'s arithmetic,
  which would otherwise count a dropped debit as a duplicate),
  `app/statements.py` (the drop moves out), `app/routers/payments.py` (the two
  endpoints the tables read, replacing five), `app/matching.py` (may now state
  that it assumes a positive amount — `matching.py:583` credits
  `transaction.amount_cents` with no sign check, so a refund carrying the
  original VS credits a negative amount today).
- **Frontend**: `Console.tsx`, `payments/QueueTabs.tsx` (two bands and the note),
  `SheetArea.tsx` (the conditional heading), the panels under
  `frontend/src/payments/` (seven collapse to two), `i18n/cs.json`.
- **No migration.** Nothing about the schema changes; both tables are queries
  over rows that already exist.
