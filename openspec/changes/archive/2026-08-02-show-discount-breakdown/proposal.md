## Why

A tournament's discounts are invisible to the fencer. The registration form shows a
total that silently moves when a second discipline is ticked, and the tournament's
information page never mentions that discounts exist at all. The fencer cannot tell
whether a price is discounted, which discount they hit, or — more importantly — which
one they *just missed* by one discipline. The pricing engine already evaluates a named,
ordered discount list; it simply never says what it did.

## What Changes

- The `/price-preview` response gains a per-discount breakdown: for every discount the
  tournament configures, its name, its effect, and whether it applied to the selection
  just priced (plus, for applied discounts, the amount actually deducted). The total
  itself is unchanged — this reports on a computation that already happens.
- The registration form gains a **Discounts** section below the checklist and above the
  total, listing every configured discount with a read-only marker showing which ones
  the current selection activates. The marker state comes from the server's breakdown,
  so the form never re-derives a pricing rule.
- The tournament information page gains a **Discounts** section below the disciplines,
  listing each discount's name, condition, and value as static rows with no markers —
  there is no selection on that screen, so no claim is made about one.
- Rows state the organizer's configured value (`−500 Kč`, `−10 %`), not the realized
  deduction, so a row's figure is the same promise on both screens.
- A tournament with no configured discounts renders no section on either screen.
- The Setup preview inherits both sections with no work: it already renders through
  these components.

## Capabilities

### New Capabilities

None. Both screens and the pricing preview already have owning capabilities.

### Modified Capabilities

- `registration`: the price preview additionally reports, per configured discount,
  whether it applied to the previewed selection and what it deducted.
- `fencer-home`: the information screen lists the tournament's discounts below the
  disciplines; the register screen shows which discounts the current selection
  activates, alongside the live total.

## Impact

- `backend/app/pricing.py` — the itemized path must return which discounts it applied
  and what each took off, not just a total. Currently `_itemized_selection_total`
  discards that as it goes.
- `backend/app/schemas.py` — `PricePreviewOut` gains a discount-breakdown field.
- `backend/app/routers/registrations.py` — the `price-preview` handler passes it through.
- `frontend/src/api.ts` — `PricePreview` type gains the breakdown.
- `frontend/src/TournamentFace.tsx` — a shared discount-list component used by
  `DisciplinesInfo`'s screen and by `RegistrationForm`.
- `frontend/src/index.css`, `frontend/src/i18n/{cs,en}.json` — section styling and the
  new labels.
- No database migration, no change to any stored total, no change to what any existing
  registration owes. Legacy (non-itemized) tournaments have no discounts and are
  unaffected.
