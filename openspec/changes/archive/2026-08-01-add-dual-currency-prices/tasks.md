## 1. Data model

- [x] 1.1 Rename `Tournament.primary_currency` to `local_currency` in `backend/app/models.py` and update the enum docstring, which currently says EUR is singled out as the currency the system can convert to — it is now singled out as the accepted second currency
- [x] 1.2 Add `Discipline.fee_eur` and `Discipline.fee_early_eur`, nullable, documented as authoritative prices and never derived
- [x] 1.3 Add `ExtraItem.price_eur`, nullable, same documentation
- [x] 1.4 Add `Registration.total_eur`, nullable, stored at registration exactly as `total_amount` is
- [x] 1.5 Add `Registration.amount_paid_eur_cents` defaulting to 0, and document that the two paid counters are never summed
- [x] 1.6 Re-document `Tournament.eur_rate` in place: a Setup convenience for recalculate-missing only, read by no pricing, matching, email, or QR path
- [x] 1.7 Extend the discount JSON shape so a `fixed` effect carries `value_eur` alongside `value`; leave `percent` effects unchanged

## 2. Migration

- [x] 2.1 Write one Alembic revision: rename `primary_currency`, add the five new columns as nullable
- [x] 2.2 Derive initial EUR prices for tournaments with `eur_payments_enabled` and a positive rate — each EUR price is the local price divided by the rate, rounded half-up to a whole unit
- [x] 2.3 Derive `total_eur` per registration on those tournaments the same way from `total_amount`
- [x] 2.4 Add `value_eur` to fixed discount effects on those tournaments, derived the same way; leave percentage effects untouched
- [x] 2.5 Leave every column NULL for tournaments that do not price in EUR
- [x] 2.6 Document in the revision that these figures are a one-time derivation, are approximations of what was previously displayed, and are authoritative prices from that point on
- [x] 2.7 Note in the revision that rollback loses any EUR price typed after deploy, so it is safe only immediately after deploying
- [x] 2.8 Verify on a copy of `backend/hema_squire.sqlite`: EUR-enabled tournaments have complete EUR prices, CZK-only tournaments gained none, and a sample of registrations renders EUR totals within one unit of today's

## 3. Pricing engine

- [x] 3.1 Parameterise `selection_total` and `_itemized_selection_total` in `backend/app/pricing.py` by currency, reading that currency's price column and that currency's fixed discount amount
- [x] 3.2 Keep the pipeline identical per currency: sum, fixed discounts floored at zero, then percentage discounts, then one half-up rounding to a whole unit
- [x] 3.3 Keep percentage discounts currency-neutral — one value applied to each currency's subtotals
- [x] 3.4 Update `registration_total` to return a total per configured currency
- [x] 3.5 **Delete** `to_eur` and `from_eur_cents` rather than leaving them unused, so no conversion helper survives to be re-wired
- [x] 3.6 Leave the legacy fixed weapon-rental and afterparty parameters single-currency and unchanged

## 4. Currency mode and Setup

- [x] 4.1 Derive the three modes from `local_currency` and `eur_payments_enabled` in `backend/app/schemas.py`, and validate that EUR mode is impossible when `local_currency` is EUR
- [x] 4.2 Extend setup completeness in `backend/app/setup.py` to require every rendered price field, so EUR completeness needs no separate rule
- [x] 4.3 Block enabling EUR on a tournament still pricing through the legacy fixed parameters, naming them and directing the organizer to itemized extra services
- [x] 4.4 Ensure a currency mode switch retains stored prices and clears nothing
- [x] 4.5 Keep `eur_rate` validation as it is (positive, plausibility warning), now framed as a Setup convenience

## 5. Payment path

- [x] 5.1 In `backend/app/matching.py`, replace the conversion step with selection of the total denominated in the transaction's currency
- [x] 5.2 Replace the `currency_unconvertible` reason with `currency_not_accepted`, which is what the condition actually is
- [x] 5.3 Remove `paid_cents_in_primary` and every remaining reference to a rate in the matching path
- [x] 5.4 Credit `amount_paid_cents` or `amount_paid_eur_cents` according to the transaction's currency, and never sum the two
- [x] 5.5 Settle a registration when either currency's credit covers that currency's total within tolerance; flag a registration part-paid in both
- [x] 5.6 Update `apply_payment_links` and `unapply_payment_link` to credit and revert within the link's own currency
- [x] 5.7 Record the currency alongside the amount in the payment audit entries

