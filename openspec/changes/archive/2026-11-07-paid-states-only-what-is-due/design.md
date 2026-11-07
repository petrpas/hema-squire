## Context

See proposal.md — Why. The mechanics that matter here:

- `entrants._conduct` reduces the tournament to two booleans, `collects`
  (payments on and registrations kept by Squire) and `queue`. `entrants._paid`
  turns `collects` plus one registration's `settled` into the cell and the fade.
  Neither knows the payment mode.
- The mode is already readable: `setup.owing_mode(tournament, registration)`
  answers which mode money is actually asked under, correcting the stored mode
  for a registration that holds no seat; `setup.seating_has_settled(tournament,
  now)` answers whether the seating deadline has passed (or an organizer closed
  seating early), resolving the date in the tournament's own zone.
- `Registration.expires_at` is the running payment window, null where none runs.
  `_initial_expires_at` already composes exactly these three facts to decide
  whether a window opens at all, so the predicate this change needs is the
  mirror of one that exists.
- The three roster builders reach a registration differently: `_teams` holds
  `team.registration`, `_individual` and `_event` hold replayed export rows
  carrying `registration_id` and a `paid` flag, with live ids in a `set[int]`.

## Goals / Non-Goals

**Goals:**

- One predicate, asked once per registration, answering "is this registration's
  money due now" — reused by all three roster builders.
- The rule stays wholly on the server, as design D4 of `show-event-entrants`
  settled: the client keeps receiving `paid` and `faded` already decided.

**Non-Goals:**

- The organizer's surfaces: the Export tab, the printed roster, the payments
  console. They state the settled flag to a reader who knows the mode.
- The visual weight of the roster — that a nearly unpaid seated block reads
  lighter than the queue below it remains true after the seating deadline, and
  is a separate change.
- Any new stored column, audit event, or mail.

## Decisions

**D1 — the predicate is "money is due", not "money was requested".** A
reservation-mode fencer may pay the moment they register; the confirmation
carries the instructions. So the question the roster asks is not whether an
invoice went out but whether the date has come: a payment window is running on
the registration (`expires_at` is not null), or the obligation its seat is held
under has fallen due (`seating_has_settled`). Alternative considered — keying
off "a window ever opened" — collapses reservation mode and deposit-after-
deposit into the same silence forever, which would leave an unpaid seat
unmarked past the deadline, when the roster genuinely has something to say.

**D2 — the running payment window *is* the per-registration half.** The
question splits cleanly in two: whether the seating deadline has passed is
asked of the tournament and becomes a third field of `_Conduct`; whether a
window is running is asked of each registration and is already recorded as
`expires_at`.

Nothing re-derives the mode at the roster. `_initial_expires_at` applied it when
it decided whether a window opened at all — it opens in immediate mode, in
deposit mode until the deposit arrives, for items held with no seat whatever the
stored mode says, and never for a seat the tournament holds unbilled — and
every later transition that closes or reopens one (the deposit threshold, a
demotion, a reinstatement) maintains it. Reading the window therefore answers
`owing_mode` without a second place deciding it.

It also costs nothing: the replayed export rows the individual and side-event
rosters are built from already carry `expires_at` (`sheet.py`), and the team
roster already loads its registrations. The `dict[int, bool]` an earlier draft
of this design proposed is unnecessary — no map, no extra query.

**D3 — `_paid` gains the parameter rather than a sibling function.** The three
call sites must not drift; the shared helper is what keeps the cell and the fade
in agreement. Its signature becomes `(conduct, settled, due)` and it answers
`("yes", False)` when settled, `("no", True)` when collecting and due,
`(None, False)` otherwise — the last branch now reached in two ways, by a
tournament Squire does not collect for and by a registration nothing is due on,
which read identically to a visitor because the claim being withheld is the
same one.

**D4 — "now" is resolved once.** `seating_has_settled` takes an instant, so
`rosters` resolves `datetime.now(UTC)` once and hands it to `_conduct`, which
also stops reading the clock a second time for the held-tournament boundary it
already decided. A long answer straddling midnight cannot have one roster
reading the day before and the next the day after.

## Risks / Trade-offs

- **A reservation-mode roster now says nothing about money for most of its
  public life** → That is the point: it says nothing because nothing is known.
  The organizer's console still shows who has paid early, and the roster says
  yes for them.
- **An empty cell now has two causes** (Squire does not collect; nothing is due
  yet) → A visitor cannot tell them apart, and does not need to: neither is a
  claim about a person. The column header stays unqualified for the same reason.
- **The seating deadline becomes load-bearing on a public page** → It already is
  (it anchors the reminder and the demotion pass), and `seating_has_settled` is
  the one place it is resolved, including the organizer's early close.

## Migration Plan

None. Nothing is stored; the rosters are computed per request, so the change
takes effect on deploy and reverts with a rollback.
