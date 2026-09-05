## 1. Backend: expired-holding endpoint

- [x] 1.1 Add `ExpiredHoldingOut` to `backend/app/schemas.py`: `registration_id`, `fencer_name`, `vs`, `credited_amount` (Decimal), `credited_eur_amount` (Decimal | None), `expired_at`
- [x] 1.2 Add `GET /expired-holding` to `backend/app/routers/payments.py`: select `PaymentEvent` rows with `kind == "expired_holding_payment"` for the tournament, join their registration, keep only registrations still in `EXPIRED` state with credit remaining, newest expiry first; reuse the cents→amount conversion pattern from `routers/registrations.py::_cents_to_amount`
- [x] 1.3 Guard it with `require_console_access` like the sibling payment endpoints
- [x] 1.4 Add `backend/tests/` coverage: a reservation that expired holding a payment appears; an ordinary expiry does not; a since-reinstated one drops off; a non-organizer gets 403

## 2. Backend: outstanding balance on the sheet

- [x] 2.1 Add `outstanding_amount` and `outstanding_eur_amount` to the row dict in `backend/app/sheet.py::base_rows`, from `Registration.outstanding_cents` / `outstanding_eur_cents` (None when the registration has no EUR total)
- [x] 2.2 Add a test asserting a part-paid registration's sheet row carries the remaining balance and that a fully paid one reads zero
- [x] 2.3 Run `pytest` in `backend/`; confirm no existing sheet/export test breaks on the added keys
- [x] 2.4 (added during implementation, owner-approved) `export_json.py`: carry `amount_paid_cents` and `amount_paid_eur_cents` in `_REGISTRATION_FIELDS`, defaulted to 0 on restore for pre-v11 documents, `SCHEMA_VERSION` 10 → 11. The round-trip previously reconstructed a registration's totals but not its credit, so a restored tournament read as if nothing had been paid while its state still said paid — invisible until the outstanding column looked at the counters
- [x] 2.5 Cover it: the credited amount survives an export, and a pre-v11 document restores as uncredited rather than raising

## 3. Frontend: API surface

- [x] 3.1 Add `candidate_vs: number[]` and `last_evaluated_at: string | null` to the `Transaction` interface in `frontend/src/api.ts` (both already returned by `TransactionOut`, neither typed)
- [x] 3.2 Add `outstanding_amount: number` and `outstanding_eur_amount: number | null` to `SheetRow`
- [x] 3.3 Add an `ExpiredHolding` interface and a `PaymentLinkRule` type (or reuse a `Rule` shape mirroring `RuleOut`: `id`, `phase`, `kind`, `target`, `payload`, `created_at`)
- [x] 3.4 Add API methods: `linkTransaction(slug, {transaction_id, vs})`, `expiredHolding(slug)`, `rules(slug, phase)`

## 4. Frontend: the payments panel directory

- [x] 4.1 Create `frontend/src/payments/` and `git mv frontend/src/PaymentsPanel.tsx frontend/src/payments/FlaggedPanel.tsx`, rename the component, update the import in `Console.tsx`
- [x] 4.2 Have it request once and keep only `status === "flagged"` (unchanged behaviour, just no longer named as if it owned the whole phase); leave the `payments.flagged.*` i18n keys where they are
- [x] 4.3 Give the four queues a shared empty-state treatment: heading plus a zero count, no body, so an empty queue costs one line (design D1)

## 5. Frontend: unmatched queue and link dialog

- [x] 5.1 Create `frontend/src/payments/UnmatchedPanel.tsx`: lists `status === "unmatched"` transactions with date, payer name, amount + currency, message, and a link action per row; own loading/empty/error states like `FlaggedPanel`
- [x] 5.2 Create `frontend/src/payments/LinkDialog.tsx` on the `.modal-backdrop` / `.modal` pattern from `MatchDialog.tsx`: shows the transaction's payer, amount, date and message; renders `candidate_vs` as selectable entries; holds selection as `number[]` so several registrations can be chosen
- [x] 5.3 Add a hand-typed VS field to the dialog that appends to the same selection, with the selected set shown and individually removable
- [x] 5.4 Wire confirm to `POST /payments/link` with the full VS array; on success close, refresh the queue and the sheet
- [x] 5.5 Handle `ApiError`: `404` with `detail.unknown_vs` names the unrecognised values and keeps the dialog open with the entry preserved; `409 already_matched` closes and refreshes
- [x] 5.6 Mount the dialog from `UnmatchedPanel` and confirm keyboard/backdrop dismissal behaves like `MatchDialog`
- [x] 5.7 Add `frontend/src/payments/linkDialog.test.tsx`: a candidate accepted in one click; two VS values confirmed in a single request; `404 unknown_vs` naming the bad value and leaving the entry in place; `409` closing the dialog; dismissal creating no link

