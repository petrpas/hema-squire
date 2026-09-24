## 0. Precondition

- [x] 0.1 Confirm `queue-rosters` is archived (this change's `etl-console` delta is written over its phase-order text)

## 1. Dormancy and silence

- [x] 1.1 `setup.DORMANT_ENTERED_BY_HAND`; `dormancy_cause` returns it for `clocks_dormant` without `source_row_id`
- [x] 1.2 `send_promoted` (both branches) and the confirmation path consult `_payment_mail_suppressed`; the surcharge's `despite_dormancy` applies only to registrations with a `source_row_id`
- [x] 1.3 Tests: every fencer mail path sends nothing for a hand-entered registration; an issued registration's surcharge notice still goes

## 2. Hand entry becomes a registration on an automatic tournament

- [x] 2.1 Extract (or reuse) the per-discipline placement in-app submission uses, including the settled-seating branch
- [x] 2.2 `handentry.register`: fencer record per the address rule, refusal `already_registered` naming the registration, `Registration` with VS, totals, `clocks_dormant=True`, no window, entries placed per 2.1
- [x] 2.3 `create_manual_row` branches on the mode; response shape carries a row id or a registration id; `schemas.py`
- [x] 2.4 Tests: seated with room; mixed full/open placed per discipline; all queued after settlement; not demoted at settlement; promoted without window or mail; bank payment credited without receipt; address already registered refused; manual tournament still writes a source row

## 3. Import is manual-only

- [x] 3.1 `import_table` refuses an automatic tournament with `import_needs_manual_mode` before reading the file
- [x] 3.2 `offeredPhases` drops `import` on an automatic tournament
- [x] 3.3 Tests: upload refused and nothing stored; Import phase absent and its URL lands on the default phase

## 4. Frontend dialog

- [x] 4.1 The manual entry dialog on an automatic tournament states that it creates a registration at the tournament's price, placed by capacity, and mails nothing; accepts the new response
- [x] 4.2 Refusal texts for `already_registered` and `import_needs_manual_mode` (cs, en)

## 5. Verify deduplication

- [x] 5.1 Check how deduplication resolves a pair of two registrations; if it cannot, record a follow-up rather than extend this change

## 6. Checks

- [x] 6.1 Backend: `uv run ruff check .`, `uv run basedpyright`, scoped `pytest`
- [x] 6.2 Frontend: `npm run typecheck`, `npm run check`, `npm test`
