## Context

The floor module (`backend/app/floor/`, `frontend/src/floor/`) was built by the seven
floor changes archived on branch `floor` (a9e9ce6). The branch has not been pushed or
deployed, so no production database holds a `floor_` table. Its console was laid out
like the office console: a top bar, a second band of eight tabs, and Setup as one long
column of five sections. Owner testing showed this is too wasteful for the laptop the
floor runs on. It also showed that Setup asks for things most tournaments do not plan,
and lacks a few they do.

The owner's decisions taken while proposing (2026-11-17), and the main-referee tick
added after, are recorded in the specs:
- a discipline belongs to exactly one day;
- officials can be planned only with a schedule;
- unplaced entrants of a take-over are seeded below the placed ones, by HR rating;
- team points are per bout × k²;
- pistes lose their days;
- referees per bout default to 1/1, and judges and table officials are dropped;
- a "Hlavní rozhodčí" tick, default yes. Each block wants one main referee, and a
  block without one is a tolerated, badged warning;
- under "na konci turnaje" every final moves to the last day;
- the rail stays on phones.

## Goals / Non-Goals

**Goals:**
- One navigation band instead of two: the top bar plus a left icon rail.
- Setup as six small tabs, three of them governed by scope ticks.
- A data model that says what the owner means: a discipline's day, pistes and referees
  per discipline with a reserve tier, referees per stage, point targets, a take-over
  source, and the finals placement.
- A planner that plans with or without a schedule.

**Non-Goals:**
- No change to the office. The office's discipline already has a weapon. The floor
  starts reading it.
- No second bracket kind, no repechage, no per-team items.
- No automatic re-planning when Setup changes. Re-planning stays asked for.
- No precise referee-matching in the planner's officials cap. The assignment states
  what it cannot fill (see Risks).

## Decisions

### D1. The rail is the tab bar turned on its side
`FloorTabBar` becomes `FloorRail`. It keeps the tablist semantics, the badge and the
unsaved mark, and its arrows become up/down.
- **Icons.** Icons come from `@tabler/icons-react`, which is already a dependency and
  outline by default. The map lives in `tabs.ts` beside `FLOOR_TABS`, so order and icon
  cannot drift apart. Starting set: setup `IconSettings`, data `IconDatabase`, plan
  `IconCalendarCog`, today `IconLayoutDashboard`, checkin `IconUserCheck`, pools
  `IconGridDots`, bracket `IconTournament`, results `IconTrophy`, schedule
  `IconCalendarTime`. If a name is missing from the installed version, the nearest
  outline icon replaces it.
- **The hint.** The hint is a small static element the rail renders and CSS reveals on
  `:hover` and `:focus-visible`. It is not the native `title` attribute: `title` does
  not appear on keyboard focus, and its delay and style belong to the browser. The hint
  has no transition (`design-system`).
- **Accessible names.** Each tab's `aria-label` is its label, plus the badge's and the
  unsaved mark's words where they apply.
- **Layout.** `.floor-workspace` becomes a three-column grid: rail, work, and the
  schedule panel. The schedule panel is present only with a schedule planned and on a
  wide screen.

*Alternative considered:* a collapsible rail that expands to show labels. Rejected,
because the owner asked for names in hints only, and a toggle is one more control.

### D2. Setup's tabs reuse office Setup's pieces where the props fit
`FloorSetupTab` becomes a thin orchestrator. It holds:
- the selected sub-tab, in component state;
- the per-section drafts, as today;
- the set of dirty and incomplete tabs.

Office's `SetupTabBar` takes office-typed tabs and a payments mode, so the floor gets
its own `setup/SetupTabs.tsx`. It has the same markup and classes (`stage-control
setup-tabs`), so it looks identical.
- **The address.** The sub-tab is not put in the address. Floor addresses name console
  tabs only (`floor-console`), and office Setup's tab is not in the address either.
- **Files.** One file per sub-tab: `ScopeTab`, `ScheduleTab` with `DayRow` and
  `DayDialog`, `FormatsTab` with `FormatFields`, `OfficialsTab`, `PistesTab`, and
  `ParamsTab`.
- **The shared dialog.** `ServesDialog` is the "ne / běžně / rezerva" dialog used by
  pistes and officials. Every dialog is a `Modal`.

### D3. Scope is three booleans on `floor_settings`
`FloorSettings` gains `plan_schedule`, `multi_day` and `plan_officials`, all
non-nullable booleans. They are saved through a new `scope` section on the existing
section endpoint. The service enforces two rules:
- `plan_officials` implies `plan_schedule`;
- `multi_day` off is refused while more than one day is stored.

Every reader of Setup (the planner problem builder, the badges, the officials
assignment, the schedule panel) gets the scope from one function. That function returns
the effective view: hidden things are left out, not deleted.

*Alternative:* keys inside the `params` JSON. Rejected: these gate whole tables, and
typed columns let a query filter on them.

