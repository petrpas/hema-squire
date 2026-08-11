## Why

The reservation model has exactly one shape: register, owe the full amount, hold the seat for `reservation_validity_days`, expire if unpaid. Organizers run three different shapes, and two of them cannot be expressed at all.

The missing concept is a **seating deadline** — one date per tournament after which registering no longer grants a seat, only a queue position, and by which any money still owed must have arrived. Today every clock is private to one registration (`registered_at + reservation_validity_days`), so there is no moment at which the tournament as a whole settles who is in.

Three consequences, all live:

- A tournament that lets fencers reserve for free and pay later has no way to say "pay by this date". The only available clock expires each fencer on their own private schedule.
- A tournament that takes a deposit has nowhere to put one. `grep -i deposit` over `backend/`, `frontend/` and `openspec/specs/` returns nothing.
- `admit_substitute` — the endpoint that promotes a fencer off the queue — **has no frontend caller anywhere** (`Console.tsx:80` renders `substitute_for` as read-only muted text). The organizer control that every one of these modes depends on after the deadline does not exist in the UI, and there is no inverse operation at all.

## What Changes

**A payment mode chosen by the organizer**, determining how a seat is held:

| Mode | Seat held by | Money owed at registration | At the seating deadline |
| --- | --- | --- | --- |
| `immediate` | full payment | full amount | nothing to settle — unpaid reservations already expired |
| `deposit` | a flat deposit | the deposit | balance unpaid → moved to the queue, deposit forfeit |
| `reservation` | nothing | nothing | full amount unpaid → moved to the queue |

**Two clocks, two distinct outcomes**, separated by which one ran out. This is the core of the change:

- the **payment window** (`reservation_validity_days`, 2–7 days) is the interval between money being requested and money being due — it exists because bank transfers are slow. Running out **expires** the reservation and releases the seat.
- the **seating deadline** (`seating_deadline`, one date per tournament) is when seating settles. Passing it with money owed **moves the registration to the substitute queue** — it does not expire it.

`expires_at` keeps exactly one meaning: the payment window. The deadline is never written into it, so `process_expiries` can never release a seat that should have been queued.

**A seating settlement pass**, run once per tournament: every still-unpaid reservation has its entries marked substitute and its teams waitlisted, in place, keeping its registration order. `queue_position` already ranks by `registered_at`, so a demoted fencer lands in the queue in registration order with no new sorting code. A `seating_settled_at` stamp makes it one-shot — without it, the next tick would demote everyone the organizer had just promoted.

It fires either from the scheduler when the deadline passes, or from the organizer, who can **settle seating early** from the console once the roster looks right. Same pass, same stamp, so the two can never both run. It is not reversible and the console confirms before firing it.

**After the deadline everything is organizer-driven.** New registrations are accepted as substitutes only. The organizer promotes from the queue at their own judgement; promotion requests money and opens a payment window like any other request. A new inverse endpoint returns a promoted fencer to the queue.

**Deposits are flat amounts** (`deposit_amount`, plus the independent `deposit_amount_eur` under dual-currency rules), never percentages, so an amendment can never move a deposit that has already been paid. Paying the deposit **clears** `expires_at` rather than extending it — the deposit discharges the payment window, the seating deadline takes over. This is consistent with the recorded decision that a partial payment does not extend a validity window.

**Not in scope:** notification of demoted fencers (deliberately deferred — the settlement pass emits audit events and the change ships without the mail); card payments; any change to matching, tolerance, crediting or refund behaviour beyond recognising the deposit threshold.

## Capabilities

### New Capabilities
- `seating-queue`: the organizer's control over who is above and below the line — the queue view, promotion, and the new return-to-queue action, plus the rules governing registration once the seating deadline has passed.

### Modified Capabilities
- `registration`: reservation lifecycle branches on payment mode; the seating deadline and its settlement; post-deadline registration as a substitute.
- `tournament-admin`: payment mode, seating deadline, deposit amounts, and the tightened payment-window range as configurable parameters.
- `payments`: crediting recognises the deposit threshold and clears the payment window when it is reached.

## Impact

**Backend** (`backend/app/`): `models.py` (`PaymentMode` enum; `Tournament.payment_mode`, `seating_deadline`, `deposit_amount`, `deposit_amount_eur`, `seating_settled_at`), Alembic revision defaulting every existing tournament to `immediate` so current behaviour is unchanged; `scheduler.py` (`settle_seating`, ordered before `process_expiries`; `process_reminders` re-anchored to whichever clock applies); `routers/registrations.py` (`register` post-deadline branch and mode-dependent `expires_at`; `admit_substitute` window clamp; new return-to-queue endpoint); `matching.py` (deposit threshold clears the window); `setup.py` (seating-deadline resolution helper); `schemas.py` + `constraints.py` (the new fields and their validation).

**Frontend** (`frontend/src/`): `ParamPanel.tsx` (mode select and its dependent fields — first select-typed field in a panel that currently knows only `number`/`date`/`text`), `setup/` (deposit amounts alongside the other prices, subject to the dual-currency completeness rule), `Console.tsx` (queue view with promote and return-to-queue — the first caller of `admit_substitute`), `api.ts`, `i18n/{en,cs}.json`, `constraints.ts` (generated).

**Design constraints**: `CLAUDE.md` / `openspec/squire-design-spec.md` are binding on every new surface — no gradients, shadows, radii above 2px, emoji, spinners, or hex values outside `tokens.css`.

**Verification**: backend by `pytest`; frontend by `npm run lint` (`tsc -b --noEmit`), build, and driving the console, since there is no frontend test runner.
