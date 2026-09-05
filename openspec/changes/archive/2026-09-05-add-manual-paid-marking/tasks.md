Depends on `regroup-tournament-settings` and everything under it: the
configuration this serves — Squire handling no payments — only became a first-
class answer there, and the switch this change adds a line to lives in that
surface.

## 1. Backend: the mark

- [x] 1.1 Endpoint on the **registrations** router, not the payments router: every path of the latter is gated on the payments setting being on, which is exactly the case this serves. Guard it with `require_console_access` as its neighbours are
- [x] 1.2 Refuse it where Squire handles the tournament's payments, with a stated reason — the mirror of `bank.require_payments_enabled`, and for the same reason: the state has one writer per tournament (design D2)
- [x] 1.3 Set `state` to `PAID` and **leave `amount_paid_cents` and `amount_paid_eur_cents` untouched** (design D1). Assert this in the test rather than trusting it: writing the outstanding amount into the paid counter is the obvious wrong move and it would pass a state-only assertion
- [x] 1.4 The reverse returns it to `RESERVED`. **`paid_at` is stamped and cleared**: it answers *when this became paid*, and a mark is when it did; clearing it on the reverse mirrors what unlinking a payment already does (`matching.py:662`). Said in the endpoint's docstring
- [x] 1.5 Two `PaymentEvent` kinds for marking and unmarking, carrying the acting organizer's identity in the detail (design D3). No new table
- [x] 1.6 Refuse on a registration that is cancelled or expired rather than reviving it: this marks money received, and it is not the route back from a state the lifecycle chose

## 2. Backend: what reads it

- [x] 2.1 The participant list marks a settled entrant confirmed where Squire collects nothing, and marks nobody unconfirmed (design D5). The list already branches on whether a payment state is guaranteed; this is a third answer in that branch, not a fourth branch
- [x] 2.2 `sheet.py` needed one thing after all: **`registration_id` on the row.** The row id cannot stand in, because an issued registration takes its *source row's* id — so `reg:<n>` is only sometimes the shape, and the cell addresses the registration itself. Added, null on imported and manual rows
- [x] 2.4 Tests: the mark and its reverse; the refusal where Squire collects; the counters untouched; the audit events and their actor; a cancelled registration refused; the participant list under all three of — Squire collects, collects nothing with no marks, collects nothing with some marks

## 3. Frontend: the boned-out Payments phase

- [x] 3.1 `offeredPhases` stops removing the Payments phase: it is offered on every tournament (design D4). Check what else read that removal — the default phase, the stale-bookmark redirect and the tab bar all consult it
- [x] 3.2 The phase's body branches on who handles the payments. Where Squire does, it is exactly what it is today and untouched. Where it does not, it holds the settled column and nothing else — no queues, no intake card, no tolerance panel, no transaction list. A control that answers a 409 is worse than no control
- [x] 3.3 A second entry in `PHASE_COLUMNS` for the boned-out phase rather than a condition inside the existing one, so a column stays a property of a phase and none has to be read as sometimes present
- [x] 3.4 The cell toggles, calls the endpoint and refreshes the sheet through the console's existing reload signal
- [x] 3.5 State what the mark means where it could mislead: the organizer's word that the money arrived, and that Squire has received nothing itself. A hand-settled row reads as paid while still showing what it is owed, and a reader who takes that for a fault is misreading the one true thing about it
- [x] 3.6 Tests: the phase is offered either way; the boned-out phase holds the mark and none of the panels; the full phase is unchanged; the toggle posts and refreshes; the failure path states itself

## 4. Localization

- [x] 4.1 English strings: the column and its heading, the action and its reverse, what the mark means, the refusal, the switch warning
- [x] 4.2 Czech in the same pass; `locale-parity.test.ts` covers the drift, and `identityLabels.test.ts` is the reminder that parity alone does not prove a key a component asks for exists

## 5. Verification

- [x] 5.1 `pytest` 1016 passed, `ruff check .` clean
- [x] 5.2 `vitest` 341 passed, `npm run lint` and `npm run build` clean
- [x] 5.3 **Partly.** Stood up a throwaway instance — its own database, its own ports — rather than writing a payments-off tournament into the developer's own, and confirmed on screen that the Payments phase is offered, that it carries the line explaining the mark, and that no queue, intake, tolerance or clear panel is drawn. **Did not see the table with rows**: the preview browser was signed in as a fencer, and reaching the console would have meant typing a password into a login form, which I do not do. The cell's own behaviour is covered by `settledCell.test.tsx`, and the end-to-end behaviour was driven against that running server through the API — but the rendered column is the one claim still unseen, and it wants an eye
- [x] 5.4 Verified against the running preview through the API rather than on a page, since no page renders the participant list yet (found in `add-external-registration`). Three entrants, one marked: `Adéla — confirmed`, the other two `status: null`. The mark carries and the absence asserts nothing, which is the whole of D5