### D4. A discipline's day is a row of `floor_discipline_days`
`floor_discipline_days` is a new table with columns `discipline_id` (PK, FK
`disciplines.id` ON DELETE CASCADE) and `day_id` (FK `floor_days.id` ON DELETE
CASCADE). The primary key is what makes "exactly one day" structural.
- **Saving.** The days section writes it, because the Rozvrh dialog edits it.
- **One-day tournaments.** With `multi_day` off, no row is needed. The effective view
  puts every discipline on the single day.
- **Removing a day.** Its disciplines become dayless, which is stated as incomplete.

`DayPin` leaves the engine and `FloorPin.kind = "day"` leaves the API. The migration
turns stored day pins into rows (D9).

### D5. Pistes and officials serve disciplines through one link shape
Two new tables, `floor_piste_disciplines` and `floor_official_disciplines`, each with
columns `(owner_id, discipline_id, reserve bool)`. The primary key is
`(owner_id, discipline_id)`.

They replace:
- `floor_piste_days`;
- `FloorPiste.reserve`;
- `FloorOfficial.discipline_ids`, a JSON column;
- `FloorOfficial.roles`.

`floor_official_days` stays. It is read only with `multi_day` on.

**Main referees.** `FloorOfficial` gains `main` (bool, not null, default true).
- In the engine, an official carries `main`.
- The planner's `Problem.officials` also states the main referees available per day.
  It uses them only for the warning (`floor-planner`).

**A piste's availability.** In the engine, a piste becomes
`Piste(id, ordinal, regular: frozenset[int], reserve: frozenset[int])` by discipline
id. A piste is usable on a day when it serves one of that day's disciplines. A piste
with neither set never reaches the engine.

### D6. Format columns
In `FloorFormat`:
- **Staffing.** `staffing` (JSON) gives way to `referees_pool` and `referees_elim`
  (int, not null, default 1).
- **The pause.** `slot_pool_overhead` is renamed `pause_between_pools`. New formats get
  10.
- **Points.** New nullable int columns `points_pool`, `points_elim` and
  `points_team_bout`. The service refuses `points_elim` on a team discipline and
  `points_team_bout` on an individual one. The team total, points × team_min², is
  computed, never stored.
- **The take-over.** New `takes_pools_from`, a nullable FK `disciplines.id` with ON
  DELETE SET NULL. The service validates:
  - same weapon, compared case-folded;
  - not self;
  - the source does not itself take over;
  - with a schedule planned, the target's day is not before the source's.
- **The third place.** The `third_place` default becomes true for new formats.

Engine `Format` follows: `referees: tuple[int, int]` for pools and elimination, and
`pause`, `takes_from: int | None`. The points never reach the engine.

### D7. Parameters split into Setup's and the plan's
The `params` JSON on `floor_settings` keeps all values, read and saved by two sections:
- `params`, from Setup: `finals`, which is `"elimination" | "day" | "tournament"`, and
  `min_rest_minutes`;
- `preferences`, from the plan tab: `pool_size`, which is `"larger" | "smaller"`, plus
  `club_weight` and `nationality_weight`.

Each section's save merges its own keys only. The old keys map like this:
- `finals_last: true` becomes `"day"`, which keeps the stored behaviour;
- an absent key reads as the new default `"elimination"`;
- `prefer_larger_pools` becomes `pool_size`.

`PreferencesSection` lives in `frontend/src/floor/plan/` and reuses `useSectionSave`
from `setup/shared.tsx`.

### D8. The engine
- **Days are facts.** `DisciplineFacts` gains `day: int` and `takes_from: int | None`.
  Variant enumeration iterates k only. A discipline that takes over has no k and no
  pool templates.
  - `Choice` keeps `day`, copied from the fact, so stored variants and `Plan.key` keep
    their shape.
- **Reserve escalation.** Each variant is scheduled first on regular pistes, with
  regular referees counted. If that overruns a day, the same variant is scheduled
  again with the reserve pistes and reserve referees of the overrunning day's
  disciplines. The variant records the reserve pistes it used: `Metrics.reserve_used`,
  which is also a dominance axis. The second pass is deterministic, so determinism
  holds.

  *Alternative:* score reserve use as a cost inside one pass. Rejected, because "only
  if needed" is a rule, not a weight.
- **Finals.** `Params.finals: Literal["elimination", "day", "tournament"]`.
  - `"day"` is today's `finals_last`.
  - `"tournament"` moves every template with `final=True` (finals and third-place
    bouts) to the last day's queue, sorted after every non-final template of every
    day. The day-by-day scheduler then places them last. Their piste is any piste
    serving the discipline that is usable on the last day. If none is, the variant is
    infeasible, with the rule named.
- **The take-over.** The target's first round depends on the source's last pool end
  plus the minimum rest, through the existing precedence edge, now pointing at another
  discipline's pools.
