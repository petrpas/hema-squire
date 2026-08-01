## 1. Pricing engine reports what it applied

- [x] 1.1 In `backend/app/pricing.py`, add a `DiscountOutcome` NamedTuple (name, effect, applied, deducted) and a `_itemized_selection_breakdown` that returns the total together with one outcome per configured discount, in configured order — inactive discounts included. Have `_apply_fixed` return how much it actually consumed so a floored deduction is reported as taken, and capture each percentage effect's realized reduction from the subtotals it scaled.
- [x] 1.2 Reduce `_itemized_selection_total` to a thin wrapper over the new function so `selection_total` keeps its `int` signature and every existing caller is untouched.
- [x] 1.3 Add `selection_discounts(tournament, *, disciplines, extras, at)` returning the per-discount breakdown for a selection, with each fixed effect's deduction taken from its own currency's pass (local always; EUR only when `tournament.shows_eur`) and percentage effects carrying one currency-neutral figure. Return an empty list for legacy tournaments and for any tournament with no discounts.
- [x] 1.4 Extend `backend/tests/test_pricing_itemized.py`: applied and unapplied rows both present and ordered; a fixed deduction floored at its scoped subtotal reported as the floored amount; per-currency deductions on a CZK + EUR tournament each read from their own column; early-bird applicability judged by the passed `at` date; empty breakdown for a legacy tournament. Assert existing totals are unchanged.

## 2. Price-preview contract

- [x] 2.1 In `backend/app/schemas.py`, add a `DiscountBreakdownOut` (name, effect, applied, deducted amount per currency when applied) and add `discounts: list[DiscountBreakdownOut]` to `PricePreviewOut`.
- [x] 2.2 In `backend/app/routers/registrations.py`, have `price_preview` call `selection_discounts` for the already-resolved selection and return it alongside the totals.
- [x] 2.3 Extend `backend/tests/test_registrations.py` with price-preview cases covering the spec scenarios: breakdown lists applied and unapplied discounts, fixed deduction reported in both currencies, percentage entry carries no EUR value, empty breakdown when the tournament configures none.

## 3. Shared discount list component

- [x] 3.1 In `frontend/src/api.ts`, add the `DiscountBreakdown` interface and the `discounts` field on `PricePreview`.
- [x] 3.2 In `frontend/src/TournamentFace.tsx`, add an exported `DiscountList({ detail, breakdown })`: renders one row per `detail.discounts` entry with the discount's name and its configured value via `formatMoneyWithEur` for a fixed effect or a percentage for a percent effect. With a `breakdown`, each row leads with a disabled checkbox reflecting that discount's `applied` flag; without one, rows carry no marker and each shows its condition as text. Returns `null` when `detail.discounts` is empty.
- [x] 3.3 Add a `discountCondition` helper rendering a condition from `kind` plus its parameter (`discipline_count` → count, `early` → date), formatting the date the way the rest of the file does.

## 4. Information page

- [x] 4.1 Render `DiscountList` without a breakdown directly below `DisciplinesInfo` on the fencer-facing tournament page, in its own `rail-card` section with a `detail.discounts` heading — check both `TournamentDetail.tsx` and `SetupPreview.tsx`'s tournament-face tab compose the same section so the organizer preview inherits it.

## 5. Registration form

- [x] 5.1 In `RegistrationForm`, hold the breakdown in state beside `total`/`eurTotal`; set it from the price-preview result, and clear it to empty on both the zero-disciplines short circuit and the request-failure path, so markers never outlive the total they belong to.
- [x] 5.2 Render `DiscountList` with the breakdown between the last checklist section and the `form-total` line.

## 6. Copy and styling

- [x] 6.1 Add the new keys to `frontend/src/i18n/cs.json` and `en.json`: the section heading on both screens, the condition phrasings, and the percentage and negative-amount value formats. No hardcoded strings, no currency unit in a message (units come from `money.ts`).
- [x] 6.2 Style the section in `frontend/src/index.css`, reusing the `checklist` grid so a discount row aligns with the checkbox rows above it, and style the disabled marker to read as stated-fact rather than disabled-control. Honor the `CLAUDE.md` prohibitions: no emoji or filled icons, no shadows, tokens only.

## 7. Verification

- [x] 7.1 Run the backend test suite and the frontend build/lint; confirm no existing total or snapshot changed.
- [x] 7.2 Walk the seeded demo tournament (`scripts/seed_demo.py`) in the browser: information page lists the discounts unmarked below the disciplines; the register form's markers flip on the second discipline and the total drops in the same refresh; a tournament without discounts shows no section on either screen; the Setup preview shows both faces exactly as the fencer sees them.
