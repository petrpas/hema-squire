## Why

An organizer can undo a bad table import. They cannot undo a bad statement
import.

`DELETE /import` removes every uploaded batch, every row, every decision taken
about one, and `table-import` spends two requirements on it — what it removes,
that it is warned about, that a re-import afterwards "starts clean". The
payments side has no delete endpoint at all: the only ones in the codebase are
for imports, rules, logos, disciplines, extra items, team members and the
tournament itself. Money that arrived by a misreading stays.

This is not hypothetical. The pilot's first two statement imports were read with
the wrong delimiter, producing 43 transactions with truncated messages, missing
payer names and one amount silently shortened from `1214,03` to `1214`. Undoing
that took hand-written SQL against the live database, twice, because nothing in
the product could do it.

The half that is easy to miss is the cached interpretations. A statement's rows
are cached per row fingerprint under decision kind `statement_row`, so a
re-import of the same file reuses what was stored and never re-reads it. Removing
the transactions alone leaves those behind: the organizer clears, re-imports the
corrected file, and gets the same wrong answers with no indication why. On the
pilot that is 48 cached rows behind 43 transactions — the difference being the
five outgoing payments that were dropped as not-payments. Clearing has to remove
both or it does not clear anything.

## What Changes

- **A new clear for imported payments.** Removes the tournament's bank
  transactions and the cached statement interpretations behind them, so a
  re-import of a corrected file is read afresh.
- **It is refused where money has been credited**, stating how many transactions
  hold credit, and removes nothing in that case. A transaction credited to a
  registration is a payment the tournament has acted on; deleting it would leave
  a fencer marked paid with nothing behind the claim. This is the rule the
  codebase already applies twice — a tournament cannot be hard-deleted once
  registrations exist because "financial history is never deletable", and
  clearing an import is refused where an issued registration holds credit.
- **It is confirmed before it runs**, stating how many payments will be removed
  and that the removal cannot be undone — the same shape as the import clear's
  confirmation, and distinguishable from resolving a single transaction.
- **It clears what arrived by import, not what arrived by matching.** Payment
  links the organizer made are rules and go with the transactions they name;
  registrations, their totals and their states are untouched.
- **A new card on the Payments phase**, beside the intake card that uploads the
  statement in the first place — the undo lives next to the do.
- Czech and English strings for the action, its confirmation, its refusal and
  its report.

Not in scope: unwinding a credited payment. That is a financial reversal with
its own consequences — a registration returning to unpaid, a refund state, mail
already sent — and it belongs to whatever change takes on reversal properly.
This change refuses in that case and says so.

## Capabilities

### New Capabilities
- `payments-clearing`: how a tournament undoes an import of money — what is
  removed, that the cached interpretations go too so a re-import is read afresh,
  what is refused and why, what survives untouched, and how the organizer is
  asked before it happens.

## Impact

**Backend** (`backend/app/`): a module for the clear, modelled on
`importclear.py` — the same shape of "remove the data rather than mark it",
ordered by dependency in one transaction; `DELETE` and a count endpoint on the
payments router. No migration: this removes rows, it adds no columns.

**Frontend** (`frontend/src/payments/`): a card on the Payments phase beside
`IntakePanel`, with the count, the confirmation and the report; `api.ts`;
`i18n/{en,cs}.json`. It uses the console's existing queue-reload signal, so the
four resolution queues empty without the organizer reloading.

**Interaction with `issue-imported-registrations`**: that change already deletes
registrations issued for cleared rows and refuses on credit. This is its
counterpart on the money side, and the two refusals should read alike — an
organizer who has met one should recognise the other.

**Design constraints**: `CLAUDE.md` and `openspec/squire-design-spec.md` bind the
new card. The confirmation is static, per the prohibition on animated
confirmations, and follows the import clear's existing treatment.

**Risk**: this deletes money records. The guard is the credit refusal, which must
be tested as the thing that is *load-bearing* rather than as a status check —
a test asserting the endpoint returns 409 proves less than one asserting the
transactions and the registration's credited amount survived it.

**Verification**: `pytest` for the clear, the refusal, and — the property this
change exists for — that a re-import after a clear re-reads the file rather than
reusing a cached interpretation; `vitest` for the card; then the pilot, whose 43
uncredited transactions and 48 cached rows are exactly the case that needed hand
SQL.
