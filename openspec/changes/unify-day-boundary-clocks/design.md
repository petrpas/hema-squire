## Context

`openspec/changes/date-boundaries-read-three-clocks.md` is the survey this change
answers. It found "today" read on three clocks; reading the code again for this
design found two more sites and one clock disagreement it had missed:

- The seating deadline is compared against the **server's** day in
  `scheduler.py:310` (`settle_seating_if_due`) and against the **UTC** day in
  `scheduler.py:130` and `registrations.py:488` (`seating_has_settled`), plus in
  `scheduler._reminder_due`. On a server in Prague those two hold contradictory
  answers for two hours a day, and the window is exactly the one where
  `seating_has_settled` says yes while `settle_seating` has not run.
- Pricing evaluates `at=registration.registered_at.date()` — the UTC day of a
  stored UTC instant — for the legacy `fee_early` columns and for the
  `registered on or before` discount condition (`pricing.py:393`, `:408`), and
  `registrations.py:421` does the same for the price preview.

The clock that is right is already built and already documented:
`setup.local_date(tournament, now)` and `setup.start_of_local_day`, decided in
`add-registration-open-time` D2/D3 and stated in `registration`'s **The two
edges of the window**. What is missing is not a mechanism but its reach.

The tests the survey named no longer fail: `e823eb9` gave `tests/conftest.py` a
`today_utc()` beside `today_local()`, and each test now names the clock it
asserts against. That was the right fix for a test suite describing the code as
it stands, and it means the conftest helpers are a faithful map of the current
inconsistency — so they move with it.

## Goals / Non-Goals

**Goals:**

- One rule, written down, for which clock a date threshold is read on, and every
  site in `app/` obeying it.
- The seating deadline decided on one clock instead of two.
- Early bird and the date discount condition expiring at the end of the
  organizer's day, not two hours early or late depending on the fencer's hour.
- A gate that stops an eleventh site from inventing a twelfth clock.

**Non-Goals:**

- Per-row timezone comparison in the public tournament listing. That boundary
  stays one global UTC day (owner decision, 2026-09-09); this change writes the
  decision into the spec, it does not change the query.
- Rewriting any stored value. `Registration.total_amount` and `total_eur` are
  written once at registration and never recomputed on read; no backfill.
- Making the scheduler's tick cadence or the Fio fetch range configurable.

## Decisions

### D1: Two kinds of date, two clocks

A date is one of two things, and which one it is decides its clock.

**A date an organizer typed** — the seating deadline, the team composition
deadline, the early-bird cutoff, registration open and close — was typed while
looking at a calendar hanging where the tournament is held. It means **the whole
of that day in the tournament's zone**. This is what `registration` already says
about the closing edge; the change is that seating, teams and pricing say it too.

**An operational window with no author** — the Fio fetch range, which tournaments
the scheduler walks, the token check, the public upcoming/past split — has no
calendar behind it. It takes **fixed hours: UTC**.

*Alternative considered:* the server's local zone, which is what four sites read
today. Rejected outright — it is the only choice that is wrong in every case,
because the same deployment gives different answers from a different `TZ`, and
neither of the two real meanings is ever "wherever the process runs".

### D2: The signature is the enforcement, not the discipline

Every function that decides an organizer's deadline takes `now: datetime` and
never a `date`. `registration_availability` already does this and says why in its
docstring: *"Takes an instant rather than a date so that no caller can pass a UTC
day and get the old, subtly-wrong answer."* The same move applies to:

    seating_has_settled(tournament, now: datetime) -> bool
    settle_seating_if_due(session, tournament, now: datetime) -> int
    _reminder_due(tournament, registration, now)   # already takes an instant

A caller holding only a bare date cannot reach these, which is the point: the
zone conversion happens once, inside, through `setup.local_date`.

*Alternative considered:* keep the `today: date` parameter and fix each caller to
compute the local date itself. Rejected — that is exactly the shape the bug has
now, three callers computing the same date three ways, and it stays one careless
call site away from returning.

### D3: `setup.local_date` stays the only conversion; no new helper for it

The survey asked whether one function should read all of it. Half of one already
does. `local_date(tournament, now)` takes the tournament and answers in its zone;
seven of the sites have a tournament in hand. Adding a second name for the same
thing would give the next reader two to choose between.

