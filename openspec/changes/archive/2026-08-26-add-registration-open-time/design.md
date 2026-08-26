## Context

See `proposal.md` — Why. The facts that shape the approach:

- **`registration_opens` is a `Date` column** (`models.py:215`) and the gate is
  `today < tournament.registration_opens` in `setup.registration_availability`
  (`setup.py:181`), fed `_now().date()` — the **UTC** date — from all three call
  sites (`routers/tournaments.py:212`, `routers/registrations.py:405`, and
  `:614` via `amendment_availability`).
- **The codebase has no timezone concept at all.** Every stored instant is UTC
  (`matching.py:150`), every timeline field is a naive date, and both fencer
  surfaces render dates with a hardcoded `toLocaleDateString("cs")`. There is no
  deployment-level zone setting to lean on.
- **The frontend re-derives the gate** rather than trusting the server:
  `registrationStatus()` in `TournamentFace.tsx:121` compares an ISO day string,
  and `amendmentOpen()` sits on top of it. Whatever the backend's opening rule
  becomes, this function has to agree with it or the Register tab and the API
  will disagree at the edge.
- **The design prohibitions (CLAUDE.md, spec §8) are binding** and name
  "skeleton shimmer, spinners, animated progress bars". A countdown has to be
  justified against that list, not smuggled past it.

## Goals / Non-Goals

**Goals**
- The organizer names the hour registration opens, in the tournament's own local
  time, and gets exactly that hour — including across a daylight-saving change.
- One resolution rule, in one place. No caller — backend or frontend — folds a
  date, a time and a zone together a second time.
- A fencer waiting for the moment is not asked to reload, and is not the reason
  the server gets a burst of polling before the moment.
- The old behavior survives untouched where nothing new is set: no opening time
  means the start of the day, as before.

**Non-Goals**
- No account-level or viewer-level timezone. The tournament's zone is the only
  one; a fencer in Berlin reads a Prague tournament's opening in Prague time,
  stated with its zone, because that is the time the organizers announced.
- No scheduled job at the opening moment. Nothing is *sent* when registration
  opens; the gate is evaluated on read, as it is today.
- No clock time on the close, seating, amendments or composition deadlines
  (proposal — Scope).
- No queueing, rate-limiting or waiting-room machinery for the clickfest itself.
  This change makes the moment predictable and civilized; surviving the load at
  that moment is a separate concern.

## Decisions

### Decision 1 — Store date + time + zone; resolve to an instant on read

Three columns:

```
registration_opens       Date          (unchanged)
registration_opens_time  Time | None   (new; NULL = start of day)
timezone                 String(64)    (new; non-null IANA name)
```

and one helper in `setup.py` that is the only place they are combined:

```python
def registration_opens_at(tournament) -> datetime | None:
    """The instant registration opens, in UTC — None when no opening date is
    set (registration opens on publication). Unset time means the start of the
    local day, which is what a date-only tournament has always meant."""
```

**Alternative rejected — a single `registration_opens_at` timestamptz.** It
looks tidier and needs no zone column, but it destroys the organizer's intent:
what they chose is *18:00 local*, and a stored instant cannot be re-displayed or
re-edited as that without the zone anyway. It also breaks re-editing across a DST
boundary — moving the date from March to April would silently shift the hour. The
zone has to be stored regardless, so storing the wall-clock parts beside it costs
nothing and keeps the value the organizer typed recoverable verbatim.

**Alternative rejected — a deployment-wide zone setting.** One `HEMA_SQUIRE_TIMEZONE`
would cover the Czech launch and cost one line. But the tournament is the thing
that has a location and a local time, not the server, and a Squire hosting a
Polish or Austrian event would then announce the wrong hour with no way to fix it
short of a redeploy. The per-tournament column is one migration either way.

### Decision 2 — The timezone governs the whole timeline, not just the opening

`timezone` is not "the zone of the opening time"; it is the tournament's zone, and
every timeline date is read as a local day in it. So the closing edge becomes
`now.astimezone(tz).date() > closes` rather than `now.astimezone(UTC).date() > closes`.

This is deliberately more than the opening needs, because the alternative is
incoherent: a tournament would open at 18:00 Prague and close at 01:59 Prague on
the day after its closing date. It also quietly fixes the existing drift — every
"today" comparison in the registration path has been up to two hours off for
Czech tournaments since the beginning.

Non-null with a default, not nullable: a nullable zone means every read site has
to decide what NULL means, and they would drift. Existing rows are backfilled
(Decision 9).

### Decision 3 — Only the opening edge is an instant; the closing edge stays a day

`registration_availability` gains two different comparisons, and the asymmetry is
the point:

```
opens:  now < registration_opens_at(tournament)          → NOT_YET_OPEN
closes: local_date(now, tz) > (registration_closes or date) → CLOSED
```

