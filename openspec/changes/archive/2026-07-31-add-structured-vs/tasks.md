## 1. Data model and migration

- [x] 1.1 Add `Tournament.vs_year: int`, `Tournament.vs_series: int`, and `Tournament.vs_next_seq: int` (default 1) to `backend/app/models.py`, with a comment stating that the prefix is documentation and nothing routes on it
- [x] 1.2 Add a `UniqueConstraint("vs_year", "vs_series")` to `Tournament.__table_args__`
- [x] 1.3 Add a `Tournament.vs_prefix` property returning `(vs_year % 100) * 100 + vs_series`, for display in Setup and for composing symbols
- [x] 1.4 Confirm `Registration.vs` already carries `unique=True` and needs no schema change; note in a comment that it is the backstop for the counter
- [x] 1.5 Write the Alembic revision: add the three columns nullable, backfill, then add the unique constraint and make them non-nullable
- [x] 1.6 In the backfill, walk tournaments ordered by `(date, id)`, group by the year of their date, and assign the lowest free series in each year; abort with a clear message if a year would need a hundredth
- [x] 1.7 Confirm the migration reads no `Registration` row and rewrites no `vs`; assert this by comparing `SELECT id, vs FROM registrations` before and after against a copy of `backend/hema_squire.sqlite`

## 2. VS allocation

- [x] 2.1 Replace `next_vs` in `backend/app/routers/registrations.py` with a per-tournament allocator taking the tournament, composing `(vs_year % 100) * 100000 + vs_series * 1000 + seq`
- [x] 2.2 Allocate `seq` with an atomic `UPDATE tournaments SET vs_next_seq = vs_next_seq + 1 ... RETURNING vs_next_seq` rather than a read-then-write
- [x] 2.3 Raise a distinct error when the returned sequence exceeds 999, refusing the registration rather than composing an overrunning value
- [x] 2.4 Wrap the insert in a bounded retry (3 attempts) that re-allocates on the unique-constraint violation of `Registration.vs`, so a race yields the next number instead of a 500
- [x] 2.5 Update the call sites in `register` — including the re-registration branch — to pass the tournament, and keep CH-01's comment about why a fresh VS is issued on re-registration
- [x] 2.6 Retire `VS_START`, or keep it only as a documented marker of where the legacy range began

## 3. Series assignment and Setup

- [x] 3.1 Assign `vs_year` from the tournament date and `vs_series` as the lowest free value for that year when a tournament is created in `backend/app/routers/tournaments.py`
- [x] 3.2 Refuse tournament creation with a message naming the year when all 99 series are taken for it
- [x] 3.3 On tournament update, reassign the series when the date moves into a different year **and** the tournament has no registrations; leave both fields untouched once a registration exists
- [x] 3.4 Reject an explicit series change that collides with another tournament in the same year, and reject any series change once a registration exists
- [x] 3.5 Expose `vs_series`, `vs_year`, and the derived prefix in the tournament schemas in `backend/app/schemas.py`, with a flag for whether the series is still editable
- [x] 3.6 Add the series field and the displayed prefix to `SetupPanel.tsx`, rendered read-only with an explanation once registrations exist

## 4. Global VS lookup

- [x] 4.1 In `backend/app/matching.py`, drop the `tournament_id` predicate from the VS resolution so the lookup is a whole-value hit on the global unique index
- [x] 4.2 Add the sibling-tournament branch immediately after resolution: when the resolved registration belongs to another tournament, finish the transaction with a distinct status and reason and take no other action
- [x] 4.3 Confirm the sibling branch sends no email, marks no registration paid, and writes no registration-affecting `PaymentEvent`
- [x] 4.4 Exclude the sibling status from the unmatched and flagged queues in `backend/app/routers/payments.py`
- [x] 4.5 Add a set-aside count to `MatchResult` and to the ingest-and-match response, distinct from matched, flagged, and unmatched
- [x] 4.6 Verify the tournament resolved from the registration governs tolerance, currency, and grace — never the tournament whose console is running the match
- [x] 4.7 Review `apply_payment_links` and the manual-link endpoint: a manual link SHALL still be restricted to the console's own tournament, since the organizer must not pay a stranger's registration by hand either

## 5. Frontend

- [x] 5.1 Show the set-aside count in `MatchPanel.tsx` after an import or poll, phrased so an organizer understands nothing is wrong and nothing is theirs to do
- [x] 5.2 Add cs and en i18n strings for the series field, the prefix display, the frozen-series explanation, and the set-aside count

## 6. Tests

- [x] 6.1 A newly issued VS has the structured form: the fifth tournament of 2026, third registration, yields 2605003
- [x] 6.2 Two tournaments in the same year each start their sequence at 001 and differ only in the series digits
- [x] 6.3 Series uniqueness holds within a year and the same series is reusable in a different year
- [x] 6.4 Series is taken from the tournament date year, not the creation year, for a tournament created in one year and held in the next
- [x] 6.5 Series is editable before the first registration and rejected after it; a colliding series is rejected in both cases
- [x] 6.6 A date change into another year after registrations exist leaves the prefix, every issued VS, and the sequence continuation unchanged
- [x] 6.7 Sequence overflow past 999 raises rather than issuing an overrunning value; a year holding 99 tournaments refuses the hundredth
- [x] 6.8 Concurrent registration produces two distinct VS and no failed registration
- [x] 6.9 A legacy sequential VS still resolves and matches unchanged
- [x] 6.10 A transaction carrying tournament A's VS, ingested while processing tournament B, is set aside — absent from B's unmatched queue, no registration paid, no email — and matches normally when A ingests its own copy
- [x] 6.11 A VS whose prefix names a real tournament but whose whole value matches no registration lands in the unmatched queue and selects no tournament from its prefix
- [x] 6.12 The migration assigns a series to every existing tournament and leaves `SELECT id, vs FROM registrations` byte-identical

## 7. Verification

- [x] 7.1 Run the full backend test suite and confirm nothing regressed, in particular the existing matching and registration tests
- [x] 7.2 Run `openspec validate add-structured-vs --strict`
- [x] 7.3 Exercise the two-tournament case in the running app: create two tournaments for one year on one bank account, register in each, import a statement covering both into each console, and confirm each matches only its own and reports the other as set aside
