## Context

Verified against the working tree, which carries the reservation-lifecycle and add-dual-currency-prices changes:

- `backend/app/matching.py` selects which stored total a transaction is compared against — `outstanding_cents` for the tournament's local currency, `outstanding_eur_cents` for EUR when the tournament prices in it — for **one** transaction, and flags anything outside tolerance. A shortfall is discarded — the matching currency's counter (`amount_paid_cents` or `amount_paid_eur_cents`) is credited only on the success path. No conversion occurs anywhere in the path (design add-dual-currency-prices Decision 4); a transaction in a currency the tournament does not price in is flagged `currency_not_accepted` and compared against nothing.
- `VS_IN_MESSAGE = re.compile(r"\bVS[:\s]*(\d{1,10})\b", re.IGNORECASE)` and `effective_vs` reads `transaction.vs` then `transaction.message`, nothing else.
- `bank.py` maps eight Fio columns (`_FIO_COLUMNS` / `_CSV_FIELDS`). Everything else in the statement is dropped at parse time, so the data needed to widen the search does not currently reach the database.
- `apply_payment_links` credits `registration.amount_paid_cents += credited` inside its per-registration loop, where `credited` is the whole transaction. Two linked registrations each receive the full amount.
- `scheduler.process_reminders` selects on `registered_at <= now - reminder_day`; `process_expiries` runs first in the tick. `schemas.py:252` validates `reminder_day` only as `gt=0`.
- Matching iterates `pending` transactions. A flagged transaction is not pending, so nothing revisits it.

Two project conventions constrain the design. Every manual mutation is a persistent, replayable, removable rule. And reruns are deterministic — state is a pure function of (source records, rule set, parameters), which is exactly what makes the re-evaluation decision below tractable.

## Goals / Non-Goals

**Goals:**

- Money already in the account marks the registration paid when it is sufficient, however many transfers it arrived in.
- A payer who follows the written instruction — "put your VS in the payment message" — matches, whether or not they type the letters `VS`.
- A club transfer for six members resolves without hand-building six links.
- No registration is ever credited money it did not receive.
- Nothing the organizer explicitly decided is undone by an automatic pass.

**Non-Goals:**

- Matching by payer name or amount alone. The VS remains the sole identity; everything here is about finding it or summing against it.
- Automatic refunds of overpayments. Still manual, via the existing refund tracking.
- Changing reservation expiry behaviour (Decision 3).
- Deduplicating statements across tournaments, or the deployment-wide reconciliation sweep left open by the structured-VS change.

## Decisions

### Decision 1 — Credit first, decide state second, within the transaction's own currency lane

The comparison inverts. Today: compare one transaction to the amount due, and credit only on success. Instead:

1. Resolve the VS and the currency lane the transaction belongs to — the tournament's local total or its EUR total, exactly as add-dual-currency-prices established. No conversion occurs; a currency the tournament does not price in is not a lane at all.
2. Credit that lane's counter (`registration.amount_paid_cents += paid_cents` for the local lane, `amount_paid_eur_cents += paid_cents` for the EUR lane) unconditionally for any VS-matched transaction, and record the transaction as accounted for.
3. Then evaluate that same lane's outstanding (`outstanding_cents` or `outstanding_eur_cents`) against the tolerance: at or within it, the registration becomes `PAID`; still positive beyond tolerance, the registration stays `RESERVED` with a recorded partial balance in that currency; negative beyond tolerance, it is an overpayment in that currency and routes to `refund_state` as the reservation-lifecycle change already specifies.

The two lanes are independent throughout — a CZK aggregate and a EUR aggregate are never summed (add-dual-currency-prices Decision 5), so a registration part-paid in each currency is flagged in both rather than read as settled. Aggregation within one lane needs no special case: the second half-payment in that currency is just another credit against a smaller outstanding in the same lane. The per-currency counters are doing exactly the job they were chosen for.

The transaction status gains `partial` alongside `matched` and `flagged`: accounted for, credited, not by itself sufficient. A `partial` transaction is not in the manual queue, because there is nothing for the organizer to do.

*What still flags:* a currency the tournament does not price in (`currency_not_accepted`), a VS that resolves to nothing, and an overpayment beyond tolerance. Those are unchanged.

### Decision 2 — Re-evaluate flagged, never re-evaluate resolved

Each matching pass processes pending transactions **and** re-examines transactions still in `flagged`. Transactions in a terminal, organizer-decided state — `matched`, manually linked, marked for refund, or set aside as another tournament's — are never reconsidered.

*Why it is required:* two half-payments almost always arrive in different statements. Without re-evaluation the first is flagged before the second exists, and aggregation would only ever work inside a single import, which is the rare case. The finding would be nominally fixed and practically useless.

