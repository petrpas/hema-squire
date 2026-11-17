## Context

**Context: floor.** `add-floor-console` stores what the planner needs: days, pistes,
formats, officials and parameters. The floor roster gives N per discipline and the
persons the disciplines share.

**The source framing.** The owner document "formalizace plánovače turnaje" frames the
planner as `Plan = solve(Fakta + Rozhodnutí(volná | připnutá) + Preference +
Konstanty)`, split into four subproblems solved in this order:
1. `structure`
2. `schedule`
3. `draw`
4. `officials`

This change builds the first two, and the handover to `draw`. `draw` is
`add-floor-pools`, and `officials` is `add-floor-officials`.

**Engine rule.** `CLAUDE.md` binds `app/floor/engine` to the standard library, with no
I/O and no clock. The owner confirmed on 2026-11-16 that the engine stays
standard-library only.

## Goals / Non-Goals

**Goals:**
- A deterministic, pure engine for structure, scheduling, variants, explanations and
  sensitivity.
- Versioned plans with pins, a publish gate, diffs and re-planning.
- The Plan tab and the schedule panel.

**Non-Goals:**
- The draw. Who fences in which pool is `add-floor-pools`.
- Assigning named officials to pistes. That is `add-floor-officials`. The planner here
  only caps concurrent pistes by the officials' count.
- Itineraries per person, call lists and printed sheets. These need the draw and arrive
  with `add-floor-pools`.
- Optimality. The engine enumerates and schedules heuristically. It does not prove a
  plan optimal.

## Decisions

### D1. The engine's model
`engine/model.py` holds frozen dataclasses only. Times are integer minutes since
midnight of a day, with days referred to by index. The service converts to and from
wall-clock time in the tournament's timezone, so the engine knows no timezone and no
date.

```
Problem(days, pistes, disciplines, shared, officials, pins, params, frozen)
  Day(index, start, end, breaks)
  Piste(id, days, reserve)
  DisciplineFacts(id, kind, n_pool, n_bracket, format)   # n_bracket = teams for a team discipline
  shared: dict[(disc_a, disc_b), int]                     # persons in both
  officials: dict[(day, role), int]
  pins: tuple[Pin, ...]                                   # day | k | place | sequence | frozen
Plan(variant_key, activities, metrics, exclusions, collisions)
Activity(id, discipline, kind, ordinal, round, piste, day, start, end, final)
Infeasible(reason, subject)
```

Activity ids are deterministic strings, for example `LS:pool:3` and `LS:r2:1`. A pin on
a placement and a diff between versions can then match activities across versions.

### D2. Structure
- **Pool counts.** `structure.pool_counts(n, lo, hi)` returns every k with
  `lo ≤ ⌊n/k⌋` and `⌈n/k⌉ ≤ hi`.
- **Bracket.** `structure.bracket(a)` returns the size, the byes, and the rounds with
  their bout counts. A third-place bout is one more activity in the last round, and it
  is marked final.
- **Team disciplines.** `n_pool` is their members and `n_bracket` their teams. This is
  the owner's 2026-11-16 decision: individual pools, then a team elimination.

### D3. Scheduling: list scheduling with a resource cap
**Order of placement.** Activities are taken in priority order:
1. by the discipline sequence, where one is pinned;
2. then by precedence depth;
3. then by critical path length, longest remaining chain first.

**Placement.** Each activity takes the earliest feasible start on any eligible piste,
lowest piste ordinal first among equal starts. At every start, feasibility checks:
- the day's window and its breaks;
- piste availability;
- precedence and rest;
- the officials cap `floor(officials[day, role] / template[role])`, minimised over
  roles.

**Why this algorithm.** It is O(activities × pistes × candidate starts), and a
tournament has tens to a few hundred activities. That is fast enough to run once per
variant.

**Alternative:** a CP-SAT model. Rejected by the owner's decision on dependencies.

### D4. Variants: enumerate, filter, Pareto, order
**The space.** The product of k choices and free day choices is enumerated in a
deterministic order. If the product exceeds 2,000, the engine fixes the disciplines with
the fewest k choices at their preferred k (largest pools when that preference is on).
It does so one discipline at a time until the product fits, and states that it did so
on the result.

**Dominance.** The criteria are each day's last end, the exclusion load and the bracket
collisions. Preferences order the Pareto set and never filter it.

**Explaining infeasibility.** Where nothing is feasible, the engine retries with each
pin and each hard rule removed, one at a time. It names the first whose removal admits
a variant. A discipline whose structure alone is infeasible is named before any pin.

### D5. Exclusion sets and collisions
After scheduling, the engine groups a discipline's pools into waves: pools that start
together. For every pair of disciplines with shared persons > 0, a wave of discipline A
is parallel to B if it overlaps in time with any activity of B.

**What is handed over.** The engine hands over the parallel waves. The draw's existing
model takes the same input (`hema-agent` `PoolConfig.parallel_waves`).

**Shortage.** A shortage exists when the places in A's non-parallel waves are fewer
than the shared persons.