For the operational side there is no helper: `datetime.now(UTC).date()`, written
out. It is three tokens, it says which clock it is, and it needs no tournament.

### D4: `date.today()` becomes a lint error

Ruff's `DTZ` ruleset is not currently selected. `DTZ011` is exactly
`datetime.date.today()` used, and after this change `app/` has none left. Adding
`DTZ` to `[tool.ruff.lint] select` makes the server-zone read impossible to
reintroduce without a written ignore.

A trial run reports 20 findings across `app/`, `../scripts/` and `tests/`: five
`DTZ011` in `app/` (the five this change removes), one `DTZ007` in `app/bank.py`
(a statement date parsed without `%z`, which is correct — a bank statement gives
a day and no zone, `paid-at-is-value-date` D1) and the rest in `tests/` and
`scripts/`. So enabling the ruleset is part of this change's scope, with the
`bank.py` finding taking a `# noqa: DTZ007` naming that decision, and the
`scripts/` `DTZ005` (a backup filename stamp) taking one of its own.

No lint can distinguish a correct `datetime.now(UTC).date()` from a wrong one —
that is what D2's signatures are for.

### D5: Early bird reads `registered_at` through the tournament's zone

`pricing.registration_total` and `registration_discounts` keep pricing at the
moment the registration was made — that is what makes a later correction
reproduce the original price — but resolve that moment to a day in the
tournament's zone rather than in UTC. `at` becomes
`setup.local_date(tournament, registration.registered_at)`, with the same
tz-naive guard the rest of the code uses for SQLite round-trips (every stored
instant is UTC; `matching.within_expiry_grace` documents it).

`price_preview` reads `local_date(tournament, _now())`.

`pricing.py` gaining an import of `setup` is a new edge; `setup` imports models
and nothing from `pricing`, so there is no cycle. If one appears, the conversion
moves to the two call sites that hold the tournament anyway.

### D6: The public listing keeps one UTC boundary, said out loud

`_published_tournaments` compares `Tournament.date` against a single day for
tournaments in many zones. Honest per-row comparison means evaluating the zone
column per row — a worse query and a lost index, for a boundary whose only
consequence is that a tournament held today stays under "upcoming" for the first
two hours of a Prague morning. The decision is to keep it, and `fencer-home`
gains the sentence saying so, because a boundary nobody wrote down reads as an
oversight to the next person who finds it.

### D7: `tests/conftest.py` follows the code

`today_local()` and `today_utc()` stay, and so does the docstring habit of naming
which clock a helper serves — but which helper serves which boundary changes.
`deadline_ahead` and `deadline_passed` are anchored to the UTC day today
*because* the reminder anchor and the settlement test read UTC; after D2 they are
tournament-local, and the helpers say so. `deadline_passed`'s `min(...)` over
three clocks, and `deadline_ahead`'s comment about taking the earlier one, exist
to straddle the disagreement this change removes.

## Risks / Trade-offs

**An amendment to a registration made in the disputed window reprices.** For a
registration whose `registered_at` falls in the hours where its tournament-local
day is already past `early_bird_until` while its UTC day is not, an amendment
recomputes the total at the standard price where it previously recomputed at the
early one. → This is the correct price, the amendment path already reprices and
logs the before/after (`amendment.py:211`), and `total_amount` is not rewritten
outside it. The population is registrations submitted in a two-hour band on one
particular day per tournament.

**A tournament mid-flight moves its settlement day.** A tournament whose seating
deadline is today, on a deployment whose `TZ` is not UTC, may settle up to a day
later than the old code would have. → `settle_seating` is idempotent on
`seating_settled_at` and the passes are reached from both the scheduler tick and
the manual `process` run, so the later settlement is a delay, never a double
run. Deploying outside the affected hours makes it a non-event.

**`DTZ` may fire on code this change does not otherwise touch.** → All 20
findings are enumerated above; nine are `date.today()` in tests, which move to
the conftest helpers they should already have been using, and the two genuine
ones take written ignores.

**The two-hour band is invisible in CI.** CI runs in UTC, where every clock in
this change agrees, so no test failure can prove the fix. → The new tests drive
the boundary through the instant parameter rather than the ambient clock: a
tournament in a zone ahead of UTC, an instant chosen inside the band, and the
assertion on the answer. That works in any runner zone, which is the property
`e823eb9` was reaching for and the reason D2 takes an instant at all.
