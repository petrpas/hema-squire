## Context

`backend/app/pricing.py` computes an itemized total by filtering the tournament's
ordered discount list down to those whose condition is met, applying every fixed effect
to its scoped category subtotals, then every percentage effect, and rounding once at the
end. That filtered list — the exact answer to "which discounts are active" — exists as a
local variable inside `_itemized_selection_total` and is discarded when the function
returns an `int`.

The fencer-facing side already calls the endpoint that runs this computation. The
register form (`RegistrationForm` in `frontend/src/TournamentFace.tsx`) debounces a
`POST /price-preview` on every selection change and renders the returned total. So the
data the fencer needs is computed on every keystroke and thrown away twice: once in the
pricing module, once in the response schema.

Constraints:

- Pricing has exactly one authority (module docstring: prices are a pure function of
  tournament, item, and as-of date). A second evaluator in TypeScript would be a second
  authority, and would judge early-bird against the browser's clock.
- Two currencies are computed independently, never derived from one another
  (`selection_totals`, design Decision 1 of the pricing work). A discount's reported
  deduction must follow the same rule.
- `CLAUDE.md` prohibitions bind the UI: no emoji, no filled icons, no shadows, no
  border-radius above 2px, one saturated color.
- Legacy tournaments (no extras, no discounts) skip the itemized path entirely.

## Goals / Non-Goals

**Goals:**

- A fencer choosing disciplines can see which discounts their selection activates and
  which it does not, without arithmetic.
- A fencer reading the information page can see that discounts exist and on what terms,
  before deciding to register.
- The discount list the fencer sees and the discount list the pricing engine applies are
  the same list, produced by the same evaluation.

**Non-Goals:**

- Changing any price, total, or rounding. Every existing total stays bit-identical.
- Explaining *how* to reach an inactive discount ("add one more discipline and save
  200 Kč"). The condition text is shown; the advice is not.
- Showing discounts on a saved registration's summary, in the confirmation email, or in
  exports. Those show what was charged; this change is about the choosing.
- A Setup-side scope picker or any new discount condition kind.
- Explaining scope. A discount scoped to `merch` reads the same as one scoped to
  `discipline`; the organizer's name for the row carries that meaning.

## Decisions

### Decision 1 — the server reports applicability, in the price-preview response

`_itemized_selection_total` becomes a function that returns the total *and* the per-
discount outcome; a thin wrapper keeps the existing `int`-returning signature for
`selection_total`. `PricePreviewOut` gains `discounts: list[DiscountBreakdown]`, one
entry per configured discount in configured order, each carrying the discount's name,
its effect, whether it applied, and — when it applied — what it deducted.

*Alternative rejected:* evaluating `condition` in TypeScript from `detail.discounts`,
which the form already holds. It needs no backend change, but it re-implements
`_condition_met` in a second language, where it would drift the first time a condition
kind is added, and it would judge the `early` condition against the browser clock while
the total beside it was judged against the server's — a fencer registering near midnight
in another timezone would see a ticked early-bird row above an undiscounted total.

### Decision 2 — the breakdown covers every configured discount, not just the applied ones

An inactive discount is the more useful row: it is the one the fencer can still act on.
Reporting only applied discounts would make the list flicker as rows appear and vanish
mid-selection, and would make "you missed this by one discipline" invisible — the exact
case the `discipline_count` condition creates, since it matches an exact count rather
than a minimum.

### Decision 3 — the fixed-effect deduction is reported per currency, the percentage effect is not

A fixed effect carries `value` and `value_eur` as two independent organizer decisions, so
its reported deduction carries both, each measured in its own currency's computation. A
percentage effect is currency-neutral by schema (`value_eur` is rejected for it), so it
reports one percentage and no per-currency amount. This mirrors the pricing module
exactly rather than inventing a parallel rule.

Consequence: the breakdown is computed from the local-currency pass, and the EUR
deduction is read from the EUR pass of the same selection. Applicability is
currency-independent — a condition is about counts and dates, never money — so both
passes necessarily agree on which discounts applied, and the response carries one
applicability flag, not two.

### Decision 4 — rows show the configured value, not the realized deduction

A row reads `−500 Kč` or `−10 %` — what the organizer configured, matching what the
information page promises. The realized deduction can differ: `_apply_fixed` floors the
subtraction at the scoped subtotal, so a 500 Kč discount against a 300 Kč subtotal takes
300. Showing that would make the row's figure move as the selection changes and would
contradict the same row on the information page.

The realized amount is still reported by the API (Decision 1) — the response tells the
truth, the UI chooses the stable figure. That keeps a future "you saved X in total" line
a pure frontend change.

### Decision 5 — one component, two renderings

A single `DiscountList` in `TournamentFace.tsx` takes the tournament and an optional
breakdown. Given a breakdown (register form) it renders a marker column; given none
(information page) it renders the rows without markers and with each condition spelled
out. This is one component because the two lists must never disagree about names,
amounts, or order — and because `SetupPreview` renders both faces through these same
components, so the organizer's preview inherits both renderings for free.

### Decision 6 — the marker is a disabled checkbox, matching the checklist above it

The section sits directly below a checklist of real checkboxes, so its markers are
`<input type="checkbox" disabled checked={...}>` with the same styling — the fencer reads
one visual language down the whole form, and the sketch's `[x] / [ ]` is literal. Being
disabled (not read-only) is the point: these boxes state a consequence of the choices
above, and are not themselves choices.

### Decision 7 — the condition is rendered from its data, in each language

A condition renders as localized text from `kind` plus its parameter: `discipline_count`
→ "when registered for N disciplines", `early` → "when registered by <date>". The
discount's `name` is organizer-written free text and may already say this ("2 disciplíny"
in the sketch) — the condition line is rendered under the name on the information page,
where there is no selection to make the terms self-evident, and omitted in the form,
where the marker states the answer directly.

