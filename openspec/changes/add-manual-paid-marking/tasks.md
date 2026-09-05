Depends on `regroup-tournament-settings` and everything under it: the
configuration this serves — Squire handling no payments — only became a first-
class answer there, and the switch this change adds a line to lives in that
surface.

## 1. Backend: the mark

- [ ] 1.1 Endpoint on the **registrations** router, not the payments router: every path of the latter is gated on the payments setting being on, which is exactly the case this serves. Guard it with `require_console_access` as its neighbours are
- [ ] 1.2 Refuse it where Squire handles the tournament's payments, with a stated reason — the mirror of `bank.require_payments_enabled`, and for the same reason: the state has one writer per tournament (design D2)
- [ ] 1.3 Set `state` to `PAID` and **leave `amount_paid_cents` and `amount_paid_eur_cents` untouched** (design D1). Assert this in the test rather than trusting it: writing the outstanding amount into the paid counter is the obvious wrong move and it would pass a state-only assertion
- [ ] 1.4 The reverse action returns the registration to `RESERVED`. Confirm what `paid_at` should do in both directions — it is stamped by the credit path today, and a mark with no money behind it either sets it or deliberately does not; decide and say which in the code
- [ ] 1.5 Two `PaymentEvent` kinds for marking and unmarking, carrying the acting organizer's identity in the detail (design D3). No new table
- [ ] 1.6 Refuse on a registration that is cancelled or expired rather than reviving it: this marks money received, and it is not the route back from a state the lifecycle chose

## 2. Backend: what reads it

- [ ] 2.1 The participant list marks a settled entrant confirmed where Squire collects nothing, and marks nobody unconfirmed (design D5). The list already branches on whether a payment state is guaranteed; this is a third answer in that branch, not a fourth branch
- [ ] 2.2 Confirm `sheet.py` needs nothing: its row carries `paid` from `registration.state` already (`sheet.py:178`)
- [ ] 2.3 Carry the count of hand-settled registrations wherever the settings surface can read it, for the switch warning in section 4
- [ ] 2.4 Tests: the mark and its reverse; the refusal where Squire collects; the counters untouched; the audit events and their actor; a cancelled registration refused; the participant list under all three of — Squire collects, collects nothing with no marks, collects nothing with some marks

## 3. Frontend: the column

- [ ] 3.1 Add the settled column to the Fencers phase in `PHASE_COLUMNS`, offered only where Squire handles no payments (design D4). `PHASE_COLUMNS` and `editableHere` are static tables today and gain their first dependence on a tournament setting — thread it deliberately rather than reaching for the detail from inside a helper
- [ ] 3.2 The cell toggles, calls the endpoint and refreshes the sheet through the console's existing reload signal
- [ ] 3.3 State what the mark means where it could mislead: the organizer's word that the money arrived, and that Squire has received nothing itself. A hand-settled row reads as paid while still showing what it is owed, and a reader who takes that for a fault is misreading the one true thing about it
- [ ] 3.4 Confirm the column is absent where Squire handles the payments, and that the Payments phase there is unchanged
- [ ] 3.5 Tests: the column appears and disappears with the setting; the toggle posts and refreshes; the failure path states itself

## 4. Frontend: the switch warning

- [ ] 4.1 Where the settings surface switches a tournament to Squire handling its payments, state how many registrations are marked paid with no money behind them (design, Risks). Reconciliation will find nothing to match them against, and the organizer should learn it before rather than from the roster
- [ ] 4.2 Do not offer to unmark them. Silently undoing is wrong and offering needs a screen; the count is what this change owes (design, Open Questions)

## 5. Localization

- [ ] 5.1 English strings: the column and its heading, the action and its reverse, what the mark means, the refusal, the switch warning
- [ ] 5.2 Czech in the same pass; `locale-parity.test.ts` covers the drift, and `identityLabels.test.ts` is the reminder that parity alone does not prove a key a component asks for exists

## 6. Verification

- [ ] 6.1 `pytest` and `ruff check .` clean
- [ ] 6.2 `vitest`, `npm run lint`, `npm run build` clean
- [ ] 6.3 **Look at the Fencers phase on a tournament that collects nothing.** A column whose presence follows a setting is a layout claim, and this one has to read as an action rather than as a value that happens to be editable
- [ ] 6.4 Look at the public list of such a tournament with some entrants marked and some not, and confirm the unmarked read as entrants rather than as people who have not paid. That distinction is the whole of D5 and it is only visible on the page
