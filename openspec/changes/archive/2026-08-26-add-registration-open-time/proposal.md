## Why

Registration opening is the one moment of a tournament's life when every fencer
arrives at once. Organizers deliberately schedule that clickfest for a civilized
hour — 18:00 on a weekday evening, not the small hours — but Squire stores
`registration_opens` as a bare date, so the only opening moment it can express is
the start of a day. Worse, the gate compares against the **UTC** date
(`setup.registration_availability`, `_now().date()`), so a Czech tournament that
"opens on 1 September" actually opens at 01:00 or 02:00 local time, depending on
daylight saving. The organizer cannot choose the hour, and the hour they get is
one nobody would choose.

## What Changes

- A tournament gains an optional **opening time of day** alongside its
  registration-opens date. Set, registration opens at that wall-clock moment;
  unset, it opens at the start of that day, exactly as today.
- A tournament gains a **timezone** (IANA name, e.g. `Europe/Prague`), which is
  what the opening time — and every other timeline date's day boundary — is read
  in. It is offered on `TIMELINE` in Setup, defaulted for new tournaments and
  backfilled for existing ones.
- The registration-availability gate stops being a date comparison and becomes an
  **instant** comparison for the opening edge. The closing edge keeps its
  whole-day meaning ("on or before the closes date") but is now evaluated against
  the tournament's local date rather than the UTC date.
- Fencer-facing payloads carry the resolved **opening instant** (an absolute,
  offset-bearing timestamp) rather than only a date, so no client has to know the
  tournament's timezone rules to display or compare it. The payload also carries
  the server's current instant, so a client can correct for a skewed local clock.
- The tournament detail page states the opening moment as date *and* time, shows
  a **live countdown** inside the last 24 hours, and **unlocks registration in
  place** when the moment passes — no reload, no manual refresh pile-up. The
  backend stays the sole authority: a submission that beats the gate is still
  rejected, and the page returns to waiting.
- **BREAKING (behavioral, no API break)**: an existing tournament whose opening
  date has not yet passed will open at 00:00 in its timezone instead of 00:00
  UTC. Every European zone is *ahead* of UTC, so its local day turns first and
  registration therefore opens one or two hours **earlier** than it would have
  — the tournament stops opening at 01:00 or 02:00 on the morning after the day
  it named, and starts opening when that day begins. (A tournament in a zone
  behind UTC shifts the other way, later.) No stored value changes and no
  client contract is removed.

Deliberately out of scope: the registration close, the seating deadline, the
amendments close and the team composition deadline stay whole-day boundaries.
They are ends of a window, not a starting gun, and nobody queues for them.

## Capabilities

### New Capabilities
<!-- none: this extends existing behavior rather than introducing a new capability -->

### Modified Capabilities
- `tournament-admin`: the Registration window requirement gains the opening time
  of day and the tournament timezone, their hints, their validation (a time
  without a date; a clock time that does not exist on a DST spring-forward day),
  and the rule that clearing the date clears the time.
- `registration`: the availability gate is defined on an instant rather than a
  date; the not-yet-open rejection and the fencer-facing tournament list carry
  the resolved opening instant instead of a bare date.
- `fencer-home`: the detail page states the opening moment with its time, counts
  down to it inside the last day, and unlocks the Register tab in place when it
  passes.
- `setup-navigation`: `TIMELINE` holds the opening time beside the opening date
  and the tournament timezone that governs the whole timeline.
- `design-system`: a live-updating figure (the countdown) is admitted to the
  vocabulary as static text that re-renders, explicitly distinguished from the
  animated progress indicators section 8 prohibits.

## Impact

- **Model / migration**: `Tournament.registration_opens_time` (nullable time),
  `Tournament.timezone` (non-null IANA string). One Alembic revision, backfilling
  the timezone on existing rows.
- **Backend**: `setup.registration_availability` and `setup.amendment_availability`
  change signature from `today: date` to `now: datetime`; their three call sites
  (`routers/tournaments.py`, `routers/registrations.py` ×2) follow.
  `setup.py` gains the resolution helper that folds date + time + zone into an
  instant. `schemas.py` gains the two fields on the setup DTOs and the resolved
  instant on `OpenTournamentOut` and the detail DTO. `export_json.py` round-trips
  both new fields.
- **Frontend**: `TimelineSection.tsx` (time input, timezone control),
  `TournamentFace.tsx` (`registrationStatus` compares instants; the window line
  states the time), the detail page's waiting state (countdown + in-place
  unlock), `api.ts` types, `en.json`/`cs.json` strings.
- **Dependencies**: `zoneinfo` (stdlib) on the backend; `tzdata` on deployments
  without a system zone database. No new frontend dependency — the client only
  compares absolute instants.
- **Tests**: `test_registration_gating.py`, `test_open_tournaments.py`,
  `test_export_json.py`, `test_tournaments.py`.
