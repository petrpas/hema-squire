## 1. Backend: the predicate

- [x] 1.1 **Lives in `app/setup.py`, not `scheduler.py`** (deviation from the written task): `admit_substitute` in `routers/registrations.py` has to ask the same predicate, and a router importing `scheduler` would drag `bank`, `matching` and `emails` into its import graph for one boolean. `setup.py` already holds the lifecycle's other predicates — `seating_deadline_for`, `seating_has_settled`, `registration_availability` — and both callers already import it, so this adds no import edge at all. Added `dormancy_cause(tournament, registration) -> str | None`, returning `None` where the clocks run and otherwise the reason they do not, from a closed set of two: the payments feature being off, and the registration having been issued from an imported row (`Registration.clocks_dormant`). A pure function over values every pass already holds — no query, no session, no model attribute (design D1)
- [x] 1.2 Added the companion as `clocks_run(...) -> bool` — the positive reading, which is what the filtering call sites want. It is one line delegating to `dormancy_cause`, so there are not two definitions to keep in step
- [x] 1.3 Document on the function that it is the single decision point, that a third cause is expected from the automatic/manual cut, and that a condition added to a pass instead of here is the defect this change removed
- [x] 1.4 Unit tests for the function alone, with no scheduler and no database: payments off yields the payments cause; `clocks_dormant` yields the origin cause; both at once yields one stated cause deterministically; neither yields `None`

## 2. Backend: the four passes consult it and nothing else

- [x] 2.1 `process_reminders`: drop the `clocks_dormant.is_(False)` term from the query and filter the loaded candidates through the predicate alongside the existing `fully_queued` and `_reminder_due` tests. The pass already builds `due` in a comprehension, so this is one more clause in a filter that exists
- [x] 2.2 `process_expiries`: drop the `clocks_dormant.is_(False)` term and filter `overdue` through the predicate before either branch. Keep the `expires_at` conditions in SQL — that is a different question and belongs where it is
- [x] 2.3 Extract the demotion selection into one function returning the registrations settlement would move, filtered by the predicate; have `pending_demotions` count what it returns and `settle_seating` act on it (design D5). Delete the twinned comments asking future editors to keep the two queries aligned — the alignment is now structural
- [x] 2.4 `settle_seating` stamps `seating_settled_at` unconditionally, outside the demotion loop, so a tournament with nothing to demote still closes its seating (design D3). Confirm `settle_seating_if_due` needs no change: its deadline test is about the tournament, not about any registration
- [x] 2.5 Remove the `if tournament.feature_payments:` branch around expiry and reminders in `run_tournament_tick`, so the passes always run and always select nothing on a payments-off tournament (design D4). Leave the Fio polling branch's `feature_payments` check alone — it is about calling the bank, not about a registration
- [x] 2.6 `admit_substitute` (`routers/registrations.py:881`) now asks `setup.clocks_run` rather than reading `clocks_dormant` directly. `clocks_dormant` is now referenced in exactly one place outside the model — inside the predicate — which is the property that makes this change hold

## 3. Backend: the regression this change exists for

- [x] 3.1 `tests/test_dormancy.py`, eleven tests. The reproduction as a test: a payments-off tournament with two seated registrations and `registration_closes` set to yesterday, one `run_tournament_tick`. Assert on the **substitute placements**, not on `state` — `state` stays `RESERVED` through a demotion, which is what hid this for as long as it hid. The working probe is in the session scratchpad
- [x] 3.2 Assert the same tick reports `seating_demoted == 0` and that `seating_settled_at` **is** stamped, so the fix is "demoted nobody", not "skipped settlement" (design D3)
- [x] 3.3 A fencer registering for that tournament after the deadline lands in the substitute queue — seating closed even though nothing moved
- [x] 3.4 A tournament every one of whose registrations is dormant by origin settles the same way: nothing demoted, seating stamped
- [x] 3.5 `pending_demotions` and the settlement agree on a mixed tournament — four unpaid seated registrations that are not dormant and six that are; the count states four and settling demotes those four

## 4. Backend: proving a collecting tournament did not change

This is the load-bearing section (design, Risks). A test that the predicate returns the right value proves much less than the lifecycle producing the same events it produced before.

- [x] 4.1 **946 passed with no test edited.** The whole suite ran green against the rewritten passes before a single new test was written, which is the evidence this section exists for: no collecting tournament changed behaviour
- [x] 4.2 Add an end-to-end pass over a payments-on tournament exercising a reminder, an expiry, a mixed demotion and a settlement in one run, asserting the events, the mail and the placements. Where an equivalent already exists, extend it rather than writing a second
- [x] 4.3 `test_payments_off.py:159` now asserts the placements as well as the state, with a comment saying why the state assertion was insufficient — a demoted registration is still `RESERVED`, so the old assertion passed throughout the bug's life

## 5. Specs and verification

- [x] 5.1 No migration and no schema change (design D2). Confirm this holds at the end — if a column was added, a decision was taken that the design did not make
- [x] 5.2 `pytest` 957 passed (946 + 11 new), `ruff check .` clean
- [x] 5.3 No frontend work needed. `QueuePanel.tsx:170` renders `queue.pending_demotions` straight from the endpoint; there is no second selection in the client
- [x] 5.4 **No live tournament was exposed.** Read-only survey of `backend/hema_squire.sqlite`: `na-duel-2026` (payments on, dated 2026-05-23, already past so the scheduler no longer selects it) and `ttt-2027` (payments on). Both collect, so neither could have been demoted by this. No repair is needed
