## 0. Precondition

- [x] 0.1 Confirm `demotion-hardening`, `queue-rosters` and `participation-condition` are archived

## 1. Storage and setting

- [x] 1.1 `Tournament.queue_payment_seats` (default false), `Registration.claim_total` / `claim_total_eur`; Alembic revision
- [x] 1.2 Setup schema and endpoint accept the setting; offered only on automatic + payments on; retained when hidden
- [x] 1.3 `export_json` carries the setting and claims (next schema version)

## 2. Claim

- [x] 2.1 Claim computed with totals (every individual placement seated), null where not wholly queued, dormant, or setting off; lazy recompute on instructions read
- [x] 2.2 Tests: single and multi-discipline claims; forfeited deposit subtracts; dormant has none; teams excluded

## 3. Matching

- [x] 3.1 Queued branch per design D2: seat + credit + audit `queue_payment_seated`, or flag `queued_amount_mismatch` / `queued_no_place`
- [x] 3.2 Re-evaluation of `queued_no_place` in arrival order against free places as they change within the pass
- [x] 3.3 Setting turned off re-labels held `queued_no_place` to `registration_queued`
- [x] 3.4 Tests: seats with room; held when full then seated when a place frees; all-or-nothing for two disciplines; first payer wins a single place; wrong amount never self-seats; organizer's refund or promotion is not undone; setting off behaves as `demotion-hardening`

## 4. Fencer-facing

- [x] 4.1 Instructions endpoint returns claim instructions with the condition statement
- [x] 4.2 Confirmation of a registration queued at submission carries the claim block and QR
- [x] 4.3 Demotion notice carries the claim block instead of "do not pay"
- [x] 4.4 Payment-received-with-place mail; held notice wording per reason (backend catalogs cs, en)

## 5. Console

- [x] 5.1 Setup: the checkbox with its consequence lines, under the payment mode
- [x] 5.2 Queue roster marker for a held payment; flag reason labels in Payments (cs, en)

## 6. Checks

- [x] 6.1 Backend: `uv run ruff check .`, `uv run basedpyright`, scoped `pytest`
- [x] 6.2 Frontend: `npm run typecheck`, `npm run check`, `npm test`