**Collisions.** These are pairs of elimination rounds of two sharing disciplines that
overlap in time.

### D6. Storage
| Table | Holds |
|---|---|
| `floor_plans` | `tournament_id`, `version`, `status` (`working` / `published` / `history`), `variant` (JSON: k and day per discipline), `metrics` (JSON), `exclusions` (JSON), `collisions` (JSON), `created_at`, `created_by` |
| `floor_plan_activities` | `plan_id`, `activity_id`, `discipline_id`, `kind`, `ordinal`, `round`, `piste_id`, `starts_at`, `ends_at`, `final` |
| `floor_pins` | `tournament_id`, `kind`, `target`, `value` (JSON), `gate` (nullable: which gate added it), `created_at`, `created_by` |

**Uniqueness.** A partial unique index allows one `working` and one `published` row per
tournament.

**Times.** `starts_at` and `ends_at` are aware UTC datetimes, converted from engine
minutes through the tournament's timezone. The timezone rule is `day-boundaries`.

### D7. Re-planning input
"Přeplánovat" builds a `Problem` with `frozen` set to the activities that have started.
In this change nothing reports that an activity has started yet. So `frozen` comes from
a function each later change contributes to (`app/floor/progress.py`, empty here), and
`now` is passed in by the service, never read by the engine. Reserve pistes are marked
available in a re-planning `Problem`.

### D8. Imports that cross the floor boundary
None new.
- `planning.py` reads `app.floor.models`, `app.floor.roster`, `app.floor.engine`,
  `app.db` and `app.errors`.
- The roster arrives through `adapters/office.py`, which gains no new office import:
  `shared` is computed from the port's persons and entries, in floor code.
- `engine/*` imports only the standard library and `app.floor.engine.*`.

### D9. The schedule panel
**Drawing.** It is an HTML grid: one row per piste, one column per 5 minutes, and an
activity spans its columns. It uses no chart library and no SVG animation.
- An activity in the diff carries a text mark: "posunuto", "nové" or "zrušeno". It is
  also outlined with `--stamp` where it moved. Colour is never the only signal.
- Reserve pistes are drawn last, labelled "rezerva".

**Narrow screens.** On a narrow screen the grid scrolls horizontally inside its own
band (`responsive-layout`, A tab control too wide…, applied to the grid).

### D10. Decisions made during implementation (made by me; for the owner's review)
These were open in the proposal. I decided them on 2026-11-17, while the owner was away,
as the owner asked:
- **Officials cap by role, not by piste count.** At every moment, the sum of each running
  discipline's template per role stays within that day's officials of the role. This
  generalises `floor(officials / template)` to days where disciplines with different
  templates run together.
- **No officials entered means no cap.** An empty officials list is "not counted yet".
  It is not "nobody". Once any official is entered, a role nobody fills counts as zero.
- **An official counts toward every role they can fill.** That is an upper bound. The
  officials assignment (`add-floor-officials`) settles who does what.
- **A sequence pin orders non-final activities.** With "finals last" on, every final
  still waits for the whole day. Otherwise sequence and finals-last would contradict
  each other.
- **Rest between two disciplines sharing persons** is enforced only where a sequence pin
  puts one after the other. Disciplines running side by side are kept apart by the
  draw's exclusion sets instead.
- **Waves are piste-sequence indexes.** A pool's wave is the number of pools of its
  discipline its piste ran before it, from 1. They are not derived from start times.
- **A shortage is counted per pair** as the smaller of the two directions' deficits,
  since either discipline can take the shared persons.
- **Disciplines with nobody entered are left out of the plan** and listed as such,
  rather than failing the whole tournament's planning before registration opens.
- **Variants are not stored.** Choosing one runs the planner again and takes the
  variant of that key, which determinism makes safe. A changed state answers 409
  `variant_gone`.
- **Re-planning stores its first variant** as the working version. A discipline that
  has started keeps its published k.
- **Plan authors are stored as account ids** (`created_by`), not as labels, so account
  deletion has no text to redact.
- **The enumeration cap fixes days too**, after k, if fixing k alone does not bring the
  space under 2,000. The result names every discipline it fixed.

## Risks / Trade-offs

- **[List scheduling can miss a better plan an exact solver would find.]** → The plan is
  a proposal. Pins let the organizer force a choice, and sensitivity shows where more
  resources stop helping. The owner accepted the trade on 2026-11-16.
- **[The enumeration cap can hide variants.]** → The result states when the cap fixed a
  discipline's k, and which discipline it was.
- **[Wave detection by common start is fragile if pools of one wave start a few minutes
  apart.]** → Pools of one discipline are placed as a block on the first free pistes.
  Waves are derived from that placement, not from the clock alone.
- **[Times stored in UTC can be shown in the wrong zone.]** → All display goes through
  the tournament zone, as `day-boundaries` requires for organizer-set times.

## Open Questions

- Is 2,000 the right enumeration cap? It needs measuring against a three-day, ten-
  discipline tournament once the engine exists.
