## Why

A fencer who selects a full discipline alongside an open one is queued for both,
and loses a seat that was there for the taking. `register()` computes one
`is_substitute` flag for the whole registration — if anything is full,
everything queues — while the form's own row copy tells the fencer, on the full
row only, that *that row* is the one they will be a substitute for.

Every other placement path in the system already works per entry: `amend()`
places each added discipline against its own capacity, `_team_waitlist_flags()`
waitlists each team on its own, and `_demote()` moves each seated entry down on
its own. Registration is the single place that decides in bulk, and the result
is route-dependent: register for rapier and then amend to add a full longsword
and you keep your rapier seat; ask for both in one submission and you do not.

## What Changes

- Registration places **each individual discipline independently**: those with
  free places are seated, those that are full join the substitute queue, in one
  submission. Teams already behave this way and are unchanged.
- **BREAKING** — `wait_for_all` is removed from `RegisterIn`, and with it the
  `409 full_disciplines` refusal. There is nothing left to negotiate at
  submission: full rows queue, open rows seat. A per-row "only if I get in"
  opt-in may return later as its own change; this version does not offer one.
- **Queue membership is re-founded on the entry rather than the registration's
  state.** A mixed registration is paid for its seated part while still holding a
  substitute entry, so counting the queue from reserved registrations alone stops
  working: the paid fencer vanishes from the queue length and two fencers both
  come back as position 1.
- **A paid registration can be promoted.** `admit_substitute()` currently refuses
  anything not in the reserved state, which would make the mixed case
  unresolvable. It instead bills the *difference*, opens a fresh payment window,
  and notifies the fencer that their place has opened and what it now costs.
- **A mixed registration whose payment window lapses is demoted, not expired.**
  It loses the seat it did not pay for and keeps the queue place it owes nothing
  for, extending the rule that already governs a lapsed promotion after seating
  settles.
- Returning a seated placement to the queue stays refused on a paid
  registration: that one would leave money in the queue, and its route is still
  cancellation.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `registration`: "Capacity and substitutes" is silent on a selection that mixes
  full and open disciplines and must state that each is placed on its own.
  "Reservation lifecycle" states that a lapsed payment window leaves the fencer
  outside the substitute queue, which stops being true for a registration that
  holds a queue place it never owed for.
- `seating-queue`: the invariant "A registration in the queue SHALL never be in
  the paid state, so queue length and queue position remain countable from
  reserved registrations alone" is stated as load-bearing and no longer holds.
  Promotion's refusal on a non-reserved registration, and what promotion bills,
  change with it.

## Impact

**Backend**

- `app/routers/registrations.py` — `register()` per-entry placement and the
  removal of the `wait_for_all` branch; `queue_position()`; `admit_substitute()`
  guard, billing and notification; `return_to_queue()` unchanged but re-examined.
- `app/availability.py` — `queue_length()` and `team_queue_length()`.
- `app/scheduler.py` — the expiry pass demotes a registration holding a
  substitute entry instead of expiring it.
- `app/schemas.py` — `RegisterIn.wait_for_all` removed.
- `app/emails.py` — a promotion notice naming the discipline that opened and the
  amount now due, modelled on `send_surcharge_due`.
- Locale bundles for the new mail.

**Frontend**

- `src/api.ts` — `wait_for_all` removed from the registration payload type.
- `src/TournamentFace.tsx` — the field is no longer sent and the
  `full_disciplines` catch block goes with it. No copy changes: `form.full`
  already promises per-row placement.

**Tests**

- `backend/tests/test_registrations.py::test_wait_for_all_queues_everything_unbilled`
  pins the behaviour being replaced and is rewritten, not deleted.
- New coverage for a paid registration holding a queue place: its position, the
  queue length it counts toward, its promotion, and its lapse.

**Not affected**

- No migration. `is_substitute` is already per-entry on
  `RegistrationDiscipline`; only who writes it changes.
- Team placement, `_demote()`, and `amend()` already do the right thing.
