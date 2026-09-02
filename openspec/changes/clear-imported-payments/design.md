## Context

The console can undo a table import and cannot undo a statement import. That
asymmetry is not a judgement about which is riskier — it is an accident of
order, since the table import came first and grew its clear when the pilot needed
one.

The pilot has now needed the other one. Two statement imports were read with the
wrong delimiter, producing 43 transactions whose messages were truncated at the
first comma, whose payer names were missing entirely, and one of which recorded
`1214` for a payment of `1214,03`. Undoing that meant `delete from
bank_transactions` written by hand against the live database, twice.

Two facts shape the design:

- **The interpretations outlive the transactions.** `statements.parse` stores each
  row's reading as an `ImportDecision` of kind `statement_row`, keyed by
  `importer.row_fingerprint(raw)`, so that re-importing a corrected statement
  interprets only what changed. The pilot holds 48 of these behind 43
  transactions — the five outgoing rows were interpreted and then dropped as not
  payments. A clear that removed only transactions would be invisible to the
  next import.
- **Some transactions are money the tournament has acted on.** A credited
  transaction moved a balance, set a state, and may have sent mail. There is no
  reversal machinery for that, and inventing one inside a clear would be the
  worst place to put it.

`importclear.py` is the model to follow throughout: same "delete the data rather
than mark it" stance, same one-transaction ordering by dependency, same shape of
report and confirmation.

## Goals / Non-Goals

**Goals:**

- A misread statement can be undone from the console.
- Re-importing after a clear genuinely re-reads the file.
- Money the tournament has acted on cannot be deleted by accident, or on purpose.
- The organizer knows the size of the action, and knows a refusal before trying.

**Non-Goals:**

- Unwinding a credited payment. Refused and explained instead.
- Clearing one statement rather than all of them. The table import made the same
  choice for the same reason: a partial clear leaves an older file's rows to
  become the tournament's payments again.
- Touching registrations, fencers, imported rows, or any payment configuration.
- An undo of the clear itself. It is a deletion, and says so.

## Decisions

### Decision 1 — Clear the interpretations, not only the transactions

The whole reason this is a change rather than a `DELETE` one-liner. Removing the
43 transactions and leaving the 48 stored readings would produce a clear that
appears to work and then silently defeats the next import — the exact failure the
pilot hit when only the transactions were removed by hand and the re-import
returned the same truncated names.

`table-import` already states this property for the other clear: "every row of
the new file is parsed afresh, with no decision or correction carried over from
the cleared content". This change owes the same promise.

The decisions are the mechanism and not the subject, so the report counts
transactions. An organizer should not have to know that an interpretation cache
exists in order to understand what they just did.

### Decision 2 — Refuse on credit, and refuse totally

Two questions: what to do about credited transactions, and whether to clear the
rest anyway.

Refuse, because there is no honest alternative. Deleting a credited transaction
leaves a registration claiming to be paid with nothing behind it; unwinding the
credit is a financial reversal that needs to consider the registration's state,
its refund state, and mail already sent, none of which belongs inside a clear.
The codebase has already answered this twice — `delete_tournament` refuses once
registrations exist, and `clear_imports` refuses where an issued registration
holds credit.

Refuse *totally* rather than clearing the uncredited remainder, because a partial
clear is the one outcome nobody can reason about: the console would report
success, the queues would empty, and the tournament would still hold money in a
state the organizer thought they had removed. All or nothing is what makes the
result describable in one sentence.

### Decision 3 — State the refusal before the organizer commits

The count endpoint reports both what would be removed and what stands in the way,
so the card can state "clearing is unavailable because four payments have been
credited" rather than offering a button that fails. A refusal is a fact about the
tournament, not an outcome of trying, and `IntakePanel` already sets this
precedent by explaining a missing Fio token rather than failing on click.

### Decision 4 — A separate action from clearing the fencer list

They are two clears on two subjects, and neither implies the other. An organizer
who imported the right roster and the wrong statement must be able to fix the
second without destroying the first — which was exactly the pilot's situation,
where the roster had been imported, matched and deduplicated over several
sessions and the statement was a day old.

The two do meet in one place: `issue-imported-registrations` deletes
registrations issued for cleared rows, and a transaction linked to one of those
returns to the unresolved queue rather than vanishing. That direction is already
decided there; this change does not revisit it.

### Decision 5 — The card lives beside the intake card

The undo belongs next to the do. `IntakePanel` is where a statement is uploaded,
the Fio poll is triggered and the lifecycle is run; the clear is the fourth thing
one can do to a tournament's money, and putting it anywhere else would leave an
organizer hunting for it at the moment they are least inclined to hunt.

## Risks / Trade-offs

**This deletes money records, and the guard is one predicate.** → The credit
refusal must be tested as load-bearing rather than as a status code: a test
asserting `409` proves less than one asserting that after the refusal the
transactions are still there, the registration's credited amount is unchanged,
and the stored interpretations survived. Both tests, with the second the one that
matters.

**A clear followed by a re-import costs a full re-interpretation.** For a
non-Fio statement that is a model call per batch, paid again. → Correct and
intended: the point of clearing is that the previous reading was wrong. Fio
exports re-read exactly and cost nothing.

**An organizer might clear expecting to undo one bad statement and lose three
good ones.** → The confirmation states the count, which is how they find out;
and the same trade-off was accepted for the table import for the same reason. A
per-statement clear invites a worse failure, where an older statement's rows
quietly become the tournament's payments again.

**The refusal could strand an organizer** whose tournament has one credited
transaction they cannot easily find. → The refusal states the count; the
credited transactions are matched, so they are the ones *not* in the resolution
queues, and unlinking is an existing action. Worth revisiting if it proves
awkward in practice.

## Migration Plan

None. This adds no columns and changes no stored shape; it removes rows.

There is nothing to roll back beyond removing the endpoints — a deployment that
reverts simply loses the ability to clear, and the tournaments that used it stay
as the clear left them.

## Open Questions

- Should the clear also remove the concluded `statement` operation records, so
  the console reports no import ever ran? Leaning no: an operation record is the
  history of what the console did, and the console did do it. But it does leave
  a "statement import: done, 48 rows" report standing over a tournament with no
  payments, which reads oddly.
- Should a Fio-polled transaction be clearable by the same action? It arrived by
  the bank rather than by a file, so "imported payments" is a slight misnomer for
  it — but leaving it behind would make the clear partial in a way Decision 2
  argues against. Current answer: clear everything, and name the action for the
  money rather than for how it arrived.
