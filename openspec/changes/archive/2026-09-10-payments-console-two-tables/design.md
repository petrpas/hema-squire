## Context

The Payments phase draws seven views behind one tab strip (`Console.tsx:882`,
`payments/QueueTabs.tsx`). Each was added to answer a question that really was
unanswered, and each is a filter over one of two underlying facts:

- **What arrived** — `bank_transactions`, plus `manual_payments` for money a
  person recorded.
- **What was credited** — `payment_credits`, one row per amount per
  registration, carrying `source_kind`/`source_id`, `origin` (`auto_vs`,
  `payment_link`, `recorded`, `reinstate`, `refund_hold`) and `rule_id`.

The journal already joins payment to fencer to reason, which is why *Připsané
transakce* and *Přiřazení plateb* list overlapping rows: one is grouped by
transaction, the other by the rule that decided it, and neither sees a credit
the other's key does not exist for.

Three things are broken rather than merely redundant:

1. `apply_payment_links` (`matching.py:749`) sets `transaction.status =
   "matched"` even when it credits nothing — the loop skips a registration that
   is not payable, or whose `due` is zero. `/payments/unmatched` filters on
   `status in ("unmatched", "flagged")`, so such a payment is in no work queue
   while showing as a completed pairing.
2. `parse_fio_json` and `parse_fio_csv` (`bank.py:124`, `bank.py:184`) ingest a
   debit as a negative transaction. Only the interpreted path drops one
   (`statements.py:155`), citing a decision the exact paths were never held to,
   and `payments-intake` states the rule for a foreign bank's CSV only.
3. Because of 2, `matching.py:583` can credit a negative amount: `paid_cents =
   transaction.amount_cents` with no sign check, and the tolerance test that
   would have caught it runs only for a *bare* token (`is_bare`). A refund sent
   by copying the original payment carries the registration's own VS, so it
   deducts from that registration.

The owner settled the shape in conversation: two tables, membership decided by
the journal, whole-payment undo, and one line of prose beside the tab band.

## Goals / Non-Goals

**Goals:**

- Two tables where there were seven, over the same rows, with nothing an
  organizer could see before becoming invisible.
- Membership answered by the credit journal, so a payment cannot be both
  resolved and uncredited.
- One gate on debits, holding for every intake path.
- The console's own tab idiom kept; no new kind of control.

**Non-Goals:**

- Cleaning up negative transactions already stored. The test environment is
  wiped and re-imported (`scripts/wipe_payments.py`).
- Relaxing `payments-clearing`'s refusal to clear while a transaction holds a
  live credit. It stays exactly as it is.
- Per-credit reversal. Undo is whole-payment (owner decision 3a).
- Any schema change. Both tables are queries over rows that exist.

## Decisions

### D1 — Membership from the journal, disposition from status

A payment is **credited** if a live `PaymentCredit` names it as its source, and
**uncredited** otherwise. That is the whole of the membership test, and it is
the one question `status` cannot answer, because `status` records what the
matcher decided rather than what the money did.

`status` is still read — for the *reason* a row is uncredited, which is exactly
what it is good for (`likely` with `proposed_fencer`, `flagged` with
`status_reason`, `unmatched` with nothing). So: **membership derived, reason
reported.** A `partial` transaction holds a credit and therefore belongs to the
credited table, which is correct — part of the money did land.

Alternative considered: keep filtering by status and fix
`apply_payment_links` to leave the transaction `unmatched` when it credits
nothing. Rejected because it fixes one instance of the class. Any future path
that resolves a transaction without crediting it reintroduces the hole, whereas
the journal-derived test cannot answer this one wrongly.

**One qualification, found while implementing.** "Holds no credit" is necessary
but not sufficient. A payment carrying a *sibling* tournament's symbol, on a
bank account several tournaments share, is stored with status
`other_tournament` (`matching.py:513`), holds no credit here, and never will —
its own console resolves it, which the phase already says in as many words
(`payments.setAside`). The journal cannot know that, because the fact is about
which tournament the symbol belongs to rather than about money. So the table is
"lies on nobody **and is this tournament's to resolve**", and the second half is
one status test. Worth stating plainly: the claim that a journal-derived
membership test cannot be wrong was too strong.

### D2 — Two endpoints replace five

- `GET /payments/uncredited` — transactions with no live credit, each carrying a
  `disposition`: `proposal` (with the fencer and what they owe), `refused` (with
  the reason and, where the flagged path already computes it, the hand-settled
  cause), `paired_uncredited` (with the registrations the rule names), or
  `none`. Replaces `/likely` and `/unmatched`.
- `GET /payments/credited` — widened from bank transactions to **every source
  holding a live credit**, grouped by `(source_kind, source_id)`: date, source,
  payer or recorder, amount, currency, and the credits it made with each
  fencer's own amount and the `origin` behind them. Replaces `/credited`,
  `/links` and `/manual`.

