## Why

Squire answers "what day is it today" in ten-odd places on three different clocks:
the tournament's own zone, the server process's `TZ`, and UTC. Only the first
group is a decision anyone wrote down — `registration_availability` says so in its
docstring, and `add-registration-open-time` D3 is where it was decided. The other
two are what each call site happened to reach for, and they draw their day
boundaries somewhere the organizer never sees.

Three of those are wrong in a way that costs something:

- **Seating settles on the server's day.** `settle_seating_if_due` compares
  `date.today()`; `seating_has_settled` and the reminder anchor compare the UTC
  day. So the same deadline decides *when to settle* and *whether it is settled*
  on two different clocks, and neither is the calendar the organizer typed the
  date into. Settlement moves people out of seats and runs once.
- **Early bird expires on the UTC day of `registered_at`.** A registration
  submitted at 00:30 CEST the day after the cutoff still gets the early price,
  because in UTC it is still yesterday. The same read decides the stored total,
  the price preview, and the date-condition discounts.
- **The team composition deadline is read in UTC**, a few lines from a
  registration deadline read in the tournament's zone.

The remaining server-zone reads (the Fio poll window, which tournaments the
scheduler walks, the token check) hurt nothing today, but they are the one
choice that is wrong in every deployment, because the answer changes with `TZ`.

## What Changes

The split is not between right and wrong readings but between two kinds of date,
and this change names it and applies it everywhere:

- A date **an organizer typed while looking at their own calendar** — seating
  deadline, team composition deadline, early-bird cutoff, registration close —
  means the whole of that day **in the tournament's zone**.
- An **operational window with no author** — the Fio fetch range, which
  tournaments are still running, the token check — takes fixed hours, **UTC**,
  never the server's zone.

Concretely:

- `settle_seating_if_due`, `seating_has_settled` and `_reminder_due` take an
  instant rather than a date and resolve it through `setup.local_date`, the shape
  `registration_availability` already set. The settle/settled disagreement goes
  with it.
- The team composition deadline (`console_teams`, and the `below_minimum` flag it
  raises) is read as a whole local day.
- Pricing's `at` is the tournament-local date of `registered_at`, not its UTC
  date — for the legacy `fee_early` columns, the date-condition discounts, and
  the price preview alike. **Historical totals stay reproducible**: the total
  stored on a registration is unchanged, only newly computed ones move, and only
  for registrations made in the two hours a day where the two clocks disagree.
- The public upcoming/past listing keeps **one global UTC boundary** — a single
  SQL comparison over tournaments from many zones — and that is written into the
  spec as a decision rather than left to be inferred from the query.
- The four server-zone reads become UTC.
- One helper is the only way to ask, so an eleventh call site cannot quietly
  invent a twelfth clock.

## Capabilities

### New Capabilities
- `day-boundaries`: which clock each kind of date threshold is read on, stated
  once, so the other capabilities name a rule instead of repeating it.

### Modified Capabilities
- `seating-queue`: the seating deadline, the settled-ness test and the reminder
  anchor are whole days in the tournament's zone, on one clock.
- `team-disciplines`: the composition deadline is a whole day in the tournament's
  zone, matching the registration deadline beside it.
- `tournament-admin`: the early-bird cutoff and the date discount condition are
  evaluated against the registration's tournament-local day.
- `fencer-home`: "dated before today" is a global UTC boundary, stated as intent.

## Impact

`app/setup.py` (the one helper), `app/scheduler.py`, `app/routers/tournaments.py`,
`app/routers/registrations.py`, `app/routers/payments.py`, `app/pricing.py`,
`app/bank.py`. Tests: `tests/conftest.py` already distinguishes `today_local`
from `today_utc`, and the boundary each helper serves moves under this change —
`deadline_ahead` and `deadline_passed` are anchored to the UTC day today and
stop being right. No migration; no stored value changes.