### Decision 8 — no section when there is nothing to say

A tournament with an empty `discounts` list renders no heading and no empty state on
either screen — matching how `OtherActionsInfo` already returns `null` for an empty list.
Legacy tournaments have no discounts by definition, so they are unaffected without a
special case.

## Risks / Trade-offs

- **A discount's realized deduction can be smaller than the row's stated value**
  (`_apply_fixed` floors at the scoped subtotal) → the fencer could read `−500 Kč` while
  only 300 came off. Mitigated by the total being authoritative and always shown
  directly below, and by this being rare in practice: a fixed discount scoped to
  disciplines exceeding the discipline subtotal means the discount is larger than the
  entry fee. Accepted for now; the realized amount is in the API when a future line
  wants it.
- **The breakdown is only as fresh as the debounced preview** (300 ms) → markers lag the
  checkbox by up to a debounce plus a round-trip. Same lag the total already has, and
  the two now move together, so the section cannot contradict the number below it.
- **A failed price-preview blanks the total today** (the catch sets it to 0) → it must
  blank the markers too rather than leave stale ones ticked beside a zero total. The
  breakdown is cleared on the same path.
- **Zero disciplines never calls the endpoint** (`PricePreviewIn` requires at least one,
  and the form short-circuits) → with nothing selected there is no server answer. The
  form renders every row unmarked, which is correct: no selection, no discount, total 0.
- **Adding a condition kind now has two obligations** — evaluate it and label it. The
  label lives in the locale files next to the others; a kind with no label is a visible
  gap in one screen rather than a wrong price.

## Migration Plan

No migration. No schema change, no stored value changes, no endpoint removed. The new
response field is additive; an old frontend against a new backend ignores it, and a new
frontend against an old backend renders the information page normally and the form
without markers. Rollback is a revert.

## Open Questions

None. The three decisions this change turned on — server-side evaluation, an unmarked
information-page list, and configured rather than realized amounts — were settled with
the owner before drafting.
