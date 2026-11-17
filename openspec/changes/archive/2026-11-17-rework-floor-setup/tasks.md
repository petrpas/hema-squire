## 1. Roster and data model

- [x] 1.1 Add `weapon` to `FloorDiscipline` in `app/floor/roster.py`, and fill it in
  `adapters/office.py::_disciplines`. Confirm `tests/floor/test_floor_boundary.py`
  still passes unchanged.
- [x] 1.2 Models (`app/floor/models.py`):
  - add the `FloorSettings` scope columns;
  - add `floor_discipline_days`, `floor_piste_disciplines` and
    `floor_official_disciplines`;
  - change `FloorFormat`: referees per stage, `pause_between_pools`, the point columns,
    `takes_pools_from`;
  - add `FloorOfficial.main` (default true);
  - drop `FloorPisteDay`, `FloorPiste.reserve`, `FloorOfficial.roles` and
    `FloorOfficial.discipline_ids`;
  - make the `FloorPlanActivity` placement columns nullable.
- [x] 1.3 Write the alembic revision with the data mapping of design "Migration Plan",
  and a lossy downgrade. Run upgrade and downgrade on a development database.

## 2. Setup service and API

- [x] 2.1 Add the `scope` section: schema, read with defaults, and save. Refuse
  officials without a schedule, and one day while several are stored.
- [x] 2.2 Add the effective-setup function. It hides by scope and puts every discipline
  on the single day when `multi_day` is off. Make every reader (badges, planner,
  officials, schedule) use it.
- [x] 2.3 Days section:
  - each day carries its discipline ids, and the save writes `floor_discipline_days`;
  - "dayless discipline" becomes an incomplete condition when `multi_day` is on.
- [x] 2.4 Pistes section:
  - each piste carries its serves list (regular or reserve), and has no days;
  - "no piste serves it as regular" becomes an incomplete condition.
- [x] 2.5 Officials section: no roles, a `main` tick (default true), a serves list, and
  days only when `multi_day` is on.
  With a person link, the stored name is the person's name.
- [x] 2.6 Formats section:
  - referees per stage, default 1/1, required only with `plan_officials`;
  - the pause, default 10;
  - point targets, with the kind-specific refusals;
  - the take-over and its validations;
  - the third place defaults to true.
- [x] 2.7 Split `params` into the `params` section (finals placement, min rest) and the
  `preferences` section (pool size, weights). Each save merges only its own keys.
- [x] 2.8 Remove the day pin from the pins API, and refuse `kind = "day"`.
- [x] 2.9 Tests in `tests/floor`:
  - scope gating;
  - one day per discipline;
  - take-over validation (weapon, chains, day order);
  - preference/params merge;
  - the migration mapping of day pins.

## 3. Engine

- [x] 3.1 `engine/model.py`:
  - `DisciplineFacts.day` and `takes_from`;
  - `Piste` by regular and reserve discipline sets;
  - `Format.referees` and `pause`;
  - `Params.finals` and `pool_size`;
  - `Problem.schedule` and officials per day and discipline, with main referees per
    day;
  - remove `DayPin`.
- [x] 3.2 `variants.py`: enumerate k only. A take-over discipline has no k. Order by the
  pool-size preference in either direction. Add `reserve_used` to dominance.
- [x] 3.3 `schedule.py`:
  - pistes per discipline, and the pause after a pool;
  - take-over precedence on the source's pools;
  - the three finals placements, with "tournament" moving finals and third-place bouts
    to the last day;
  - the referee cap per stage;
  - `Metrics.main_warnings`, the moments where running pistes exceed the main referees
    (not a dominance axis).
- [x] 3.4 Reserve escalation: a second pass with the reserve pistes and referees of an
  overrunning day. Record the reserve pistes used.
- [x] 3.5 `structure_variants` for plans without a schedule.
- [x] 3.6 Hypothesis tests:
  - determinism with reserves;
  - a reserve never used when regular pistes suffice;
  - finals placement invariants for all three modes;
  - a take-over target never starts before its source's last pool ends plus the rest;
  - schedule-less variants equal the feasible k-combinations;
  - main-referee warnings never change feasibility or the order of variants.

## 4. Planning, draw, officials, pools, bracket

- [x] 4.1 `planning.py`: build the `Problem` from the effective setup. Store unplaced
  pools for a schedule-less plan. Filter placed activities in the diff, the
  sensitivity and the schedule panel. Publishing obstacles follow the scope.
- [x] 4.2 `pools.py` (draw): weights from `preferences`. One wave, with no wave
  constraint, when the plan has no placement. No draw for a take-over discipline.
- [x] 4.3 `officiating.py` and `engine/officials.py`:
  - referee-only blocks per stage, split at the pause;
  - reserve officials only where no regular can fill a place, marked reserve;
  - one main place per block, filled in the order regular main, regular non-main,
    reserve main, reserve non-main;
  - a block without a main referee is marked "bez hlavního rozhodčího", listed among
    the warnings and badges `plan`, and never refuses publication;
  - nothing at all with `plan_officials` off.
- [x] 4.4 Pools state and `today`: a take-over discipline reads "převzaty z <source>",
  and its `pools` tab links to the source.