*Why not full replay* (the most literal reading of the determinism convention): replaying resolved rows means a manual link or a refund decision can flip back, and every confirmation email needs an idempotency guard to avoid re-sending. The convention is about *rule* replay — a rule set applied to source records — and organizer decisions are rules. Re-running the automatic pass over rows nobody has decided on satisfies it; re-running it over decisions does not, it overrides them.

*Consequence, accepted:* a flagged row can become matched without the organizer touching it. That is the point, but it means the flagged queue is not stable between passes. The console states when each transaction was last evaluated so a row vanishing from the queue is explicable.

### Decision 3 — A partial payment does not touch the expiry, and expiring with money held is announced

Per the owner: the validity window is unchanged by a partial payment. A reservation that reaches its expiry holding a partial payment expires like any other.

This is the consistent choice — the alternative renews a hold on a fraction of the fee — but it creates a state that must not be silent: an `EXPIRED` registration with `amount_paid_cents > 0`, money in the organizer's account, and a fencer who has paid something. So expiry checks for it:

- A distinct `expired_holding_payment` audit event, separate from ordinary expiry.
- The registration is marked for organizer attention, and the console lists these separately from ordinary expiries — this is a queue of real money needing a decision, not a housekeeping log.
- The expiry email says the partial payment is held by the organizer, who will be in contact. It does not imply the money is lost, and it does not promise a seat.

The reservation-lifecycle change already handles the *next* payment: a remaining balance arriving within the grace period reinstates and, with the aggregate now sufficient, pays. The two changes compose without either knowing about the other, because both go through `amount_paid_cents`.

### Decision 4 — Widen the fields at ingestion, and be selective about which

The data must reach the database before matching can search it, so `bank.py` and `BankTransaction` gain the text-bearing Fio fields that carry SEPA references:

| Field | Fio JSON | Fio CSV | Why |
|---|---|---|---|
| `user_identification` | `column7` | Uživatelská identifikace | Where several banks land the originator's reference |
| `comment` | `column25` | Komentář | Free text, commonly the payer's own note |
| `specification` | `column18` | Upřesnění | Carries SEPA remittance detail on some routings |
| `specific_symbol` | `column6` | SS | A Czech payer who puts the VS in the wrong symbol field |

Deliberately **not** searched: `payer_name` and `payer_account`. Both are structured identifiers, an account number is a long digit string, and scanning them for bare numeric tokens is a false-positive generator with no upside — a payer does not put their VS in their own account number.

*Which columns actually carry SEPA references varies by originating bank,* and this cannot be settled from the repository. The four above are the standard Fio placements; implementation should confirm against a real statement from the tournament's own account before the first live use, and the field list is deliberately a single mapping so adding a fifth is a one-line change.

### Decision 5 — Bare tokens match automatically, guarded by the amount

The VS scan runs in two tiers over the concatenated searchable fields:

1. **Labelled** — a `VS`-prefixed token, as today, widened to all searchable fields. Matches on the number alone; the amount is then evaluated by Decision 1 exactly as for a VS-field transaction, including partial crediting.
2. **Bare** — any 7-digit token resolving to an issued VS. Auto-matches **only when the transaction also covers that registration's outstanding within tolerance**. Otherwise it becomes a pre-filled candidate for the organizer, not an automatic match and not a credit.

*Why the asymmetry:* a labelled token is an assertion of intent — the payer wrote `VS`. A bare number is an inference, and inferring from a number alone is what lets an invoice reference attach itself to a stranger's registration. Requiring the amount to agree keeps the automation the owner asked for (a payer who follows the instruction pays the right amount and matches) while making a coincidence need two independent agreements instead of one.

*Why this is safe now and would not have been before:* the structured-VS change makes a VS a 7-digit value beginning `26`/`27`. Restricting bare-token candidates to exactly 7 digits already excludes most dates, order numbers, and amounts.

*Interaction with partial payments:* a bare token cannot credit a partial payment, because a partial payment by definition does not cover the outstanding balance. A genuine bare-token installment therefore surfaces as a candidate. Accepted — the alternative is letting an unlabelled number credit money on no other evidence.

### Decision 6 — Multi-VS transfers become auto-created rules, not a special matching path

When the scan yields several distinct issued VS in one transaction:

- Sum those registrations' outstanding balances **in the transaction's own currency lane** — local or EUR, whichever the transaction is denominated in; a registration with nothing outstanding in that lane contributes zero, not a conversion of its other lane. Within tolerance of the transaction, create a `payment_link` rule with those VS — the same kind the manual endpoint creates — and let `apply_payment_links` do the work.
- Outside tolerance, leave the transaction unmatched with the detected VS attached as a candidate, so the manual dialog opens pre-filled.

