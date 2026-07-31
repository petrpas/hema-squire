## Context

Verified against `main` at the time of writing:

- `backend/app/routers/registrations.py:38` sets `VS_START = 1000001`; `next_vs` at `:60-62` returns `max(Registration.vs) + 1` over the whole table, with no tournament predicate.
- `backend/app/models.py:354` already declares `Registration.vs` as `unique=True`, so a race no longer produces two identical VS — it produces an `IntegrityError` and a 500, because nothing retries.
- `backend/app/matching.py` resolves a VS with `Registration.tournament_id == tournament.id AND Registration.vs == vs`, so a sibling tournament's VS falls through to `unmatched` / `unknown_vs`.
- `backend/app/bank.py:ingest` stores transactions keyed `(tournament_id, external_id)`, and each tournament carries its own `fio_token`. Two tournaments on one account each fetch and each store a full copy of the statement.
- `Tournament` has no VS-related column of any kind.

The domain constraint that shapes the format: the Czech VS is at most 10 digits, banks strip leading zeros, and the SPAYD `X-VS` field carries it as-is. A 7-digit all-numeric value beginning with a nonzero digit is safe on every one of those counts while `YY >= 26`.

## Goals / Non-Goals

**Goals:**

- A VS that identifies its tournament and registration on sight, on a bank statement, without a lookup.
- Payments stop landing in the wrong tournament's manual queue when one bank account serves several events.
- VS allocation is correct under concurrent registration, and fails loudly rather than silently when it runs out of room.
- Not one already-issued VS changes value.

**Non-Goals:**

- Deduplicating the ingested statement across tournaments. Each console keeps its own copy of the rows it fetched; provenance follows the fetch, not the money.
- Cross-tournament matching. A transaction ingested by tournament B never pays tournament A's registration (Decision 5); it is only recognized and set aside.
- Parsing VS out of additional transaction fields, bare-number tokens, or multi-VS transfers. That is the payment-matching-hardening change, which depends on this one.
- Retrofitting the structured format onto historical registrations.

## Decisions

### Decision 1 — `YYNNnnn`, with the prefix stored rather than recomputed

`Tournament` gains three columns:

- `vs_year: int` — the full four-digit year the series belongs to, taken from the tournament date at assignment time.
- `vs_series: int` — `NN`, 1..99, unique within `vs_year`.
- `vs_next_seq: int` — the next `nnn` to issue, starting at 1.

The issued value is `(vs_year % 100) * 100000 + vs_series * 1000 + seq`.

*Why store `vs_year` instead of deriving it from `Tournament.date` on every allocation:* the prefix must be stable. An organizer who moves a January event back into December must not cause the next registration to be issued under a different prefix than the previous one, splitting one tournament's registrations across two prefixes. Storing the year makes the prefix an assigned identity rather than a running function of a mutable field.

*Why the year comes from the tournament date, per the owner:* a January 2027 event belongs to the 2027 season even though it is created and sells out during 2026, and that is how the organizer and the payers will think about it.

### Decision 2 — Assignment at creation, freeze at first registration

The series is assigned when the tournament is created: the lowest integer in 1..99 not already taken for that `vs_year`. It stays editable in Setup — including implicitly, by changing the tournament date into a different year — until the tournament has its first registration. From that moment `vs_year` and `vs_series` are read-only, and a later date change does not renumber anything.

*Why the freeze:* the prefix appears in every payment instruction and QR code already sent. Changing it after issuance would produce a tournament whose registrations carry two different prefixes, and would make the prefix actively misleading — which is tolerable only because nothing routes on it, but is still worth avoiding.

*Consequence, accepted:* a tournament moved across a year boundary after its first registration keeps a prefix naming the old year. This is documentation drift, not a defect, precisely because of Decision 4.

### Decision 3 — Per-tournament atomic counter, unique constraint as backstop

Allocation is an atomic `UPDATE tournaments SET vs_next_seq = vs_next_seq + 1 WHERE id = :id RETURNING vs_next_seq`, which is race-safe on both SQLite (3.35+) and the PostgreSQL target without an explicit lock. The composed VS is then inserted, with `Registration.vs`'s existing unique constraint catching anything the counter somehow missed and a bounded retry (3 attempts) re-reading the counter before giving up.

*Alternative rejected — keep `max(vs) + 1`, scoped to the tournament's prefix range.* It is one query fewer and needs no new column, but it re-derives state that can be read directly, and its correctness under concurrency depends entirely on the retry rather than on the increment. The counter makes the common path correct and the retry a genuine backstop instead of the primary mechanism.

*Gaps are expected and fine.* A re-registration after expiry (CH-01) issues a fresh VS and burns a sequence number. The counter never reuses a number, because reuse would credit an old payment instruction against a new selection at a new price.

### Decision 4 — The prefix is documentation; lookup is global and by whole value

Matching resolves a registration as `SELECT ... WHERE Registration.vs == vs` with no tournament predicate, and takes the tournament from the resolved row. It never parses `YY` or `NN`.

This is the single most important rule in the change and it must be explicit in the spec, because parsing the prefix looks like an optimization and is a correctness trap: a payer who mistypes one digit of the series would have their money routed into a sibling event's reconciliation, where it would be compared against a stranger's amount due. Resolving the whole value means a mistyped digit either hits nothing (unmatched, which is correct and recoverable) or hits a real registration that genuinely owns that number.

