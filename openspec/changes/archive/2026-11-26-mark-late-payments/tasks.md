## 1. Backend

- [x] 1.1 In `sheet.py`, read the tournament's flagged transactions with reason `expired_outside_grace` / `expired_seat_taken` and no live credit once per projection, resolve each by `matching.effective_vs` to its registration (D2)
- [x] 1.2 Add `late_payment` to the row of an expired registration: the most recent flagged payment (table `uncredited`, transaction id, amount, currency, day, count), else the latest live credit entry (table `credited`, `(source_kind, source_id)`, `held_amount`, currency, expiry day) (D1, D3)
- [x] 1.3 Add the field to the row schema in `schemas.py` — none to add: sheet rows are untyped `Row` dicts, as `held_amount` already is
- [x] 1.4 Tests in `tests/payments`: a flagged late payment lands on its expired row; held credit points at its latest credit; the flagged one wins over held credit; a reinstated registration carries no `late_payment`; an ordinary expiry carries none

## 2. Frontend

- [x] 2.1 `api.ts`: type `late_payment` on `SheetRow`
- [x] 2.2 `.stamp-muted` modifier in `index.css` using `--ink-faded` (D5); `PaidStamp` takes an optional `muted`; the stamp itself is `LateStamp.tsx`, the marked row `payments/ArrivedRow.tsx`
- [x] 2.3 `StateBadge`: muted "Pozdě" stamp for an expired row with `late_payment`, tooltip per case and count, replacing "Vypršela s platbou"; a button only when an `onLate` handler is passed (D4)
- [x] 2.4 `StateCell` on the Payments phase passes `onLate`; `Console` holds `arrivedAt`, opens the right money tab, clears it when `openTab` changes (D6)
- [x] 2.5 `UncreditedTable` and `CreditedTable` take `arrivedAt`, mark the row (`aria-current`, `--paper-shade`) and scroll it into view once
- [x] 2.6 `cs.json` / `en.json`: label "Pozdě" / "Too late", tooltips for flagged (with count) and held credit; drop the now-unused `expiredHolding.label` if nothing else reads it
- [x] 2.7 Component tests: stamp drawn and muted, never the paid stamp; pressing it opens the named table with the row marked

## 3. Checks

- [x] 3.1 `uv run ruff check .` and `uv run basedpyright` in `backend/`; scoped `pytest tests/payments`
- [x] 3.2 `npm run typecheck`, `npm run check`, `npm test` in `frontend/`
- [x] 3.3 By hand in the browser: an expired registration with a flagged late payment, stamp → Nepřipsané on the row, reinstate, stamp gone