`/expired-holding` stays as an endpoint — it computes a figure honestly and
cheaply — but stops being drawn as a queue. `/transactions/{id}/reversal` and
`/reverse` are unchanged, which is what makes 3a cheap: no new API.

The uncredited query is a `NOT EXISTS` against live credits rather than a
Python-side filter, so the count the tab shows and the rows the table lists come
from one statement.

### D3 — The console owns the two fetches; the tabs stop registering themselves

`QueueTabs` exists because seven independent panels each had to announce its own
title and count to a strip that could not know them, with `register` /
`unregister` effects and a comment explaining why withdrawal is a separate
effect. With two fixed tables that indirection has nothing left to do.

The console holds two independent loads and passes rows and counts down; each
table renders what it is given. Independent failure is kept by keeping the two
loads independent, not by giving each panel its own lifecycle. `QueueCard`,
`QueueTabs`'s registration context, and `useSheetVisible`'s dependence on it all
go; the band component becomes a dumb pair of `stage-control` strips plus the
note.

Alternative considered: keep the registry and let the two tables register as the
seven did. Rejected — it preserves a mechanism whose only justification was the
number of panels.

### D4 — The note is computed by the console, not by the table

The line beside the band belongs to the open table but is not the table's to
draw: it sits outside the table's own box, beside the tabs. So the console
computes it from the active tab and the data it already holds — proposal count
for uncredited, credited total for credited, nothing for the fencer table — and
hands it to the band as a string. One rule about where it may live, no table
reaching outside itself.

Wording carries the containment: *"z toho 3 návrhy párování"* rather than *"3
návrhy párování"*, so a subset never reads as a rival count. Absent, not zero,
when there is nothing to say.

### D5 — One gate in `bank.ingest`, and the matcher still refuses a non-positive amount

The drop moves to `bank.ingest`, which every path passes through, and comes out
of `statements.py`. `IngestResult` gains `dropped`, and `duplicate` becomes
`len(transactions) - new - dropped`; without that a dropped debit is reported as
a duplicate, which tells the organizer their statement had been imported before.

The matcher **also** refuses a non-positive amount, rather than merely
documenting that it may assume a positive one. The gate is the guarantee and
this is one branch; the failure it guards is a silent negative credit against a
real person's balance, and a guard whose cost is a comparison is cheaper than
the class of bug it excludes. The two are not redundant in the way that matters:
the gate keeps the row out of the database, the guard keeps the money out of the
journal if a row ever arrives another way.

Alternative considered: guard only in the matcher and let debits be stored.
Rejected — a stored debit is a row in the uncredited table forever, with no
action that can resolve it.

## Risks / Trade-offs

- **One table mixing proposals, refusals and unreadable payments reads as a
  jumble** → the disposition column is the table's primary sort, so the rows
  needing the same decision sit together, and the note states how many are
  proposals. This is the redundancy the owner objected to being traded for one
  scan instead of three tabs.
- **A payment crediting many registrations makes a wide cell** → the fencers are
  named in one cell with their own amounts; beyond a handful the cell states the
  count and expands. Grouping by payment is what keeps date and payer from
  repeating down the rows.
- **Money stranded on an expired reservation loses its queue** → it remains
  derivable on the fencer row (`state` expired with `outstanding <
  total_amount`), but finding those rows becomes a scan across the roster rather
  than a tab with a count. See Open Questions; this is the one place where
  absorbing a queue removes a signal rather than a duplicate.
- **Five endpoints go, and the test suite is the real cost** → the only callers
  are `frontend/src/api.ts` and the backend suite, but sixteen test files reach
  those paths (`test_matching.py` alone ten times) plus `contract_seed.py`. Most
  assert on a queue's *contents*, which the two tables still express, so the
  work is rewriting assertions rather than rethinking them — but it is the bulk
  of this change's diff and should not be discovered halfway.
- **The spec was already behind the code** — `payments-console` still describes
  six views "stacked above the fencer table" though the tab strip shipped. The
  delta restates that requirement, so this change also brings the spec level
  with reality; a reader comparing the archive will see two moves in one.

## Migration Plan

No data migration and no schema change. Deploy is the code; rollback is a
revert, since nothing is written that the previous version cannot read.

The one ordering constraint is operational rather than technical: the owner runs
`scripts/wipe_payments.py` against the test environment and re-imports, so the
new tables are first read against data ingested through the new gate.

## Open Questions

1. **Does the fencer tab need a line after all?** The delta spec currently says
   the fencer table carries no line beside the band, because
   `console.footerStats` already states its totals. But absorbing *Vypršelé s
   platbou* leaves money-on-an-expired-reservation with no count anywhere. A
   line reading "2 vypršelé rezervace drží peníze" would restore it for one
   sentence's cost, and would mean changing that one sentence in the spec. The
   alternative is accepting the scan, or a filter — which D4 deliberately
   refused for proposals.
2. **Does the credited table need the payment's own message?** The uncredited
   table needs it to judge who sent the money. Once credited, the message has
   done its work, and leaving it out is what makes room for the fencers and
   their amounts. Confirm before building the columns.
