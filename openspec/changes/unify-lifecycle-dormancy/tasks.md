## 1. Backend: the predicate

- [ ] 1.1 Add `dormancy_cause(tournament, registration) -> str | None` beside the lifecycle in `backend/app/scheduler.py`, returning `None` where the clocks run and otherwise the reason they do not, from a closed set of two: the payments feature being off, and the registration having been issued from an imported row (`Registration.clocks_dormant`). A pure function over values every pass already holds — no query, no session, no model attribute (design D1)
- [ ] 1.2 Add the companion `is_dormant(tournament, registration) -> bool` only if call sites read better for it; otherwise every caller tests the cause against `None` and there is one function rather than two that must agree
- [ ] 1.3 Document on the function that it is the single decision point, that a third cause is expected from the automatic/manual cut, and that a condition added to a pass instead of here is the defect this change removed
- [ ] 1.4 Unit tests for the function alone, with no scheduler and no database: payments off yields the payments cause; `clocks_dormant` yields the origin cause; both at once yields one stated cause deterministically; neither yields `None`

## 2. Backend: the four passes consult it and nothing else

- [ ] 2.1 `process_reminders`: drop the `clocks_dormant.is_(False)` term from the query and filter the loaded candidates through the predicate alongside the existing `fully_queued` and `_reminder_due` tests. The pass already builds `due` in a comprehension, so this is one more clause in a filter that exists
- [ ] 2.2 `process_expiries`: drop the `clocks_dormant.is_(False)` term and filter `overdue` through the predicate before either branch. Keep the `expires_at` conditions in SQL — that is a different question and belongs where it is
- [ ] 2.3 Extract the demotion selection into one function returning the registrations settlement would move, filtered by the predicate; have `pending_demotions` count what it returns and `settle_seating` act on it (design D5). Delete the twinned comments asking future editors to keep the two queries aligned — the alignment is now structural
- [ ] 2.4 `settle_seating` stamps `seating_settled_at` unconditionally, outside the demotion loop, so a tournament with nothing to demote still closes its seating (design D3). Confirm `settle_seating_if_due` needs no change: its deadline test is about the tournament, not about any registration
- [ ] 2.5 Remove the `if tournament.feature_payments:` branch around expiry and reminders in `run_tournament_tick`, so the passes always run and always select nothing on a payments-off tournament (design D4). Leave the Fio polling branch's `feature_payments` check alone — it is about calling the bank, not about a registration
- [ ] 2.6 Confirm `admit_substitute` (`routers/registrations.py:881`) still reads correctly: it guards the one place a due date is set, and its condition should now be the shared predicate rather than `clocks_dormant` directly, so a payments-off promotion is covered by the same rule

## 3. Backend: the regression this change exists for

- [ ] 3.1 The reproduction as a test: a payments-off tournament with two seated registrations and `registration_closes` set to yesterday, one `run_tournament_tick`. Assert on the **substitute placements**, not on `state` — `state` stays `RESERVED` through a demotion, which is what hid this for as long as it hid. The working probe is in the session scratchpad
- [ ] 3.2 Assert the same tick reports `seating_demoted == 0` and that `seating_settled_at` **is** stamped, so the fix is "demoted nobody", not "skipped settlement" (design D3)
- [ ] 3.3 A fencer registering for that tournament after the deadline lands in the substitute queue — seating closed even though nothing moved
- [ ] 3.4 A tournament every one of whose registrations is dormant by origin settles the same way: nothing demoted, seating stamped
- [ ] 3.5 `pending_demotions` and the settlement agree on a mixed tournament — four unpaid seated registrations that are not dormant and six that are; the count states four and settling demotes those four

## 4. Backend: proving a collecting tournament did not change

This is the load-bearing section (design, Risks). A test that the predicate returns the right value proves much less than the lifecycle producing the same events it produced before.

- [ ] 4.1 Run the existing suite unchanged and expect no edits to `test_scheduler.py`, `test_payment_e2e.py`, `test_registrations.py`, `test_issuing.py` or the seating tests. Any test that needs changing is a behaviour change to explain, not a test to fix
- [ ] 4.2 Add an end-to-end pass over a payments-on tournament exercising a reminder, an expiry, a mixed demotion and a settlement in one run, asserting the events, the mail and the placements. Where an equivalent already exists, extend it rather than writing a second
- [ ] 4.3 `test_payments_off.py:159` currently asserts only that the registration is still `RESERVED`, which was true while it was being demoted. Strengthen it to assert the placements too, and note in the docstring why the state assertion was insufficient

## 5. Specs and verification

- [ ] 5.1 No migration and no schema change (design D2). Confirm this holds at the end — if a column was added, a decision was taken that the design did not make
- [ ] 5.2 `pytest` in `backend/` and `ruff check .` clean
- [ ] 5.3 No frontend work expected. Confirm the console's settle confirmation reads its count from the endpoint rather than computing one of its own; if it computes, that is a second selection and belongs in 2.3
- [ ] 5.4 Report to the owner which live tournaments have payments off and a seating deadline already past — those may be carrying registrations demoted for a reason that was never valid. This change stops the cause; the repair, if any is needed, is the owner's call and not part of it
