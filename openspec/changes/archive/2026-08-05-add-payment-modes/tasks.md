## 1. Model and migration

- [x] 1.1 Add `PaymentMode` StrEnum to `backend/app/models.py` — `IMMEDIATE = "immediate"`, `DEPOSIT = "deposit"`, `RESERVATION = "reservation"` — with a docstring stating that the mode decides how a seat is held, and that `immediate` is the pre-mode behaviour
- [x] 1.2 Add to `Tournament`: `payment_mode` (default `IMMEDIATE`), `seating_deadline: date | None`, `deposit_amount: int | None`, `deposit_amount_eur: int | None`, `seating_settled_at: datetime | None`. Comment `seating_deadline` with the fallback chain and `seating_settled_at` with why it is one-shot (Decision 6)
- [x] 1.3 Alembic revision adding the five columns, defaulting `payment_mode` to `immediate` and leaving `reservation_validity_days` values untouched (Decision 9)
- [x] 1.4 Test: an existing tournament loads as `immediate` with no deposit, no seating deadline, and an unchanged payment window

## 2. Seating deadline resolution

- [x] 2.1 Add `seating_deadline_for(tournament) -> date` to `backend/app/setup.py`, next to `registration_availability`: returns `seating_deadline`, else `registration_closes`, else `tournament.date` (Decision 7). No caller spells the chain out again
- [x] 2.2 Add `seating_has_settled(tournament, today) -> bool` in the same place — `seating_settled_at is not None` **or** the resolved deadline has passed (Decision 6a). Both disjuncts: the stamp alone leaves the gap between the deadline and the next tick, the deadline alone ignores an early manual settlement
- [x] 2.3 Test both helpers across all four fallback combinations, plus: settled-by-stamp before the deadline is settled; deadline passed with no stamp is settled

## 3. Registration: mode-dependent windows and post-deadline entry

- [x] 3.1 In `routers/registrations.py::register`, set `expires_at` per mode: `registered_at + reservation_validity_days` for `IMMEDIATE`/`DEPOSIT`, `None` for `RESERVATION`; substitutes keep `None` as today (Decision 2)
- [x] 3.2 In the same function, force `as_substitute = True` for every entry and `waitlisted = True` for every team when `seating_has_settled(...)`, regardless of capacity
- [x] 3.3 Have `pricing.registration_total` continue to exclude substitute placements — no change, but assert it in a test for a post-deadline registration (total is zero)
- [x] 3.4 Tests: reservation-mode registration has no `expires_at` but holds a seat in `taken_seats`; immediate and deposit modes open a window; post-deadline registration is queued with free seats available and owes nothing

## 4. Seating settlement pass

- [x] 4.1 Add `settle_seating(session, tournament) -> int` to `backend/app/scheduler.py`, shaped like `process_composition_reminders`, as a pure pass with no trigger condition of its own so the scheduler and the organizer endpoint can share it. It stamps `seating_settled_at` and demotes; the caller decides when
- [x] 4.2 For each `RESERVED` registration in the tournament: set every `RegistrationDiscipline.is_substitute = True`, every `Team.waitlisted = True`, `expires_at = None`, and add a `PaymentEvent(kind="seating_demoted")`
- [x] 4.3 Set `tournament.seating_settled_at` at the end of the pass and commit
- [x] 4.4 Call it from `run_tournament_tick` **before** `process_expiries` (Decision 1), guarded by "not yet stamped and the deadline has passed", with a comment stating why the order is load-bearing
- [x] 4.5 Add `POST /api/tournaments/{slug}/settle-seating` in the console router, guarded by `require_console_access`: refuse with a clear reason when `seating_settled_at` is already set, otherwise run the same pass and return the number demoted. Available in every mode, including `immediate`, where it demotes nobody but still stamps
- [x] 4.6 Tests: unpaid seated registration is demoted and keeps its VS; paid registration untouched; deposit-paid-balance-unpaid is demoted with its credit intact; teams are waitlisted with their registration; capacity is freed; three registrations end up in the queue in registration order via `queue_position`; a second tick demotes nobody; a promotion between two ticks survives; `immediate` mode demotes nobody but stamps; manual settlement before the deadline demotes and stamps, and the later deadline tick then does nothing; settling twice is refused; a non-organizer gets 403

## 5. Reminders re-anchored

- [x] 5.1 Rewrite the `process_reminders` predicate: drop `expires_at IS NOT NULL` as the not-a-substitute proxy and filter on substitute status directly, reusing the fully-queued predicate from `emails.py:98` (every entry substitute **and** every team waitlisted)
- [x] 5.2 Anchor the due date to `expires_at - reminder_day days` where a window is running, and to `seating_deadline_for(...) - reminder_day days` where it is not (Decision 2)
- [x] 5.3 Tests: reservation-mode registration with no window is reminded before the seating deadline; immediate-mode registration is reminded before its window; a fully queued registration is never reminded; a deposit-paid registration is reminded about its balance before the deadline

## 6. Matching: the deposit threshold