- **Officials cap.** The cap is per day: concurrent referee demand (the sum over
  running pistes of their stage's `referees`) ≤ the referees available that day who
  serve at least one of the day's disciplines. This is an over-approximation of what
  per-discipline matching allows (see Risks).
- **Main referees.** These are not a cap. After placement, a sweep over each day's
  concurrency counts the moments where running pistes exceed the main referees
  available, and stores them as `Metrics.main_warnings`. They are not a dominance axis.
- **Assignment.** `engine/officials.py` gives each block a main place.
  - It is filled first, in this preference order: regular main, then regular non-main
    with the block marked, then reserve main, then reserve non-main with the block
    marked.
  - The other places follow the existing order.
  - A block without a main referee is a warning and a `plan` badge condition, never an
    unfilled place.
- **No schedule.** `structure_variants(problem)` returns k-combinations ordered by the
  pool-size preference and then the discipline order. It does no placement.

### D9. A plan without a schedule stores unplaced pools
`FloorPlanActivity.piste_id`, `starts_at` and `ends_at` become nullable. A plan made
with `plan_schedule` off stores one pool activity per pool, with its size and no
placement.
- `planned_pools` reads them as one wave, so the draw's wave constraint is empty.
- Every reader of placed activities filters on `piste_id IS NOT NULL`: the schedule
  panel, slip, the officials blocks, the diff and sensitivity.

*Alternative:* store only the variant's k's and let the draw compute pool sizes.
Rejected: the draw, pool sheets and `today` already read pool activities, and one
shape serves both modes.

### D10. The weapon reaches the floor through the existing adapter
`FloorDiscipline` (`app/floor/roster.py`) gains `weapon: str`, filled in
`app/floor/adapters/office.py::_disciplines` from `discipline.weapon`.

**Imports across the floor boundary.** This change adds none. The adapter already
imports `Tournament` and `DisciplineKind` from `app.models`, and those stay its only
office imports. `app.floor` keeps importing only `db`, `auth`, `errors`, `i18n` and
`config` from the rest of `app`. `tests/floor/test_floor_boundary.py` needs no change.

### D11. An official's name with a link
With "Šermuje jako" set, the API stores the person's name at save time as the
official's `name`, and the form greys out the field. Rendering prefers the roster's
current name while the link resolves, and the stored name once it does not. This keeps
the "link no longer finds a person" row readable.

## Risks / Trade-offs

- [The officials cap over-approximates.] A day may look staffable in the planner while
  the per-discipline assignment cannot fill a place. → The assignment states every
  unfilled place and badges `plan` (`floor-officials`), as it does today. An exact
  matching cap can come later, inside the engine, without changing the spec.
- [The reserve two-pass doubles the cost of an infeasible variant.] → Variants are few
  (k-combinations only, now that days are facts). The second pass runs only on overrun.
- [Finals at the end of the tournament can crowd the last day.] → The overrun is stated
  like any other. This is the owner's choice for tournaments that want it, and the
  default is "v rámci eliminace".
- [Nullable placement columns ripple into every reader.] → D9 names every reader, and a
  test plans with the schedule off and opens each tab.
- [A take-over whose source changes weapon later.] → The service re-validates on every
  format read, and the Disciplíny tab states the broken take-over as incomplete. It is
  never dropped silently.

## Migration Plan

One alembic revision, after the floor revisions:
1. Create `floor_discipline_days`. Fill it from day pins where they exist, and failing
   that from the first stored day. Then delete the `kind = 'day'` pins.
2. Create `floor_piste_disciplines`. For each piste, add every discipline that has a
   format, with `reserve = piste.reserve`. Drop `floor_piste_days` and
   `floor_pistes.reserve`.
3. Create `floor_official_disciplines` from `discipline_ids`, all regular. Drop
   `discipline_ids` and `roles`. Add `floor_officials.main`, true for every existing
   official.
4. `floor_formats`:
   - add `referees_pool` and `referees_elim` from `staffing.referee`, or 1 where it is
     missing;
   - drop `staffing`;
   - rename `slot_pool_overhead` to `pause_between_pools`;
   - add the point and take-over columns.
5. `floor_settings`: add the three scope columns. `plan_schedule = true`.
   `multi_day = (more than one day stored)`. `plan_officials = (any official stored)`.
   Rewrite the `params` JSON keys as in D7.
6. `floor_plan_activities`: make the placement columns nullable.

Because the branch has never been deployed, the mapping matters only for development
databases. A downgrade is provided but lossy: reserve per discipline collapses to "any
discipline reserve".

## Open Questions

- **Point targets** have no defaults. They are optional, and a sheet without one
  leaves the target blank. If the owner wants defaults, for example 5/10, they are one
  constant each.
- **New scope defaults** for a new tournament: schedule on, several days off, officials
  off, i.e. the smallest event. Owner to confirm.