## 6. Frontend: expired-holding and payment-links queues

- [x] 6.1 Create `frontend/src/payments/ExpiredHoldingPanel.tsx`: lists fencer, VS, credited amount, expiry time from `expiredHolding(slug)`; empty state states plainly that nothing is stranded
- [x] 6.2 Create `frontend/src/payments/PaymentLinksPanel.tsx`: fetch `rules(slug, "payments")`, keep `kind === "payment_link"`, show target transaction and `payload.vs`, mark `payload.auto_created === true` as auto-created
- [x] 6.3 Add a remove action calling `deleteRule`, refetching the card and the sheet afterwards rather than assuming the outcome
- [x] 6.4 Add `frontend/src/payments/paymentsQueues.test.tsx`: the expired-holding list renders its rows; an auto-created link is marked apart from a manual one; removing a link refetches rather than dropping the row locally

## 7. Frontend: the payments main column

- [x] 7.1 In `Console.tsx`, render the four queues in the payments phase's main column, above `SheetArea`, in order: unmatched, flagged, expired-holding, payment links; the fencer table stays (design D1)
- [x] 7.2 Narrow the payments rail to `TolerancePanel` and `ManualEditsRail` — the four cards no longer go there
- [x] 7.3 Add `outstanding` to `PHASE_COLUMNS.payments`, after `total_amount`
- [x] 7.4 Add a money case to `CellDisplay` for `outstanding` and `total_amount` using `formatMoneyWithEur`; pass the currency context in as its own prop beside the existing `timezone` and `hrIdentity` props, not as the whole `TournamentDetail`. This also fixes `total_amount` currently rendering unitless
- [x] 7.5 Confirm the column renders `—` (not `0`) where a row has no registration behind it, e.g. imported rows
- [x] 7.6 Extend `frontend/src/consoleCells.test.tsx` for the money case (local only, local + EUR, and the `—` fallback), and add a payments-phase layout test: the four queues precede the table, an empty queue collapses to its heading, and one failing queue leaves the others and the table rendered

## 8. Localization

- [x] 8.1 Add `payments.unmatched.*`, `payments.link.*`, `payments.expiredHolding.*` and `payments.links.*` string groups to `frontend/src/i18n/en.json`
- [x] 8.2 Add the Czech equivalents to `frontend/src/i18n/cs.json` in the same pass
- [x] 8.3 Add the `outstanding` column header to both files alongside the existing payments column headers
- [x] 8.4 Grep for hardcoded user-facing strings in the new components; there should be none

## 9. Design compliance and verification

- [x] 9.1 Review the new components against `CLAUDE.md`: no gradients, shadows, blur, radii > 2px, emoji, filled icons, spinners, `#FFF`/`#000`, weight 600+, Title Case, or hexes outside `tokens.css`
- [x] 9.2 Confirm the queues reuse existing classes (`rail-card`, `sheet-table`, `row-action`, `rail-hint`, `muted`) and that any new CSS in `index.css` draws only on `tokens.css` values; check the cards read correctly at main-column width, not just at the rail's 300px
- [x] 9.3 Run `npm run lint`, `npm test` and `npm run build` in `frontend/`
- [x] 9.4 Run `pytest` in `backend/`
- [~] 9.5 Drive the console against a tournament seeded with an unmatched transaction carrying a candidate VS, a flagged one, a part-paid registration, a reservation expired holding a payment, and both an auto and a manual payment link; verify each queue and the link dialog end-to-end, and that a clean tournament still opens with the table near the top

  Partly done: driven against the running console on `na-duel-2026`. The four
  queues render in the main column above the fencer table, each collapsed to
  its heading and a zero; the `outstanding` column reads `—` on the imported
  rows; the rail holds only the tolerance panel and the edits log. Empty-queue
  padding was tightened after seeing it — four cards cost ~230px, not the "one
  line each" the design claims; now ~130px.

  Not done: the populated states end-to-end. The only tournaments on this
  machine are the owner's own pilot data and an unpublished scratch one, and
  seeding transactions, an expiry and links means writing to them. The
  populated states are covered by `vitest` against mocked responses and by
  `pytest` end-to-end on the backend, but not yet by the real UI on real
  rows.
- [x] 9.6 Add a note to `openspec/changes/archive/2026-08-01-harden-payment-matching/NOTES.md` recording that Group 10 is superseded by this change
