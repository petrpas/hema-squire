## 1. Backend: expired-holding endpoint

- [ ] 1.1 Add `ExpiredHoldingOut` to `backend/app/schemas.py`: `registration_id`, `fencer_name`, `vs`, `credited_amount` (Decimal), `credited_eur_amount` (Decimal | None), `expired_at`
- [ ] 1.2 Add `GET /expired-holding` to `backend/app/routers/payments.py`: select `PaymentEvent` rows with `kind == "expired_holding_payment"` for the tournament, join their registration, keep only registrations still in `EXPIRED` state with credit remaining, newest expiry first; reuse the cents→amount conversion pattern from `routers/registrations.py::_cents_to_amount`
- [ ] 1.3 Guard it with `require_console_access` like the sibling payment endpoints
- [ ] 1.4 Add `backend/tests/` coverage: a reservation that expired holding a payment appears; an ordinary expiry does not; a since-reinstated one drops off; a non-organizer gets 403

## 2. Backend: outstanding balance on the sheet

- [ ] 2.1 Add `outstanding_amount` and `outstanding_eur_amount` to the row dict in `backend/app/sheet.py::base_rows`, from `Registration.outstanding_cents` / `outstanding_eur_cents` (None when the registration has no EUR total)
- [ ] 2.2 Add a test asserting a part-paid registration's sheet row carries the remaining balance and that a fully paid one reads zero
- [ ] 2.3 Run `pytest` in `backend/`; confirm no existing sheet/export test breaks on the added keys

## 3. Frontend: API surface

- [ ] 3.1 Add `candidate_vs: number[]` and `last_evaluated_at: string | null` to the `Transaction` interface in `frontend/src/api.ts` (both already returned by `TransactionOut`, neither typed)
- [ ] 3.2 Add `outstanding_amount: number` and `outstanding_eur_amount: number | null` to `SheetRow`
- [ ] 3.3 Add an `ExpiredHolding` interface and a `PaymentLinkRule` type (or reuse a `Rule` shape mirroring `RuleOut`: `id`, `phase`, `kind`, `target`, `payload`, `created_at`)
- [ ] 3.4 Add API methods: `linkTransaction(slug, {transaction_id, vs})`, `expiredHolding(slug)`, `rules(slug, phase)`

## 4. Frontend: rename the flagged panel

- [ ] 4.1 `git mv frontend/src/PaymentsPanel.tsx frontend/src/FlaggedPanel.tsx`, rename the component, update the import and usage in `Console.tsx`
- [ ] 4.2 Have it request once and keep only `status === "flagged"` (unchanged behaviour, just no longer named as if it owned the whole phase); leave the `payments.flagged.*` i18n keys where they are

## 5. Frontend: unmatched queue and link dialog

- [ ] 5.1 Create `frontend/src/UnmatchedPanel.tsx`: rail card listing `status === "unmatched"` transactions with date, payer name, amount + currency, message, and a link action per row; own loading/empty/error states like `FlaggedPanel`
- [ ] 5.2 Create `frontend/src/LinkDialog.tsx` on the `.modal-backdrop` / `.modal` pattern from `MatchDialog.tsx`: shows the transaction's payer, amount, date and message; renders `candidate_vs` as selectable entries; holds selection as `number[]` so several registrations can be chosen
- [ ] 5.3 Add a hand-typed VS field to the dialog that appends to the same selection, with the selected set shown and individually removable
- [ ] 5.4 Wire confirm to `POST /payments/link` with the full VS array; on success close, refresh the queue and the sheet
- [ ] 5.5 Handle `ApiError`: `404` with `detail.unknown_vs` names the unrecognised values and keeps the dialog open with the entry preserved; `409 already_matched` closes and refreshes
- [ ] 5.6 Mount the dialog from `UnmatchedPanel` and confirm keyboard/backdrop dismissal behaves like `MatchDialog`

## 6. Frontend: expired-holding and payment-links cards

- [ ] 6.1 Create `frontend/src/ExpiredHoldingPanel.tsx`: rail card listing fencer, VS, credited amount, expiry time from `expiredHolding(slug)`; empty state states plainly that nothing is stranded
- [ ] 6.2 Create `frontend/src/PaymentLinksPanel.tsx`: fetch `rules(slug, "payments")`, keep `kind === "payment_link"`, show target transaction and `payload.vs`, mark `payload.auto_created === true` as auto-created
- [ ] 6.3 Add a remove action calling `deleteRule`, refetching the card and the sheet afterwards rather than assuming the outcome

## 7. Frontend: console wiring and the outstanding column

- [ ] 7.1 In `Console.tsx`, render the four cards for `phase === "payments"` in order: flagged, unmatched, expired-holding, payment links
- [ ] 7.2 Add `outstanding` to `PHASE_COLUMNS.payments`, after `total_amount`
- [ ] 7.3 Add a money case to `CellDisplay` for `outstanding` and `total_amount` using `formatMoneyWithEur(local, eur, detail)`; this also fixes `total_amount` currently rendering unitless — `CellDisplay` needs the tournament detail passed in
- [ ] 7.4 Confirm the column renders `—` (not `0`) where a row has no registration behind it, e.g. imported rows

## 8. Localization

- [ ] 8.1 Add `payments.unmatched.*`, `payments.link.*`, `payments.expiredHolding.*` and `payments.links.*` string groups to `frontend/src/i18n/en.json`
- [ ] 8.2 Add the Czech equivalents to `frontend/src/i18n/cs.json` in the same pass
- [ ] 8.3 Add the `outstanding` column header to both files alongside the existing payments column headers
- [ ] 8.4 Grep for hardcoded user-facing strings in the new components; there should be none

## 9. Design compliance and verification

- [ ] 9.1 Review the new components against `CLAUDE.md`: no gradients, shadows, blur, radii > 2px, emoji, filled icons, spinners, `#FFF`/`#000`, weight 600+, Title Case, or hexes outside `tokens.css`
- [ ] 9.2 Confirm the new cards reuse existing classes (`rail-card`, `sheet-table`, `row-action`, `rail-hint`, `muted`) and that any new CSS in `index.css` draws only on `tokens.css` values
- [ ] 9.3 Run `npm run lint` and `npm run build` in `frontend/`
- [ ] 9.4 Run `pytest` in `backend/`
- [ ] 9.5 Drive the console against a tournament seeded with an unmatched transaction carrying a candidate VS, a flagged one, a part-paid registration, a reservation expired holding a payment, and both an auto and a manual payment link; verify each card and the link dialog end-to-end
- [ ] 9.6 Add a note to `openspec/changes/harden-payment-matching/NOTES.md` recording that Group 10 is superseded by this change
