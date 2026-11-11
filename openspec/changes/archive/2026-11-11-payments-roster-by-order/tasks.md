## 1. Backend: order lines

- [x] 1.1 Add `pricing.registration_lines` (design D2): billed lines from the same selection and date as `registration_breakdown`, team lines per `Team` with name, discounts summed per discount/code, queued placements priced and flagged `queued`
- [x] 1.2 Tests: a mixed order's counted lines sum to `registration_breakdown`'s pieces less its deductions; a waitlisted team and a substitute entry come back `queued` and outside that sum; a legacy-priced tournament yields `legacy_*` lines
- [x] 1.3 Add `GET /tournaments/{slug}/payments/order-lines` with its schema (design D3), organizer-only like the other payments reads, with `selectinload` over entries, teams, extras and items
- [x] 1.4 Add `club` and `team_names` to `RankedFencerOut` and fill them in `transaction_roster` (design D7)
- [x] 1.5 `uv run ruff check .` and `uv run basedpyright` pass; `pytest tests/payments -q --maxfail=3 --tb=short --show-capture=no`

## 2. Frontend: the registration table lists orders

- [x] 2.1 `rowsForPhase("payments")` drops member rows (design D1); update `consolePhases`/`consoleTeamsPanel` tests for the start-field vs. orders split
- [x] 2.2 Rename the first-band tab to "Registrace" / "Registrations" in both locales (`payments.tabs.fencers`), and update `paymentTabs.test.tsx`

## 3. Frontend: contents and unfolding lines

- [x] 3.1 `api.ts`: types and the `orderLines(slug)` call for the new endpoint, plus `club`/`team_names` on `RankedFencer`
- [x] 3.2 `payments/orderLines.ts`: a pure summary builder and line labels (design D4), with unit tests for the one-team, mixed and queued-team scenarios
- [x] 3.3 Load the lines with the Payments phase, independently of the tables and on the same reload signal (design D3)
- [x] 3.4 Add the `contents` column to both the Payments and the boned-out Payments column sets; its cell is the disclosure control (design D6)
- [x] 3.5 `payments/OrderLines.tsx`: unfolded sub-rows under the order, with amounts in the amount column, queued lines muted and italic, and the difference line from `total_amount` (design D5, waived rows against the original total)
- [x] 3.6 Tests: every billed row unfolds; queued lines are marked and not counted; the difference line appears only on a mismatch; an EUR-local tournament states EUR

## 4. Frontend: pairing lookup

- [x] 4.1 `LinkDialog`: filter over name, club and team names, and show each candidate's contents summary (design D7)
- [x] 4.2 Extend `linkDialog.test.tsx`: found by team name, found by club

## 5. Finish

- [x] 5.1 i18n cs/en for the column, line kinds, the queued note and the difference line (lowercase sentence case, no exclamation marks)
- [x] 5.2 `npm run typecheck`, `npm run check` and `npm test` pass from `frontend/`
- [x] 5.3 Check by eye on TTT Test: 16 rows on Payments, every row unfolds, a mixed order reads correctly
