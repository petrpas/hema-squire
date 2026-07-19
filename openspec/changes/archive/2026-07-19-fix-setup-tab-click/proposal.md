# Fix Setup Tab Click

## Why

The Setup tab (step 0) in the console phase stepper is not clickable: once the organizer leaves Setup, they cannot navigate back to it. This breaks the etl-console spec's phase-tab switching requirement for the Setup phase.

Root cause (found by inspection): `.step-slot:first-child { flex: 0 }` in `frontend/src/index.css` resolves to `flex-basis: 0%`, which together with `min-width: 0` collapses the first stepper slot to zero width. The Setup button overflows the empty slot and the second slot's connector line is painted over it, intercepting all clicks.

## What Changes

- Correct the first stepper slot's flex sizing so it takes its content width (`flex: none` instead of `flex: 0`), restoring the Setup tab's hit area.
- Visual check of the stepper alignment across all seven tabs after the fix.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `etl-console`: no behavioral change of intent — the existing "Phase-tabbed fencer table" requirement gains an explicit scenario that the Setup tab is reachable from every phase, turning this regression into a stated acceptance criterion.

## Impact

- `frontend/src/index.css` (one rule). No backend, API, or data changes.