An opening is a starting gun — a moment. A close is a deadline — you have until
the end of that day. Making the close an instant too would mean a tournament
"closing on 30 September" stops accepting at 00:00 on the 30th, reversing what
every existing tournament's stored value means. Left as a local-day comparison,
every stored close keeps meaning exactly what it meant.

### Decision 4 — Daylight saving: reject what does not exist, take the first of what is ambiguous

An opening time is a wall clock the organizer picked; on two days a year a wall
clock is not a function.

- **Nonexistent** (spring forward — 02:30 on the changeover day in Europe/Prague
  never occurs): rejected at save with a field error on the time, naming the
  clock jump. Silently resolving forward to 03:30 would announce an hour the
  organizer did not choose, on the one day they are most likely to be surprised.
- **Ambiguous** (autumn back — 02:30 occurs twice): accepted, resolved to the
  **first** occurrence, i.e. the earlier instant. Registration opening a little
  early is harmless; opening an hour after the announced time is the failure that
  matters. Not surfaced to the organizer — there is nothing for them to decide.

Implemented with `zoneinfo` + `datetime.fold`: build the naive local datetime,
attach the zone, and compare `fold=0` against `fold=1` to detect both cases.
`zoneinfo` needs `tzdata` on a container without a system zone database — a
requirements entry, not a design constraint.

### Decision 5 — The gate takes an instant, and the helper is the only resolver

`registration_availability(tournament, today: date)` becomes
`registration_availability(tournament, now: datetime)` (aware, UTC), and
`amendment_availability` follows it — it delegates already, and its own
`amendments_close` boundary is compared as a local day per Decision 3. All three
call sites pass `_now()` instead of `_now().date()`.

Changing the signature rather than adding an overload is what keeps the invariant
enforceable: no caller can accidentally keep passing a UTC date and get the old,
subtly-wrong answer. `seating_has_settled` and the scheduler's other date
comparisons are **not** in scope — they govern settlement and reminders, not the
registration gate, and moving them is a larger blast radius for no gain here.

### Decision 6 — The wire carries a resolved instant and the server's own clock

`OpenTournamentOut` and the fencer detail DTO carry:

```
registration_opens_at   ISO-8601 with offset, or null   (resolved; replaces the
                                                         bare date's role in the
                                                         not-yet-open status)
registration_opens      date                            (kept — Setup edits it)
registration_opens_time time | null                     (kept — Setup edits it)
timezone                IANA name                       (for display: "18:00 CEST")
server_time             ISO-8601 with offset            (this response's instant)
```

The client compares instants and never does timezone arithmetic. This matters
more than it looks: `TournamentFace.registrationStatus` currently reimplements the
gate in ISO day strings, and the only way to keep it honest against a
zone-and-DST-aware rule is to hand it an absolute instant to compare against.

`server_time` is what makes the countdown trustworthy. The client computes
`skew = server_time − Date.now()` once at load and applies it to every tick, so a
browser whose clock is three minutes fast neither counts down to zero early nor
unlocks a form the server will reject.

**Alternative rejected — shipping the zone and letting the client resolve it.**
`Intl` can do it, but then the DST rules live in two implementations and can
disagree at exactly the moment that matters.

### Decision 7 — The countdown is text that re-renders, not an animation

Section 8 prohibits "skeleton shimmer, spinners, animated progress bars" — devices
that move to suggest progress they do not measure. A countdown is the opposite:
it is a *measured figure*, and it changes because the number changes. It is
admitted on those terms, with the constraints that keep it text:

- Rendered as a line of type in the same `--ink` as the rest of the hint. No bar,
  no ring, no track, no fill, no color transition, no easing, nothing that moves
  except the digits.
- Updated once per second by re-rendering the string. No CSS animation and no
  transition is attached to it.
- Tabular numerals at a fixed width, so the line does not reflow as digits
  change — the jitter, not the ticking, is what would read as animation.
- **Shown only inside the last 24 hours.** Beyond that it states the moment
  ("otevře se 1. září v 18:00") and nothing ticks. A seconds counter next to a
  date six weeks out is noise, and a page left open for six weeks should not hold
  a running timer.
- Below one hour it reads `MM:SS`; above, `H:MM:SS`. It stops at zero and is
  replaced by the opened state — it never displays a negative figure.

### Decision 8 — Unlock with one scheduled timeout and one refetch; the server stays the authority

While the page is showing the not-yet-open state, it schedules a **single**
`setTimeout` for the skew-corrected opening instant (plus a small margin). No
polling: a thousand fencers with the page open must not become a thousand
requests per second against the gate.

When it fires, the page refetches the detail once — the seat counts are stale by
then anyway — and re-renders with registration open. Because a browser throttles
timers in a background tab and suspends them across sleep, the same evaluation
also runs on `visibilitychange` and on window focus, so a tab returned to at
18:05 opens immediately rather than whenever a throttled timer catches up.

