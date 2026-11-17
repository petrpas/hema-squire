## Why

On tournament day the floor console runs on a laptop with a small screen. Today it spends
two full-width bands on navigation and stacks every Setup section in one long column.
Floor Setup also asks for things most tournaments never plan. It asks for judges and
table officials, a schedule from a one-day club event, and officials from an event that
staffs pistes on the spot. And it still lacks things organizers do ask for: point
targets, taking pool results over from a sister discipline, reserve pistes and officials
per discipline, and where the finals go.

This change belongs to the **floor** context only. The one new office fact it needs, a
discipline's weapon, reaches the floor through `floor-roster` and its one adapter, as
the team size bounds already do.

## What Changes

- **Left icon rail.** The floor console's second band of tabs moves to a narrow rail on
  the left. Each tab is an outline icon, and its name appears only in a floating hint
  and to assistive technology. The top bar stays across the screen. The rail stays on
  narrow screens too, where "Rozvrh" becomes its last icon.
- **Setup gets its own small tabs** across the top, as office Setup has: Rozsah, Rozvrh,
  Disciplíny, Rozhodčí, Planše, Parametry.
- **Rozsah (scope)** is a set of ticks that decide what the rest of Setup and the
  console show:
  - "Plánovat rozvrh". Off means no schedule, only the pool structure.
  - "Vícedenní turnaj", under it. Off means one day.
  - "Plánovat rozhodčí". It is available only with the schedule on.
- **Rozvrh (schedule)** is a table of days: datum, od, do, disciplíny, přestávka.
  Disciplines and breaks are ticked in a dialog per day. **A discipline belongs to
  exactly one day.** **BREAKING:** the planner no longer chooses a discipline's day, and
  the day pin is removed.
- **Disciplíny (formats):**
  - the advancing count becomes a choice between "všichni" and a fixed number;
  - the third-place bout defaults to yes;
  - **BREAKING:** the staffing template becomes referees per bout, one number for
    pools and one for the elimination, default 1 and 1. Judges and table officials
    are dropped;
  - the "changeover overhead" becomes "Pauza mezi skupinami", default 10 minutes;
  - new point targets: pool bout, plus either elimination bout (individual) or points
    per team bout with the stated total (team);
  - new "Převzít skupinové výsledky z", which takes the pool results of another
    discipline of the same weapon.
- **Rozhodčí (officials):**
  - **BREAKING:** officials are referees only, so roles go;
  - each referee has a "Hlavní rozhodčí" tick, default yes. Every piste's block wants
    one main referee. A block without one is a tolerated error: it is warned about and
    badged, and never makes a plan infeasible;
  - the row starts with "Šermuje jako" (a roster person). Choosing one greys out the
    name field, and the fencer's name is used;
  - disciplines are ticked in a dialog, as days are. Each ticked discipline is either
    regular or **reserve**, and a reserve official is used only where nobody else can
    be.
- **Planše (pistes):**
  - **BREAKING:** the piste's days and its global reserve flag are removed;
  - a piste is assigned to disciplines, regular or **reserve**. It is planned on for
    those disciplines, a reserve piste only with lower priority;
  - a piste assigned to no discipline stays free for the floor to use on the spot.
- **Parametry:**
  - finals become a three-way choice: within the elimination (default), at the end of
    the day, or at the end of the tournament;
  - the non-choice "pool sizes differ by at most one" row is removed. The rule stays;
  - the pool-size preference (larger or smaller) and the draw weights move to the
    `plan` tab;
  - the minimum rest stays.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `floor-console`:
  - the second band becomes the left icon rail with hints;
  - the narrow screen keeps the rail;
  - the schedule panel is drawn only where the schedule is planned.
- `floor-setup`:
  - Setup sub-tabs and scope ticks;
  - days carry their disciplines, and a discipline belongs to one day;
  - the format's staffing, pause, points and take-over;
  - officials are referees, with per-discipline reserve;
  - pistes by discipline with reserve, without days;
  - the finals placement;
  - parameters leave Setup for the `plan` tab.
- `floor-planner`:
  - a discipline's day is a fact, not a decision;
  - pistes are available per discipline, reserve with lower priority;
  - three finals placements;
  - a plan without a schedule (pool structure only);
  - the pool-size preference has two directions;
  - a taken-over discipline has no pools;
  - officials are counted only when planned;
  - a variant warns where pistes outnumber main referees.
- `floor-plan`:
  - the day pin goes;
  - the pool-size preference and the draw weights are edited on the `plan` tab;
  - re-planning no longer opens reserve pistes;
  - the tab works without a schedule.
- `floor-officials`:
  - referee role only;
  - one main referee per block, a missing one tolerated, stated and badged;
  - pools and elimination staffing;
  - reserve officials per discipline;
  - the whole capability is off unless "Plánovat rozhodčí".
- `floor-draw`:
  - the weights are read from the `plan` tab;
  - without a schedule there are no waves to respect.
- `floor-pools`:
  - pool sheets state the point target;
  - a taken-over discipline has no pools of its own;
  - its Skupiny cell on `today` names its source.
- `floor-bracket`:
  - a taken-over discipline seeds from its source's closed ranking;
  - unplaced entrants are seeded below the placed ones;
  - bracket sheets state the point target.
- `floor-roster`:
  - every discipline also states its weapon.

## Impact

- **Frontend:**
  - `frontend/src/floor/`: `FloorConsole`, `FloorTabBar`, which becomes a rail, and
    the whole of `setup/`, which gets sub-tabs, a scope tab, the dialogs, and
    sections split per sub-tab;
  - `plan/`, which gets a new preferences section;
  - the floor i18n keys;
  - icons from `@tabler/icons-react` (outline), already a dependency.
- **Backend:**
  - `app/floor/models.py`: new and changed `floor_` columns and tables, with an
    alembic migration that maps existing data;
  - `schemas.py`, `setup.py` and `planning.py`;
  - the engine: `model.py`, `variants.py`, `schedule.py`, `officials.py`;
  - `pools.py`, `bracket.py` and the Typst sheets for the point targets and the
    take-over.
- **Boundary:** the floor boundary is unchanged. The weapon is added to
  `FloorDiscipline` in `app/floor/roster.py` and filled in `app/floor/adapters/office.py`,
  the only floor file that reads office modules.
- **Data:** existing floor setups migrate:
  - every discipline goes to its pinned day, and failing that to the first day, and day
    pins are removed;
  - each piste goes to every discipline as regular, or as reserve if it was reserve;
  - the staffing template keeps its referee count for both pools and elimination;
  - the overhead is kept as the pause;
  - officials keep their disciplines as regular.