- [x] 6.1 In `matching.py`, after crediting a payment: when mode is `DEPOSIT`, the registration is `RESERVED`, `expires_at` is not None, and the credited amount has reached `deposit_amount` in that currency lane, set `expires_at = None` and add a `PaymentEvent(kind="deposit_settled")`
- [x] 6.2 Keep the existing full-settlement path unchanged — reaching the total still sets `PAID`
- [x] 6.3 Tests: credit equal to the deposit closes the window and the registration survives past the old expiry; credit below the deposit leaves the window running and it still expires; credit reaching the full total still marks paid; the EUR lane behaves the same against `deposit_amount_eur`

## 7. Promotion and return to queue

- [x] 7.1 Clamp the window in `admit_substitute`: `expires_at = min(now + reservation_validity_days, end of tournament.date)` (Decision 8)
- [x] 7.2 Add `POST /registrations/{registration_id}/return-to-queue/{discipline_slug}` in `routers/registrations.py`, guarded by `require_console_access`: refuse when the registration is `PAID` (directing to cancellation), otherwise set `is_substitute = True`, clear `expires_at`, add a `PaymentEvent`, and return the registration
- [x] 7.3 Add `ReturnToQueue` handling to `schemas.py` if a response shape beyond `RegistrationOut` is needed; reuse `RegistrationOut` otherwise
- [x] 7.4 Tests: promotion three days before the tournament clamps the window; return-to-queue frees the seat and clears the window; returning a paid registration is refused; a returned registration's `queue_position` sits correctly between earlier and later substitutes
- [x] 7.5 In `process_expiries`, a lapsed payment window on a tournament whose seating has settled returns the registration to the queue instead of expiring it (Decision 8, owner-confirmed 2026-08-04): entries substitute, teams waitlisted, `expires_at` cleared, state stays `RESERVED`, distinct audit event. Before settlement, expiry is unchanged. Tests both sides of the stamp

## 8. Validation

- [x] 8.1 In `schemas.py`, constrain `reservation_validity_days` to `ge=2, le=7` on write only, leaving stored values alone
- [x] 8.2 Add `reminder_day < reservation_validity_days` validation with a message naming both values (the unimplemented `harden-payment-matching` 4.4, now mandatory)
- [x] 8.3 Add `seating_deadline <= registration_closes` (falling back as in 2.1) with a message naming both dates
- [x] 8.4 Require `deposit_amount > 0` when mode is `DEPOSIT`, and `deposit_amount_eur` alongside it when the tournament shows EUR; ignore both in other modes
- [x] 8.5 Add the deposit amounts to the setup completeness check on the same terms as other prices
- [x] 8.6 Regenerate `frontend/src/constraints.ts` from the backend constraints
- [x] 8.7 Tests for each rejection, asserting the message names the conflicting values

## 9. Frontend: setup

- [x] 9.1 Teach `ParamPanel.tsx` a `select` field type (it currently handles `number`, `date`, `text` only) and add the payment-mode selector
- [x] 9.2 Show `seating_deadline` in the panel with help text distinguishing it from the registration close in one line (the main usability risk — see design Risks)
- [x] 9.3 Show the deposit amounts only in deposit mode, in the same shape as other prices (local + EUR where the tournament prices in EUR)
- [x] 9.4 Add `payment_mode`, `seating_deadline`, `deposit_amount`, `deposit_amount_eur` to the tournament types in `api.ts`
- [x] 9.5 Czech and English strings for the mode names, the deadline, the deposit, and every new validation message

## 10. Frontend: queue view

- [x] 10.1 Add `admitSubstitute(slug, registrationId, disciplineSlug)` and `returnToQueue(...)` to `api.ts` — `admit_substitute` currently has no caller anywhere in the frontend
- [x] 10.2 Add a queue view to `Console.tsx` (or a `QueuePanel.tsx` under a per-panel directory if `Console.tsx` is near its size seam): per discipline, the free places and the queued registrations in order with fencer, registration time and position
- [x] 10.3 Promotion action on each queued entry, return-to-queue on each seated one, each reporting its own failure
- [x] 10.4 State plainly when a queue is empty rather than hiding the discipline
- [x] 10.5 Add `settleSeating(slug)` to `api.ts` and a settle-seating action on the queue view, using the existing `.modal-backdrop` / `.modal` pattern to confirm: state how many registrations will be demoted and that it cannot be undone. Hide or disable it once `seating_settled_at` is set
- [x] 10.6 Czech and English strings; verify against `CLAUDE.md` / `squire-design-spec.md` — no radii above 2px, no shadows, no emoji, no spinners, no hex outside `tokens.css`

## 11. Verification

- [x] 11.1 `pytest` in `backend/` — full suite green, with attention to `test_registrations.py`, `test_scheduler.py`, and any test asserting the old `expires_at`-always-set assumption
- [x] 11.2 `npm run lint` (`tsc -b --noEmit`) and `npm run build` in `frontend/`
- [x] 11.3 Drive each mode end to end in the running app: immediate (register, let the window lapse, seat freed); deposit (register, pay the deposit, window closes, miss the deadline, demoted); reservation (register free, miss the deadline, demoted, organizer promotes someone from the queue, they pay); and one manual settlement before a deadline, confirming later registrations join the queue
- [x] 11.4 Confirm a tournament created before this change behaves exactly as it did — full amount at registration, unchanged window, no settlement pass