The unlock fires on the **transition alone**, guarded by a flag armed only
where the moment is still ahead when the payload arrives. Two things would
otherwise loop, and both were observed in the browser before the guard was
written: the refresh brings back a new payload, whose freshly measured skew
re-runs the scheduling effect, which fires the unlock again; and a page opened
on a tournament that opened weeks ago would fire immediately and then forever.
The skew is therefore a correction the effect *reads*, never a dependency it is
re-run by, and a page that was never shut never asks for a refresh.

The client-side flip is a *presentation* decision only. The backend gate is
unchanged as the authority, and a submission that arrives early is still rejected
with `not_yet_open`; the page handles that reason by returning to the waiting
state with the countdown recomputed from the fresh response, rather than showing a
generic error. That is also the fallback for a badly wrong client clock.

### Decision 9 — Editing rules: the time is a child of the date

- Clearing `registration_opens` clears `registration_opens_time` in the same
  save. A time hanging off no date is not a state the organizer can see or
  correct.
- Submitting a time with no date (a direct API caller, or a UI bug) is rejected
  with a field error on the time rather than silently stored.
- `timezone` is validated against `zoneinfo.available_timezones()`; an unknown
  name is a field error. Setup offers a `<select>` of the European zones with
  `Europe/Prague` preselected on a new tournament, and always includes the
  tournament's stored value even if it falls outside that list, so a value set
  through the API is never silently rewritten by opening Setup.
- Both new fields round-trip through `export_json.py` (its `_parse_date` sibling
  gains a `_parse_time`), so an export taken after this change and reimported
  reproduces the same opening moment.

### Decision 10 — Hints state the fallback, as every timeline field already does

`tournament-admin` requires each timeline field's hint to state what happens when
it is left unset. The two new controls follow, but only one of them gets a hint marker:

- opening time — no marker of its own. Its fallback is stated in the
  registration-opens hint, which the time sits inside. The time is a qualifier
  of that date, not a field beside it, so one hint covers both halves — and a
  second marker at the end of the field's row opens its window past the edge of
  the setup panel, which clips horizontally.
- timezone — "The tournament's local time. Every date and time on this timeline
  is read in it."

Both go through the normal i18n bundles; no literal is written into a component.

## Risks / Trade-offs

- **Existing tournaments shift by an hour or two** → An opening date already in
  the future resolves at 00:00 local instead of 00:00 UTC. For a zone ahead of
  UTC — every European one — the local day turns first, so registration opens
  1–2 hours *earlier* than it would have: at the start of the day it named
  rather than at 01:00 or 02:00 the following morning. A zone behind UTC shifts
  the other way. Nobody has been told an exact hour
  (there was none to tell), and the new hour is the more defensible reading of
  "opens on the 1st". Called out in the proposal; the migration touches no
  tournament whose opening has already passed, since the gate is only consulted
  before it.
- **The frontend gate can still drift from the backend's** → Two implementations
  of one rule remains the structural weakness, unchanged by this design.
  Mitigated by Decision 6: the client's job shrinks to `now >= opens_at`, which is
  small enough to stay correct, and Decision 8 makes the server's answer the one
  that decides.
- **A wrong client clock unlocks early or late** → Skew correction (D6) handles
  the common case; the `not_yet_open` rejection path (D8) handles the rest without
  a dead end.
- **A background tab's throttled timer misses the moment** → `visibilitychange`
  and focus re-evaluation (D8).
- **The unlock re-triggering itself** → The refresh it schedules brings back a
  payload that must not re-arm it (D8). Verified in the browser: one refresh
  across the moment, and none at all during the wait or on an
  already-open tournament.
- **The countdown reintroduces motion into a deliberately static UI** → Bounded by
  D7's constraints, and confined to the last 24 hours before one specific moment.
  It is admitted to the design system explicitly (a `design-system` delta) rather
  than added quietly, so the prohibition list keeps its force.
- **`tzdata` missing on the deployment container** → Added to requirements;
  `zoneinfo` raises at import of the zone rather than computing a wrong answer,
  so the failure is loud.
- **The clickfest itself is untouched** → This change moves the load to a chosen
  hour; it does not reduce it. Deliberate (Non-Goals), and now at least the spike
  is at a time the organizer is awake to watch.

## Migration Plan

1. One Alembic revision: add `registration_opens_time` (Time, nullable) and
   `timezone` (String(64), nullable) via `batch_alter_table`, as the existing
   SQLite-compatible revisions do.
2. Backfill `timezone = 'Europe/Prague'` on every existing row, then alter it to
   non-null with that server default.
3. Deploy backend and frontend together. The frontend reads `registration_opens_at`,
   which only the new backend sends; an old frontend against the new backend keeps
   working from `registration_opens`, which is still present and unchanged.
4. **Rollback**: downgrade drops both columns. No existing column is altered and
   no stored value is rewritten, so a rollback loses only opening times set in
   the window — recoverable from the organizer, and visible as an empty field
   rather than a wrong one.
