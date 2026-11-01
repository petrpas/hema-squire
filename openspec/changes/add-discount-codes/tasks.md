## 1. Data model

- [x] 1.1 Add `DiscountCode` to `models.py` (tournament, code, name, max_uses, effect kind, value, value_eur, scope) with `unique(tournament_id, code)`; add `Registration.discount_code_id` and `Registration.code_covered`
- [x] 1.2 Alembic revision for the table and the two columns, with a working downgrade
- [x] 1.3 Add field bounds to `constraints.py` and `constraints.ts`, and `DiscountCodeStr` to `fieldtypes.py`
- [x] 1.4 Delete a tournament's codes in `tournament_delete.py`, after registrations

## 2. Pricing

- [x] 2.1 Extract the discount loop in `pricing.py` to run over subtotals, keeping fixed before percent, with a code appended after the automatic discounts
- [x] 2.2 Thread the code through `selection_total(s)`, `selection_discounts`, `registration_total`, `claim_totals`; expose the code's outcome separately from the configured breakdown
- [x] 2.3 Price a code on the legacy path from legacy subtotals, leaving `uses_itemized_pricing` unaware of codes; make `registration_breakdown`'s legacy branch return deductions
- [x] 2.4 Add `code_id` to `CategoryDeduction`
- [x] 2.5 Set `code_covered` in `reprice`: the code deducted something and a lane's total is zero
- [x] 2.6 Tests: stacking order (the 1275 Kč case), both worlds, the flat fee still billed, two currencies, floor at zero, a code that deducted nothing leaves `code_covered` false, breakdown still sums to the total

## 3. Settled and its readers

- [x] 3.1 Add the third arm to `Registration.settled` and to its SQL expression, the queue guard preserved
- [x] 3.2 Walk every reader of `settled` and `settling_lane` (`ledger.py`, `scheduler.py`, `matching.py`, `emails.py`, `exportrevenue.py`, `sheet.py`, `entrants.py`, `routers/payments.py`, `routers/registrations.py`, `routers/tournaments.py`), giving each lane-assuming branch the waiver's treatment
- [x] 3.3 Make `cancel()` record a refund standing only where credit is held
- [x] 3.4 Tests: a 100 % code on a paying tournament is never reminded or expired; amending down from covered reopens a window; a covered queue registration reads reserved until admitted; cancelling opens no refund
- [x] 3.5 Withhold the claim where a code covers it, so a queued registration is never offered 0 Kč

## 4. Redemption

- [x] 4.1 New `app/discount_codes.py`: normalization, `find_usable`, derived `uses`, `claim` taking the row lock and refusing past the limit
- [x] 4.2 Accept a code in `RegisterIn`; in `create_registration` check early, then claim after the flush; set the key on every cycle so a re-registration carries only what it submits
- [x] 4.3 Accept a code in the amendment body; add-only, refuse a replacement, leave the console correction path untouched
- [x] 4.4 Add the rate-limited code preview route, and a managed-registration preview pricing the held code without an availability check
- [x] 4.5 Add `applied_code` to `PricePreviewOut` and `RegistrationOut`, and `accepts_discount_codes` to `TournamentOut`
- [x] 4.6 Tests: identical refusal for unknown, foreign and exhausted; last-use race; release on cancel and expiry; a revival overrunning the limit; re-registering without the code; a held code past its limit still repricing; preview equals registration; substitution keeps the code; no public response contains any code data

## 5. Organizer API

- [x] 5.1 CRUD endpoints under console access, with bounds from `money_bounds`, duplicate refusal, locking while a registration carries the code, and limit not below uses
- [x] 5.2 Report a fixed code's missing EUR amount through `MISSING_DISCOUNT_PRICES` in `setup.py`
- [x] 5.3 Redemptions endpoint: live holders with deduction and paid state, plus uses per code
- [x] 5.4 Tests: lock, retire by lowering the limit, delete refused for a code a cancelled row carries, console access required

## 6. Mail and the deposit

- [x] 6.1 Add the nothing-to-pay case to the confirmation in `emails.py`, with no QR, in both locale files
- [x] 6.2 Cap the deposit at the total in the due mail, the reminder, the QR and the payment instructions
- [x] 6.3 Tests: confirmation of a covered registration, and a total below the deposit

## 7. Revenue and export

- [x] 7.1 Tally code deductions by `code_id` in `exportrevenue.py` and emit a `Sleva <name>` line per code, on both pricing paths
- [x] 7.2 Export schema v20 in `export_json.py`: codes, each registration's code and `code_covered`; defaults for older documents
- [x] 7.3 Tests: a block sums with a code in it; a round trip keeps uses and covered state; v19 loads

## 8. Frontend: Setup

- [x] 8.1 Move `slugify` out of `TournamentCreateDialog.tsx` into a shared module
- [x] 8.2 Add `setup/DiscountCodesSection.tsx` below `DiscountsSection`: name, code following the name until edited, limit, effect, scope for a percentage, uses; saved through the section saver; hidden on a manual tournament; locked fields say why; help text warns that a code derived from a common word can be guessed
- [x] 8.3 Tests: slug prefill stops once edited, fields lock on a used code, section absent on manual

## 9. Frontend: fencer

- [x] 9.1 Add a code field component used by the register form and the amendment form, with a refresh sharing the evaluation of the total
- [x] 9.2 Wire the guest variant; submit only an accepted code; keep the form on a refused submission
- [x] 9.3 Show the code's line on the registration, and no payment slip when covered
- [x] 9.4 Tests: field absent, accepted, refused, selection changed after applying

## 10. Frontend: Payments phase

- [x] 10.1 Add the codes tab to `PaymentTabs`, shown only while the tournament has a code, including on a payments-off tournament
- [x] 10.2 Add the codes table and the uses line, loading independently and stating emptiness in one line
- [x] 10.3 Tests: tab absent without codes; its failure leaves the other tables alone; 2 / 1 renders after a revival

## 11. Finish

- [x] 11.1 Add the copy to both i18n files in sentence case, no exclamation marks
- [x] 11.2 Backend: `uv run ruff check .`, `uv run basedpyright`, scoped pytest with `--hypothesis-profile=dev`
- [x] 11.3 Frontend: `npm run typecheck`, `npm run check`, `npm test`, `npm run build`
- [x] 11.4 Check the form, Setup section and table against the prohibitions in `CLAUDE.md`, on both skins, and at phone width