*Why route it through the rules engine rather than pay the registrations directly:* the project convention is that mutations are removable rules, and the finding explicitly requires the auto-created link to be revertible like a manual one. Reusing `payment_link` means `unapply_payment_link` reverts it with no new code and no second revert path to keep correct. The rule records that it was created automatically, so the console can distinguish it and the organizer can see why six registrations were paid at once.

*No partial subset matching.* If the sum of six VS does not match, the system does not search for a subset of five that does. That is a combinatorial guess about intent, and presenting six pre-filled candidates the organizer adjusts is both simpler and more honest.

### Decision 7 — A link distributes its amount; it does not multiply it

`apply_payment_links` credits each registration **its own outstanding balance in the transaction's own currency lane**, in VS order, capped by what remains of the transaction. `unapply_payment_link` subtracts exactly what was credited, from the currency lane it credited.

The current code credits the full transaction to every registration in the loop, so a 3500 transfer covering two 1750 registrations records 3500 against each — both paid, both apparently overpaid by 1750, both eligible for a refund nobody owes. It is a one-line defect in uncommitted work, but it is precisely the kind that reaches production through a change whose stated subject is something else, so it is fixed here with a test that pins the arithmetic.

To make the revert exact, the rule payload records the amount credited per VS at apply time rather than recomputing it — outstanding balances move, and a revert must undo what happened, not what would happen now.

### Decision 8 — Reminder day validated on write

`reminder_day < reservation_validity_days` is enforced in the tournament update schema, rejecting the combination with a message naming both values. Existing tournaments are not migrated: the validation fires on the next edit, and the pre-change defaults (5 and 10) are already valid. A deployment holding a bad combination today would have been silently sending no reminders, which the validation surfaces the moment anyone touches the tournament.

## Risks / Trade-offs

**A flagged transaction changing status without organizer action.** → Only rows nobody has decided on are revisited (Decision 2), and the console shows when each was last evaluated. Organizer-resolved states are terminal.

**Bare-token matching attaches a coincidental reference.** → Two independent agreements required: a 7-digit token that resolves to an issued VS *and* an amount covering that registration's outstanding within tolerance. Failing either, it is a candidate, not a match.

**Unconditional crediting means a wrong VS credits the wrong registration.** → Same exposure as today's matching, which also acts on VS alone; the difference is that the credit is now visible on the registration rather than only in the transaction's status. `unapply` and the organizer actions from the reservation-lifecycle change are the correction path.

**A reservation expires holding money.** → Deliberate, per Decision 3, and made loud rather than silent: distinct audit event, separate console queue, honest email.

**Widened parsing depends on Fio column placements not verified against a live statement.** → The field list is a single mapping, and implementation confirms against a real statement before first live use (Decision 4). A wrong column costs a missed match, never a wrong one.

**Three changes modify `Amount tolerance`.** → This change's block is written on top of the reservation-lifecycle and add-dual-currency-prices post-state and must archive after both. Archiving out of order would drop the amount-due wording or the per-currency, no-conversion wording either depends on.

## Migration Plan

1. One additive Alembic revision adding the four text columns to `bank_transactions`, all nullable. Historical transactions keep `NULL`, which the scan treats as absent — no historical transaction changes status as a result of this migration.
2. No backfill is possible or attempted: the discarded Fio columns were never stored, and re-fetching historical statements is out of scope.
3. No registration, VS, or payment record is rewritten.
4. Deploy after the reservation-lifecycle, structured-VS, and add-dual-currency-prices changes — the last of which this change's per-currency crediting is built on. The first matching pass after deploy will re-evaluate existing flagged transactions — expect some to resolve, which is the intended effect, and review the audit trail once rather than treating it as noise.
5. Rollback drops the four columns. Credits already applied to `amount_paid_cents` are not reverted by a rollback and would need the organizer's unapply path, so verify on a copy of `backend/hema_squire.sqlite` before deploying.

## Open Questions

- **Which Fio columns actually carry SEPA references** for the banks this tournament's payers use. Decision 4 lists the standard placements; confirm against a real statement and extend the mapping if a fifth appears.
- **Whether `partial` belongs in the organizer's view at all.** The design keeps partial transactions out of the manual queue because there is nothing to do, but an organizer may want a "money in, seat unconfirmed" list. Cheap to add once someone runs a real tournament with it.
- **Bare-token installments are unreachable** (Decision 5): an unlabelled partial payment can only ever be a candidate. If foreign installments turn out to be common, the guard needs revisiting — with real data, not in advance.
