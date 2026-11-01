## 1. The kind

- [x] 1.1 Add `Tournament.is_event` and expose it on `TournamentOut` and the list payload
- [x] 1.2 Add `Registration.items_only`, and make `fully_queued` answer false for it (design D4)
- [x] 1.3 Test: empty registrations stay vacuously queued, and team-only records are tournaments

## 2. Completeness

- [x] 2.1 Drop `MISSING_DISCIPLINES` from `setup_missing`, keeping the price check for disciplines that exist
- [x] 2.2 Skip `deposit_amount` and `payment_feed` while `is_event`
- [x] 2.3 Test publish, and removal of an unreferenced and a referenced last discipline
- [x] 2.4 Check adding a discipline to a published event: a new discipline with no price is held to completeness, and confirm the Setup path can supply it in one save

## 3. Registration, pricing and payment

- [x] 3.1 Add `items_stand_alone` to `selection_total` and the discount-code breakdown guard, and pass it from reprice, registration and preview (design D3)
- [x] 3.2 Rework the guards in `register`, `amend` and the preview around the kind and `items_only`; rename the refusal `nothing_selected` and map it in the frontend
- [x] 3.3 Audit every reader of `payment_mode` and open the ordinary window for `items_only` (design D5)
- [x] 3.4 Send `items_only` through ordinary expiry in `scheduler.py` past `settled_seating`
- [x] 3.5 Test the spec scenarios: billing, preview parity, queued items still zero, both stored modes, expiry, late payment, discipline added afterwards, amendment

## 4. Console and public page

- [x] 4.1 Drop Queue and Import from `phasesFor` on an event, and hide hand entry
- [x] 4.2 Refuse hand entry and import on the server for an event, not only in the UI
- [x] 4.3 Omit the Entrants tab and seat counts on an event's detail and card
- [x] 4.4 Confirm the register form, Setup sections and preview render with no disciplines and items only

## 5. Exports

- [x] 5.1 Test the fencer list, item tables and Souhrn with items-only registrations
- [x] 5.2 Test Příjmy and journal reconciliation with an items-only registration
- [x] 5.3 Test a JSON export round trip of an event with registrations

## 6. Wording

- [x] 6.1 Add the context helper in the frontend and the variant helper for mail in the backend (design D6)
- [x] 6.2 Change text not about one record to the event term in `cs.json` and `en.json`
- [x] 6.3 Give every string reachable on an event its `_event` variant, covering Setup, publish, console, detail, payments and mails; verify by scanning rendered event pages and mails for "turnaj" / "tournament"
- [x] 6.4 Check the copy against the design prohibitions, then run the locale parity test

## 7. Checks

- [x] 7.1 `uv run ruff check .`, `uv run basedpyright` and scoped pytest for `tests/payments`, `tests/registration`
- [x] 7.2 `npm run typecheck`, `npm run check`, `npm test`, `npm run build`
- [x] 7.3 Drive a full event in the running app: create, add a seminar, publish, register, pay
