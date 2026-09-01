## Why

The payment-matching backend hardened in `harden-payment-matching` (groups 2–9, 11, 12) exposes candidate VS detection, outstanding balances, manual linking, holding-payment expiry events and payment-link rules — and almost none of it is reachable from the console. `PaymentsPanel.tsx` renders only the `flagged` subset of transactions; `POST /payments/link` has no caller anywhere in the frontend. An organizer facing a transfer with no VS, a part-paid reservation, or money stranded on an expired reservation has no screen that shows it, let alone resolves it.

That change's Group 10 was written against wrong premises (it names `MatchDialog.tsx` / `MatchPanel.tsx`, which belong to the unrelated hemaratings fighter-identity feature) and is replanned here as its own scoped piece of work.

## What Changes

- **New manual-link modal** (`LinkDialog.tsx`), opened from an unmatched transaction row, pre-filling the `candidate_vs` the backend already computes as one-click choices, accepting hand-typed VS, and supporting the one-payer-covers-several-registrations split that `LinkIn` already takes. First frontend caller of `POST /payments/link`.
- **New unmatched-transaction rail card** (`UnmatchedPanel.tsx`): the `unmatched` half of `GET /payments/unmatched`, which the existing panel filters away.
- **`PaymentsPanel.tsx` narrows to its actual job** — the flagged queue — and is renamed `FlaggedPanel.tsx` to stop the name implying it covers payments as a whole.
- **New expired-holding-payment rail card** (`ExpiredHoldingPanel.tsx`) listing reservations that expired while holding credited money, backed by a **new read endpoint** `GET /api/tournaments/{slug}/payments/expired-holding`. Nothing currently queries `PaymentEvent.kind == "expired_holding_payment"`, so this money is invisible today.
- **New payment-links rail card** (`PaymentLinksPanel.tsx`) listing active `payment_link` rules with auto-created ones marked, and removal via the existing rules API. These rules replay through `_apply_opaque`, so they emit no audit rows and never appear in the rail's edits log — today a link, once made, cannot be seen or undone from the console.
- **Outstanding balance becomes a sheet column**: `sheet.base_rows` gains `outstanding_amount` (and the EUR sibling) from the existing `Registration.outstanding_cents` properties, `SheetRow` gains the fields, and the Payments phase gains an `outstanding` column.
- Czech and English strings for every new surface.

Not in scope: any change to matching, crediting, expiry or refund behaviour — this change only surfaces and resolves what the backend already decides.

## Capabilities

### New Capabilities
- `payments-console`: the organizer's payment-resolution surface — the flagged, unmatched, expired-holding and payment-link views, the manual-link dialog, and the read endpoint that backs the expired-holding view.

### Modified Capabilities
- `etl-console`: the Payments phase's fencer-table columns gain the outstanding balance, so a part-paid reservation is legible in the table rather than only in the fencer's own view.

## Impact

**Frontend** (`frontend/src/`): `PaymentsPanel.tsx` → `FlaggedPanel.tsx`; new `UnmatchedPanel.tsx`, `ExpiredHoldingPanel.tsx`, `PaymentLinksPanel.tsx`, `LinkDialog.tsx`; `Console.tsx` (four rail cards on the payments phase, `PHASE_COLUMNS.payments`, `CellDisplay` money formatting); `api.ts` (`linkTransaction`, `expiredHolding`, `rules`, `Transaction.candidate_vs`, `SheetRow.outstanding_amount`); `i18n/{en,cs}.json`; `index.css` if the modal or the chips need anything beyond existing classes.

**Backend** (`backend/app/`): `routers/payments.py` (new expired-holding endpoint), `schemas.py` (its response model), `sheet.py` (two more row fields). No model, migration, or matching-logic change.

**Design constraints**: all four cards and the modal are subject to `CLAUDE.md` / `openspec/squire-design-spec.md` — no gradients, shadows, radii > 2px, emoji, spinners, or hexes outside `tokens.css`; the modal follows the existing `.modal-backdrop` / `.modal` pattern.

**Verification**: `npm run lint` (`tsc -b --noEmit`), `npm run build`, and `npm test` (`vitest run`), alongside driving the console; the new endpoint and sheet fields are covered by `backend/tests/`.

> Corrected by `add-mobile-fencer-layout`: this line previously stated the frontend had no test runner. `frontend/package.json` defines `"test": "vitest run"` and `frontend/src/` holds two dozen `.test.ts(x)` files, several of them covering this console.
