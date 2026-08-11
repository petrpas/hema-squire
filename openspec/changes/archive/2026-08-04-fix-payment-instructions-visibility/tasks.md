## 1. Backend: bank account becomes a mandatory setup item

- [x] 1.1 Add `MISSING_BANK_ACCOUNT = "bank_account"` to the item-key block in `backend/app/setup.py`, alongside the existing `MISSING_*` constants
- [x] 1.2 Add a `charges_money(tournament) -> bool` helper next to `uses_legacy_fixed_fees()`: true when any of `Discipline.fee`, `fee_early`, `fee_eur`, `fee_early_eur`, `ExtraItem.price`, `price_eur`, or the four legacy `Tournament` fee columns is above zero. Discounts are excluded — they only reduce a total (design Decision 2)
- [x] 1.3 Add the check to `setup_missing()`: when `charges_money(tournament)` and `not (tournament.bank_account or "").strip()`, append `MISSING_BANK_ACCOUNT`
- [x] 1.4 Confirm no other change is needed — `publish_tournament` (`routers/tournaments.py:998`) and `guard_published_completeness` both consume `setup_missing()` and need no edit; `registration_availability()` is deliberately untouched (design Decision 1)
- [x] 1.5 Add `backend/tests/` coverage: a priced tournament complete but for the bank account is refused publication with `422` naming `bank_account`; it publishes once the account is set; an all-zero-price tournament publishes with no account; clearing the account on a published priced tournament is refused by `guard_published_completeness`; a draft may still be saved without it
- [x] 1.6 Add the transition test: a **published** free tournament that gains its first nonzero price is refused that save until an account is supplied, and the refusal names `bank_account` (design Decision 2, second consequence)
- [x] 1.7 Run `pytest` in `backend/` and fix any existing test that publishes a priced fixture tournament without a bank account — expect several, since nothing required it before

## 2. Backend: report already-published tournaments

- [x] 2.1 Add a one-shot script under `backend/` (matching the existing operational-script style) listing published, non-cancelled tournaments whose `bank_account` is empty: slug, display name, date, and count of live registrations
- [x] 2.2 Document in the script's docstring that it is run once after deploy and that repair is a manual Setup edit — the publish gate cannot reach tournaments published before it existed (design Decision 4)

## 3. Frontend: bank account onto the PAYMENTS tab

- [x] 3.1 Create `frontend/src/setup/BankAccountSection.tsx` holding `bank_account`, following the save pattern of the sibling sections and registering with `SaverRegistry` like the others on that tab
- [x] 3.2 Render it in `SetupPanel.tsx` in the `setup-tabpanel-payments` panel, **first**, above `CurrencySection` (spec: the account precedes the currency it is denominated in)
- [x] 3.3 Remove `{ key: "bank_account", type: "text" }` from `PHASE_PARAMS.payments` in `ParamPanel.tsx`, and its `case "bank_account"` from `fieldCheck` if nothing else uses it — the field must have exactly one editor
- [x] 3.4 Add `bank_account: "payments"` to `MISSING_TAB` in `setup/shared.tsx` so the item marks its tab
- [x] 3.5 Reuse the existing `checkString(key, "TournamentUpdate.bank_account", raw)` validation so the Setup field enforces the same bound the console field did

## 4. Frontend: the payment panel stops failing silently

- [x] 4.1 In `TournamentDetail.tsx`, give `PaymentPanel` a discriminated state — `loading | ready | reason` — instead of `PaymentInstructions | null`, and capture the `ApiError` in the rejection handler rather than discarding it
- [x] 4.2 Map the endpoint's three refusals to their own copy: `no_payment_due` → the "everything you asked for is queued" text (the string moved in 4.4), `no_bank_account` → payment details not available, organizer will supply them, `not_unpaid` → this reservation is no longer awaiting payment. Any other failure gets the generic retry text
- [x] 4.3 Render each state as static text in existing classes (`.rail-hint` for the informational reasons, `.login-error` for the generic failure) — no new colour, icon, spinner or animation (`CLAUDE.md`)
- [x] 4.4 Delete the `fullyQueued` computation (line 269) and both branches at lines 296-299; render `<PaymentPanel slug={slug} />` for any `reserved` registration. The `registration.fullyQueuedHint` string **moves** into the panel's `no_payment_due` state — keep the i18n key so the Czech translation is not re-authored (design Decision 3)
- [x] 4.5 Verify `ApiError` in `api.ts` exposes `status` and `detail` in the shape 4.2 reads; the 409 bodies are bare strings (`detail: "no_payment_due"`), not objects — confirm against `registrations.py:687,695` before writing the branch

## 5. Localization

- [x] 5.1 Add `en.json` and `cs.json` strings for the bank-account section (label, and a hint that registrations cannot be paid without it) and for the three refusal reasons plus the generic failure
- [x] 5.2 Add the `bank_account` item label to the `PUBLISH` tab's missing-item catalogue in both locales, matching how the other `MISSING_*` keys are named
- [x] 5.3 Confirm `registration.fullyQueuedHint` still resolves after the move in 4.4, in both locales

## 6. Verification

- [x] 6.1 `npm run lint` (`tsc -b --noEmit`) and `npm run build` in `frontend/`
- [x] 6.2 `pytest` in `backend/`
- [x] 6.3 Drive a registration through all four panel states against a seeded tournament: instructions shown; team-only waitlisted registration (nothing due); tournament with the bank account cleared on a draft (no details); registration matched while the panel is open (no longer awaiting payment)
- [x] 6.4 Confirm the two divergence cases from the proposal now behave: a team-only registration with an active team shows a payment slip; a registration with queued entries and an active team shows a slip rather than the "all queued" hint
- [x] 6.5 Confirm the `PAYMENTS` tab carries the incompleteness marker while a priced tournament's bank account is empty, that `PUBLISH` lists it, and that setting the first nonzero price on `DISCIPLINES` raises the marker on `PAYMENTS` without visiting that tab