## 6. Emails, QR, and API

- [x] 6.1 Build each SPAYD string from its own currency's stored total in `backend/app/emails.py`, with `CC` from that currency, and remove the conversion call
- [x] 6.2 Present both totals from stored figures in the confirmation, reminder, and surcharge emails
- [x] 6.3 Return both totals and both QR codes from the payment-instructions endpoint, omitting the EUR pair entirely in single-currency mode
- [x] 6.4 Return a total per configured currency from the price-preview endpoint
- [x] 6.5 Update `schemas.py` response models for the renamed currency field and the second total throughout

## 7. Frontend

- [x] 7.1 Add the currency mode box above the price tables in `SetupPanel.tsx`, with the ratio input shown only in local + EUR mode
- [x] 7.2 Render one or two price columns from the mode, across disciplines and extra services
- [x] 7.3 Add the recalculate-missing action: fills empty fields only in either direction, rounds to whole units, never overwrites a typed value, and runs only when invoked
- [x] 7.4 Add per-currency amounts to fixed discount rows
- [x] 7.5 Add the price-change warning shown when registration is open, wording it as agreed — existing registrations keep their quoted amount, amending fencers are repriced, new registrations use the new price
- [x] 7.6 Present stored totals rather than converting anywhere in the registration form and fencer views
- [x] 7.7 Add cs and en i18n strings for the mode box, the second price column, recalculate-missing, and the warning, with no hardcoded currency units

## 8. Tests

- [x] 8.1 Two prices per item are stored as entered and neither is recomputed from the other
- [x] 8.2 Prices whose implied ratios differ across rows are accepted with no warning and no reconciliation
- [x] 8.3 Each currency totals independently, including fixed discounts per currency and a currency-neutral percentage discount
- [x] 8.4 Changing `eur_rate` after a reservation exists changes no stored price, no total, no payment instruction, and no QR code
- [x] 8.5 Recalculate-missing fills empty fields in either direction, rounds to whole units, and leaves typed values untouched
- [x] 8.6 A currency mode switch away and back reveals the same prices unchanged
- [x] 8.7 Incomplete EUR prices block registration through the existing completeness rule
- [x] 8.8 A legacy tournament using fixed fee parameters cannot enable EUR and is told why
- [x] 8.9 A EUR transaction matches against the stored EUR total with no conversion; a CZK transaction against the local total
- [x] 8.10 A transaction in an unpriced currency is flagged not-accepted and compared against nothing
- [x] 8.11 Credits are recorded per currency, are never summed, and either currency's credit settles the registration
- [x] 8.12 A registration part-paid in each currency is flagged rather than aggregated
- [x] 8.13 Each QR encodes its own currency's stored total with the matching SPAYD currency field
- [x] 8.14 A price change leaves existing registrations' totals and payment reconciliation untouched, and applies to new registrations
- [x] 8.15 A single-currency tournament is unaffected throughout — one price column, one total, one QR, totals identical to before
- [x] 8.16 The migration derives complete EUR prices for EUR-enabled tournaments and none for others

## 9. Verification

- [x] 9.1 Run the full backend test suite; update the existing EUR matching tests, which assert conversion behaviour that no longer exists
- [x] 9.2 Confirm by search that no code path reads `eur_rate` outside the Setup convenience, and that `to_eur` and `from_eur_cents` are gone
- [x] 9.3 Run `openspec validate add-dual-currency-prices --strict`
- [x] 9.4 Rebase `harden-payment-matching`: its `Amount tolerance` delta and its currency-conversion tasks describe a step this change removes
- [x] 9.5 Walk the flow in the running app: configure a CZK + EUR tournament, recalculate missing, register, check both QR codes, pay in each currency, then change the rate and confirm nothing moves