The same rule is what makes legacy VS keep working with no compatibility shim: `1000042` is a plain index hit exactly like `2605003`.

### Decision 5 — A sibling tournament's transaction is parked, not matched

When the resolved registration belongs to a different tournament than the one being processed, the transaction is finished with a distinct status and reason, is excluded from the unmatched and flagged queues, and produces no payment, no state change, and no email. The owning tournament's own ingestion matches its own copy of the row.

*Why not match it there and then* (the alternative the owner considered and declined): the transaction row lives under tournament B, so B's organizer would trigger a payment confirmation for a fencer who is not in their event, and the audit `PaymentEvent` — which carries `tournament_id` from the transaction — would record A's registration's payment in B's trail. The reconciliation would be right and the provenance would be wrong.

*Why not reattribute the row to A:* `BankTransaction` is idempotent on `(tournament_id, external_id)`. Moving a row to A means A's own poll then ingests the same `external_id` as a new row, because the key it deduplicates against has just been vacated. Fixing that means reworking ingestion identity, which is a much larger change than this one.

*The residual risk this leaves* is a tournament that never polls: its payments sit parked in the sibling's records and nothing matches them. Mitigation is visibility rather than machinery — the ingest result reports the parked count, and the console shows it, so an organizer who sees "14 belonging to other tournaments" has a reason to ask whether the other tournament is polling. A deployment-wide reconciliation sweep is the real answer and is out of scope here.

### Decision 6 — Overflow refuses rather than degrades

`nnn` caps a tournament at 999 registrations and `NN` caps a year at 99 tournaments. Both are far outside the domain — the largest HEMA events run to a few hundred entries — but neither may fail quietly:

- Creating a 100th tournament in one year is refused with a message naming the exhausted year, rather than assigning a colliding or out-of-range series.
- Issuing a 1000th VS for one tournament is refused with a message naming the tournament, rather than composing an 8-digit value that would silently borrow a digit from the series field.

Wrapping or truncating either field produces a VS that resolves to the wrong registration, which is the one outcome this change exists to prevent.

### Decision 7 — Backfill assigns a series to every existing tournament and rewrites nothing

The migration walks existing tournaments in a deterministic order (`date`, then `id`), groups them by the year of their date, and assigns each the next free series in its year. `vs_next_seq` starts at 1 for every tournament regardless of how many registrations it already has, because existing registrations hold legacy VS from a different range and consume none of the structured sequence.

No `Registration.vs` is read, written, or considered by the migration.

## Risks / Trade-offs

**A payment for a non-polling tournament sits parked and invisible.** → The parked count is surfaced in the ingest result and the console. Accepted as the cost of not doing cross-tournament side effects (Decision 5); a deployment-wide sweep is the follow-up if it bites.

**A structured VS could collide with a legacy one.** → Legacy values start at `1000001` and increment; the structured range starts at `2600000`. Roughly 1.6 million registrations separate them. The unique constraint on `Registration.vs` is the backstop, and the bounded retry turns a collision into the next number rather than a 500.

**The frozen prefix can name the wrong year after a date change.** → Accepted and documented: nothing routes on the prefix (Decision 4), so a stale prefix is cosmetic. The alternative — renumbering — would invalidate QR codes already in inboxes.

**`next_vs` is also being edited by CH-01, which is mid-implementation.** → CH-01 touches it only to add a comment about re-registration; this change rewrites the body. Land them in either order and reconcile the comment, which survives the rewrite unchanged in meaning.

**Alembic on SQLite.** → Additive columns plus a data-only backfill; no table rebuild. The unique constraint on `(vs_year, vs_series)` is created after the backfill has populated both, so it cannot fire mid-migration.

## Migration Plan

1. One Alembic revision adding `vs_year`, `vs_series`, and `vs_next_seq` (default 1) to `tournaments`, all nullable at first.
2. Data step: for each tournament ordered by `(date, id)`, set `vs_year` from the year of its date and `vs_series` to the lowest free value in that year. A year holding more than 99 tournaments aborts the migration with a message rather than assigning a hundredth — this cannot occur in any real deployment, and silently proceeding would produce duplicate prefixes.
3. Add the unique constraint on `(vs_year, vs_series)` and make the three columns non-nullable.
4. Verify against a copy of `backend/hema_squire.sqlite`: every tournament has a series, no two tournaments share one within a year, and `SELECT vs FROM registrations` is byte-identical before and after.
5. Rollback drops the three columns and the constraint. Nothing else was written, so a rollback restores the previous behaviour exactly — including, deliberately, the sibling-tournament defect.

## Open Questions

- **Cross-deployment reconciliation.** Decision 5 leaves a payment unmatched when its owning tournament never polls. Whether to add a periodic deployment-wide matching sweep, and who would own it operationally, is unresolved and deliberately out of scope.
- **Series visibility to payers.** The Setup panel shows the organizer their prefix. Whether the fencer-facing payment instructions should explain the VS structure at all, or simply state the number, is a copy decision left to implementation — the number alone is sufficient for payment.
- **Ingestion deduplication across tournaments.** Two tournaments on one account store two copies of every transaction. This change makes the duplication visible (parked counts) without addressing it; reworking `BankTransaction` identity to be account-scoped rather than tournament-scoped is a candidate follow-up.