- [x] 4.5 `bracket.py`: seed a take-over target from the source's closed ranking.
  - Unplaced fencers go below, by HR rating and then by lot.
  - Teams short of k placed members go below.
  - Draw the lot once at confirmation and store it.
  - Require the source closed.
  - Name the unplaced entrants in the confirmation.
- [x] 4.6 Typst sheets:
  - pool sheet point target, with piste and time omitted when unplaced;
  - bracket sheet elimination target, or team points per bout and the total.
  - Officials rozpis without a role column.
- [x] 4.7 Tests in `tests/floor` for 4.1–4.6. Run
  `pytest tests/floor -q --maxfail=3 --tb=short --show-capture=no --hypothesis-profile=dev`.

## 5. Frontend: console rail

- [x] 5.1 In `tabs.ts`, add the icon per tab (`@tabler/icons-react` outline). Check
  each name exists in the installed version.
- [x] 5.2 Replace `FloorTabBar` with `FloorRail`:
  - a vertical tablist with up/down arrows;
  - a static hint on hover and focus-visible;
  - the badge and unsaved mark on the icon and in the accessible name.
- [x] 5.3 `FloorConsole`: grid of rail, work and an optional schedule panel. No panel
  and no "Rozvrh" tab when the schedule is not planned. The rail stays on narrow
  screens.
- [x] 5.4 CSS with tokens only:
  - no shadow, no transition, no radius above 2px outside the tokens;
  - touch target sizes per `responsive-layout`;
  - check both skins.
- [x] 5.5 Update `floorConsole.test.tsx` for the rail: order, hint text, accessible
  names with the badge, and the narrow ninth tab.

## 6. Frontend: Setup tabs

- [x] 6.1 `floorApi.ts`: the new section types (scope, days with disciplines, serves
  lists, format fields, params/preferences split), and remove the dropped fields.
- [x] 6.2 `setup/SetupTabs.tsx`, and a thin `FloorSetupTab` orchestrator:
  - sub-tab state, opening on the first incomplete tab;
  - incomplete and unsaved markers;
  - drafts kept across tabs.
- [x] 6.3 `ScopeTab`: three ticks. "Vícedenní turnaj" is nested and disabled without
  the schedule. "Plánovat rozhodčí" is greyed out without the schedule.
- [x] 6.4 `ScheduleTab`, `DayRow` and `DayDialog`:
  - columns datum, od, do, disciplíny, přestávka;
  - the dialog ticks disciplines, naming the day each currently belongs to, and edits
    breaks;
  - one-day mode reads "všechny".
- [x] 6.5 `FormatsTab` and `FormatFields`:
  - "všichni / pevné číslo";
  - the third place;
  - referees for pools and elimination (only with officials);
  - "Pauza mezi skupinami";
  - the point targets, with the team sentence "Počet bodů na střet: [n], celkem do
    N bodů";
  - "Převzít skupinové výsledky z", offering the same weapon only, with the pool
    fields hidden for a target.
- [x] 6.6 The `ServesDialog` ("ne / běžně / rezerva") as a `Modal`. Use it in
  `PistesTab`, which has no days and states free pistes, and in `OfficialsTab`.
- [x] 6.7 `OfficialsTab`: "Šermuje jako" first, which greys out the name. A "Hlavní
  rozhodčí" tick, default yes. Days only in multi-day mode. No roles. On the `plan` tab,
  show the variant's main-referee warnings, and mark the main place and the blocks
  without a main referee in Obsazení.
- [x] 6.8 `ParamsTab`: the finals placement (three choices) and the minimum rest, each
  with its kind in words. No pool-size rule row.
- [x] 6.9 `plan/PreferencesSection`: pool size larger/smaller and the two weights,
  with their own save. Hide the sensitivity, the Obsazení section and the place and
  sequence pins without a schedule. Remove the day pin UI.
- [x] 6.10 i18n (cs, en): new labels in sentence case, no exclamation marks. Remove
  the keys for judge, table and overhead.
- [x] 6.11 Tests: sub-tab markers and drafts, scope hiding, the day dialog moving a
  discipline, the team points sentence, the take-over options by weapon, and the
  serves dialog.

## 7. Finish

- [x] 7.1 From `frontend/`: `npm run typecheck`, `npm run check`, `npm test`.
- [x] 7.2 From `backend/`: `uv run ruff check .` and `uv run basedpyright`.
- [x] 7.3 Run the app on a laptop-sized window (1366×768) and a phone width. Check the
  rail, the hints, the Setup tabs in both skins, and a schedule-less tournament end to
  end.

## 8. Found in the 7.3 run

- [x] 8.1 Publishing a new plan discards every unannounced draw; an announced draw stays.
  The publishing confirmation says so. Tests in `tests/floor/test_floor_pools.py`.
- [x] 8.2 Without a schedule the draw names no wave, in the pools or in the score.
- [x] 8.3 The pin field reads "Počet skupin", not the pin line's template.
- [x] 8.4 The piste tag is dropped (owner decision 2026-11-17: nothing read it), by its own
  revision `floor_0009`, since development databases already carry `floor_0008`.
