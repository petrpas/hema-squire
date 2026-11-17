## Why

An organizer has to answer the same questions half a year ahead, a week before the
tournament, and at eleven on the day:
- How many pools does each discipline get?
- Which day does it run?
- When does each pool and each elimination round start, and on which piste?

Today they answer them on paper. The owner document "HEMA Squire: formalizace plánovače
turnaje" (2026-11-16) frames every one of these questions as one problem:

```
Plan = solve(Facts + Decisions(free | pinned) + Preferences + Constants)
```

Every output is a projection of that one plan. This change builds the solver and the
plan it produces. Check-in, pools and the bracket then act on that plan.

**Context:** floor. No office module is touched.

## What Changes

- **A pure engine in `app/floor/engine/`:**
  - It takes a frozen `Problem` and returns plans and their explanations. It uses the
    standard library only and has no clock (owner decision 2026-11-16: no OR-tools).
  - **Structure.** For each discipline it computes the feasible pool counts `k`. Sizes
    are ⌊N/k⌋ and ⌈N/k⌉ within the format's range. It also computes the bracket size
    from the advancing count. A team discipline's pools are counted in members and its
    bracket in teams.
  - **Schedule.** List scheduling places every activity on a piste and a start time.
    An activity is a pool, an elimination round's bout, or a final. Scheduling respects:
    - days, breaks and piste availability;
    - precedence: pools, then rounds, then finals at the end of the day;
    - minimum rest;
    - concurrent pistes capped by the officials available for the staffing template.

    Scheduling never uses reserve pistes in a first plan.
  - **Variants.** It enumerates `k` per discipline, and the day of each discipline not
    pinned to one. It keeps the variants no other variant dominates and orders them by
    the soft preferences. Hard rules and pins shrink the space. Where nothing survives,
    the engine names the rule or pin that removed the last variant.
  - **Draw handover.** For each pair of disciplines that share persons and overlap in
    time, it states the time windows the shared persons must avoid. The draw reads
    these exclusion sets. It also lists the bracket rounds where shared persons may
    collide.
  - **Sensitivity.** It reports the entrant counts at which a discipline's structure
    changes. It also reports what an extra or a missing piste would change, and names
    the limiting resource (pistes or officials).
- **The plan, versioned.**
  - A `Plan` is stored as a version with its activities and metrics.
  - There is one working plan and at most one published plan.
  - The working plan diffs against the published plan: what moved, what is new, what
    is gone.
  - Publishing is a gate. It lists its obstacles before it can be confirmed, the way
    the office `PUBLISH` tab does.
- **Pins.** Five decisions can be pinned:
  - a discipline's day;
  - a discipline's `k`;
  - an activity's piste and start;
  - a fixed sequence of disciplines;
  - a frozen past.

  A pinned decision is a fixed value the engine does not move. Pins are how a
  published schedule, a closed gate or the morning's events stop the planner from
  moving things.
- **Re-planning.** "Přeplánovat" builds a new working version from the current state. It
  never happens on its own:
  - activities started before now are frozen;
  - reserve pistes become available;
  - the diff against the published version is shown before anything is published.
- **The Plan tab.** It shows:
  - variants side by side with their metrics;
  - pins, which can be added and removed;
  - sensitivity;
  - the publish gate.
- **The schedule panel.** It draws the published plan as piste × time for the chosen
  day. Where a working plan exists, it also draws that plan with its changes marked
  against the published one.

## Capabilities

### New Capabilities
- `floor-planner`: the engine's behaviour. Covers structure, scheduling, variants,
  explanations, the draw handover and sensitivity, as observable through the plan it
  produces.
- `floor-plan`: plan versions, pins, publishing and its gate, diffing, re-planning, the
  Plan tab and the schedule panel.

### Modified Capabilities
- `floor-console`: the default tab becomes `today` once a plan is published, which
  `floor-console` already states. The `plan` tab and the schedule panel stop being
  placeholders. No requirement text changes, so there is no delta.

## Impact

- **Backend:**
  - new `app/floor/engine/{model,structure,schedule,variants,sensitivity}.py`;
  - new `app/floor/planning.py`, the service that builds the `Problem` from Setup and
    the roster port, and stores plans;
  - tables `floor_plans`, `floor_plan_activities`, `floor_pins`, migration
    `floor_0002`;
  - endpoints under `/floor/plan/*`.
- **Office:** `account_deletion.py` gains string classifications for the new columns.
  Floor tables refer to persons only in check-in and later changes, so this change adds
  none that names a person.
- **Frontend:** `frontend/src/floor/plan/` and the schedule panel. It is drawn as static
  SVG or table markup, with no animation and no chart library.
- **Dependencies:** none.
