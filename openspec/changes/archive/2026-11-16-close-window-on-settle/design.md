## Context

`derive-balances-from-credits` made "paid" a reading rather than a state. The expiry pass in `scheduler.process_expiries` spares a reserved registration only while `Registration.settled` is true, and selects it on `expires_at <= now` otherwise. Settling never touched `expires_at`, so a paid registration carries its registration-time deadline indefinitely, and the moment the reading flips it is already overdue.

`amendment.py` handles the one flip its authors foresaw: `was_paid and not registration.settled` → `setup.payment_window(tournament, now)`. Five other flips are unhandled (`openspec/payments_gaps.md`, P3): EUR switched off, tolerance tightened, recorded payment removed, transaction credit reversed, waiver revoked. Payment-link removal (`matching.unapply_payment_link`) is a sixth that the audit did not probe but behaves identically.

## Goals / Non-Goals

**Goals:**
- No organizer action that unsettles a registration expires it within a tick.
- A path that unsettles and is not wired up fails safe: the registration owes with no deadline rather than expiring.
- One rule decides the reopened window.

**Non-Goals:**
- Mode-specific windows on reopening (see D2).
- A new mail announcing the debt.
- P4–P7 of the audit.

## Decisions

### D1. The tick closes the window of every reserved, settled registration

At the start of `process_expiries`, before selecting overdue registrations, `scheduler.close_settled_windows` sets `expires_at = NULL` on the tournament's registrations that are `RESERVED`, `settled` and carry a window — selected with the existing SQL `settled` expression and cleared through the ORM.

Why the tick, not each settle site: settling happens in `_settle` (both bank and recorded routes), `grant_waiver`, the tolerance re-decision pass, discount-code repricing, a downward amendment, and implicitly whenever tolerance widens. Clearing at each site repeats D2's mistake of trusting every author to remember. The tick is the only consumer of `expires_at` for expiry, so clearing there is enough, and it also clears the windows of registrations settled before this change — no Alembic migration.

`RESERVED` only: an expired registration's `expires_at` anchors the 48 h grace (`matching.within_expiry_grace`) and must stay.

Alternative considered: stop reading `expires_at` for settled registrations and leave it stored. Rejected — that is today's design; it fails the moment the reading flips.

### D2. One reopening rule, the amendment's

`setup.reopen_window(tournament, registration, was_settled: bool) -> None`: if `was_settled and not registration.settled and clocks_run(tournament, registration) and not registration.fully_queued`, set `expires_at = payment_window(tournament, now)` (which is `None` with payments off) and `reminded_at = None`. The amendment's inline block moves onto it.

The window is the same in every payment mode, as the amendment's and a promotion's already are. A mode-aware rule (no window in `reservation` mode before seating; none in `deposit` mode while the deposit stays covered) would be gentler in two corners but would make reopening differ from the amendment and promotion windows it is meant to share a rule with. Kept out; can follow if a real tournament runs into it.

`fully_queued` is checked because a queued registration is never settled except by waiver, and a revoked waiver on one must not start a clock the queue does not have.

### D3. Reopening lives in the ledger, where money is taken back

Credit reversal, payment-link removal and recorded-payment removal all end in `ledger.reverse` (through `reverse_for_source` / `reverse_for_rule`); waiver revocation is `ledger.revoke_waiver`. Each reads `registration.settled` before its write, flushes, and calls `reopen_window`. This is where `clear_promotion_marks` already sits, for the same reason: one place every route passes through, so a new route cannot forget. The amendment, which writes no ledger row, calls `reopen_window` itself.

The derivation re-reads in memory: the reversed entry is the same object in `registration.credits`, and `live_credits` / `active_waiver` filter on the stamp just written.

The cycle restart in `routers/registrations.py` also reverses through `ledger.reverse`; the window it reopens is overwritten a few lines later by `_initial_expires_at`, which is what a new cycle should carry.

### D4. Tournament settings: snapshot the settled ids around the update

`update_tournament` loads the reserved, settled registrations before applying the updates, and after applying them calls `reopen_window` on each with `was_settled=True`; the rule re-reads `settled` against the tournament's new values in memory and acts only where it dropped. This covers tolerance tightening and anything else in the PATCH that moves the reading (local currency, payments feature) without enumerating fields.

The query only runs when the update touches a field that can move the reading (`amount_tolerance_percent`, `eur_payments_enabled`, `local_currency`, `feature_payments`), so ordinary Setup saves pay nothing.

### D5. EUR switched off with EUR credit is refused

After the update is applied and the currency invariants reconciled: if the tournament took EUR before (`takes_eur`) and no longer does, and any live credit entry of the tournament is in EUR, raise `409 eur_credits_present: <n>` where `n` is the number of distinct registrations. The check runs before the commit, as every other validation of this endpoint does, so nothing is saved. Frontend maps the code to a Czech and English sentence carrying the count.

### D6. The misleading comment

`resettle_within_tolerance`'s docstring says a tightened tolerance leaves settled registrations alone and cites "Re-deciding a short payment", which no spec holds. Rewrite: tightening is a derivation like widening, and what follows for the window is `reopen_window` in `update_tournament`.

## Risks / Trade-offs

- [A settle-then-unsettle within one tick leaves the old window in place, which the expiry pass would see] → `reopen_window` sets a fresh window unconditionally on the flip, so the old one is overwritten either way.
- [A path not wired up still leaves the stale window if the tick has not yet run between settle and unsettle] → the window lasted at least until the tick after settlement in practice; the tick runs every 5 minutes, so the exposure is a settle and unsettle within the same 5 minutes on a path we missed. Accepted.
- [Clearing `expires_at` changes readers] → `entrants._paid` reads the window only for unsettled rows; mail reads it only when money is due. Checked; no reader treats a settled registration's window as meaningful.
- [Tolerance tightening silently creates debtors] → owner chose to allow it; the console's balance column states the shortfall, and the reminder reaches the fencer.

## Migration Plan

None. The first tick after deploy clears windows on settled registrations. Rollback is a code revert; a cleared window on a settled registration is harmless to the old code, which spares settled registrations anyway.
