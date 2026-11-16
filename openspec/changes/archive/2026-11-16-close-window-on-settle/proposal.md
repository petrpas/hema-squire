## Why

A registration that is paid keeps the payment window it was registered under, and the expiry pass spares it only for as long as it *reads* as paid. Whether it is paid is derived from credits, total and tolerance at every reading, so more things can take it back than were written knowing that. Five of them do — disabling EUR, tightening the tolerance, removing a recorded payment to re-enter it, reversing a credit, revoking a waiver — and each, after the window has passed, expires a fencer who paid within five minutes and mails them (`openspec/payments_gaps.md`, P3). Only an upward amendment opens a fresh window today.

## What Changes

- Settling a registration closes its payment window: once it reads as paid it carries no `expires_at`, as one that reached its deposit already does. The scheduler tick does this for every settled registration, whatever settled it, so it also clears the windows registrations settled before this change still carry.
- Losing the settled reading opens a fresh payment window through one shared rule, the one an upward amendment already applies: wherever the registration's clocks run, a new `setup.payment_window` from now. Credit reversal, payment-link removal, recorded-payment removal, waiver revocation and any tournament setting change that unsettles someone all go through it, and the amendment is moved onto it.
- A registration whose window was reopened this way is not mailed at that moment; its reminder record is cleared, so the ordinary reminder follows the new window.
- A tournament update after which a registration holding live EUR credit would have no EUR lane — EUR payments switched off — is refused with 409, stating how many registrations hold such credit.
- Tightening the amount tolerance stays allowed. Registrations it unsettles owe the difference under a fresh window.
- The comment in `matching.resettle_within_tolerance` claiming a tightened tolerance leaves settled registrations alone, and citing a requirement that does not exist, is corrected.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `payments`: a paid registration carries no payment window, losing the paid reading opens a fresh one without a mail, and EUR cannot be switched off while EUR money stands. `payment-ledger` keeps its wording: it says what reads as settled, and this change is about what follows when that reading changes.

## Impact

- `backend/app/setup.py` (shared reopening rule beside `payment_window`), `amendment.py`, `matching.py` (link removal, recorded-payment removal, comment), `routers/payments.py` (credit reversal), `routers/registrations.py` (waiver revocation), `routers/tournaments.py` (EUR refusal, settings that unsettle), `scheduler.py` (window cleared on settled registrations).
- No migration: the tick clears existing windows on settled registrations.
- Frontend: the Setup save surfaces the new 409 `eur_credits_present` in Czech and English.
- The probe tests named in `openspec/payments_gaps.md` P3 become regression tests.
