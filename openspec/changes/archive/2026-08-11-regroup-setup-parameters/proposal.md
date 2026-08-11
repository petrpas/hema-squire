## Why

Setup is where decisions about the tournament as a whole are made, before it is published; in the ideal case it is never touched again. The rest of the console is where decisions about people and teams are made, during registration. That split is the tool's logic, and `ParamPanel.tsx` — the console's "Parameters" rail card — breaks it for thirteen of its fourteen fields. Every one of them is a tournament-wide decision settled before publication: the payment mode, the deposit, the seating deadline, the payment window, prices, policy dates.

The split already has a mechanical test, which the code half-keeps: **anything that can block Publish must be reachable from a Setup tab.** Two items fail it today, both of them `ParamPanel` fields:

- **`deposit_amount`** gates publication (`setup.py:123`) and `MISSING_TAB` has no entry for it. The organizer is told *"the deposit is missing on a tournament that takes one"* by the Publish checklist, no tab is marked — and because `markedTabs` is then empty, the `if (markedTabs.size > 0) markedTabs.add("publish")` line does not fire either. The field lives on a screen Setup cannot reach.
- **`legacy_fixed_fees_block_eur`** gates publication and `MISSING_TAB` maps it to `PAYMENTS`, so Setup confidently marks a tab that does not contain `weapon_rental_fee` or `afterparty_fee` — they are in the console's `load` phase.

Separately, the tournament's five dates are scattered across three components with no view that shows them together, though they constrain each other and are validated against each other server-side. An organizer setting the seating deadline cannot see the registration close it must precede — the usability risk `add-payment-modes` flagged and could not resolve from inside one panel.

## What Changes

**A new `TIMELINE` tab**, between `EXTRA` and `PAYMENTS`, holding every date in chronological order with the tournament date pinned read-only at the foot as the anchor:

```
  registration opens  →  seating deadline  →  registration closes
                      →  team composition  →  tournament date (read-only)
```

Each date carries a hint stating what it does and what happens when it is left unset, since four of the five are optional and their fallbacks are otherwise invisible. The team composition deadline moves here from `DISCIPLINES`, and its hint leads with what it does **not** do — it reminds and never enforces, which the label alone implies the opposite of.

**A new `PaymentModeSection` on `PAYMENTS`**, standing first: the payment mode as three options each carrying a one-line consequence built from the tournament's own values, the deposit amount nested inside its own option so it reads as part of the sentence rather than a field that appears and vanishes, plus the payment window and reminder day. It replaces a three-option `<select>` sitting eighth of ten on an operations screen.

**Parameters that are not decisions leave the UI**, their columns retained so each can return as a parameter later without a migration:

| Field | Why it goes | Behaviour after |
| --- | --- | --- |
| `refundable_until` | refunds are the organizer's own business for now | the column, `RefundState` and `refundable` stay for a future partial-refund policy |
| `amendments_close` | unset already means "same window as registration" (`setup.py:162-172`) | unchanged — dropping the field *is* the requested default |
| `expiry_grace_hours` | a bank-latency tolerance, not an organizer's opinion | fixed at its existing default of 48 hours |
| `early_bird_until` | superseded by the `early` discount condition (`pricing.py:117`), and `Discipline.fee_early` has no editor anywhere | legacy tournaments keep repricing from the stored values |
| `weapon_rental_fee`, `afterparty_fee` (+ `_early`) | superseded by extra items | as above |

**`amount_tolerance_percent` stays in the console** — it is a reconciliation knob, not a tournament parameter — and moves into the payments phase's own panel. `output_sheet_url` moves to Setup `OTHER`. **`ParamPanel.tsx` is then deleted.**

**The two publish-checklist bugs close as a consequence**: `deposit_amount` and `legacy_fixed_fees_block_eur` both attribute to `PAYMENTS`, and both now have a field there. A tournament already carrying legacy fees on a EUR-priced setup — publish-blocked with nothing left to edit — gets a clear action offered only while that condition holds.

Not in scope: any change to what these parameters mean or how the backend reads them. Every field already patches through `updateTournament`; this change moves where they are edited.

## Capabilities

### Modified Capabilities
- `setup-navigation`: seven tabs instead of six, the reallocation of sections across them, and the corrected attribution of publish-blocking items to the tabs that now resolve them.
- `tournament-admin`: which tournament parameters the organizer configures and where, the payment mode as an explained choice rather than a bare list, the timeline's hints and their fallbacks, and the parameters that become fixed or organizer-invisible.
- `etl-console`: the phase general-rules panel narrows to genuine operation parameters, so it no longer carries tournament configuration.

## Impact

**Frontend** (`frontend/src/`): new `setup/PaymentModeSection.tsx`, `setup/TimelineSection.tsx`, `setup/LegacyFeesSection.tsx`; `setup/shared.tsx` (`SETUP_TABS` gains `timeline`, `MISSING_TAB` gains `deposit_amount` and keeps `legacy_fixed_fees_block_eur` now that the field exists, `SECTION_ORDER`); `SetupPanel.tsx` (the new tab panel and sections); `setup/DisciplinesSection.tsx` (composition deadline leaves); `setup/IdentitySection.tsx` (registration window leaves, tournament date stays); `PaymentsPanel.tsx` or its rail neighbour (gains the tolerance); `Console.tsx` (`ParamPanel` removed from the rail); `ParamPanel.tsx` **deleted**; `api.ts`; `i18n/{en,cs}.json`.

**Backend**: none required. Every affected field is already writable through `TournamentUpdate`, and `expiry_grace_hours` keeps its column and its 48-hour default.

**Design constraints**: `CLAUDE.md` / `openspec/squire-design-spec.md` are binding — no gradients, shadows, radii above 2px, emoji, spinners, hex outside `tokens.css`, no Title Case in system copy, and the option group must not introduce a second saturated colour.

**Verification**: `npm run lint` (`tsc -b --noEmit`), `npm run build` and `npm run test` (vitest — `locale-parity.test.ts` covers the cs/en parity this change's new strings must keep), plus driving Setup for what a test cannot see. `pytest` should be unaffected and is run to confirm it.
