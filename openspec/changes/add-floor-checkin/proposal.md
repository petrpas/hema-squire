## Why

On the morning of the tournament the plan's N is a guess. Registrations are not the
people who came. The desk at the entrance has to say three things: who arrived, who
withdrew, and which members each team fields today. When check-in closes for a
discipline, its N becomes a fact and the planner can count on it.

The owner's UX document makes check-in the one step done by person rather than by
discipline. A human arrives once. The closing is per discipline.

The `today` tab is the day's home screen. It is the only place that shows both axes at
once: discipline × step.

**Context:** floor. Check-in state lives only in the floor (owner decision 2026-11-16).
Office registrations, payments and team rosters are not touched.

## What Changes

- **Prezence (`checkin`):**
  - **Arrival.** One row per person on the floor roster, searchable by name and club.
    Each row lists the person's disciplines and teams and the paid mark. One tick marks
    the person arrived in every discipline they entered.
  - **Withdrawal.** Withdrawal is per entry: from one discipline, or from all.
  - **Team lineups.** For a team discipline, each team's lineup for the day is chosen
    from its members, within the discipline's team size bounds.
    - A member missing from the office roster can be added by name as a floor-only
      person.
    - A team is present when at least the minimum of its lineup has arrived.
  - **Office changes before close.** Until a discipline's check-in closes, the desk
    reads the floor roster live. An entry added or cancelled in the office appears or
    disappears.
- **Closing check-in per discipline is a gate:**
  - **Before confirming,** it states the impact computed by the planner: N, the pool
    structure, and the change in the day's end. Example: "N = 29, vychází 5 skupin
    místo 6, konec o 25 minut dřív".
  - **Confirming** freezes the discipline's snapshot of entrants, with their name,
    club, nationality, HEMA Ratings id, rating and rank as they stood. It also pins N
    for the planner.
  - **Reopening** is possible, and lists what it invalidates.
- **Přehled (`today`):**
  - **The matrix.** It has disciplines as rows and steps as columns (Prezence, Skupiny,
    Pavouk, Výsledky), with each cell's state.
  - **Navigation.** A cell links to the step's tab at that discipline, through a new
    address segment, for example `/organizer/:slug/floor/pools/LS`.
  - **Slip.** Each discipline shows how far it is behind or ahead of the published plan.
  - **Waiting.** A "waiting on you" list collects every tab's badge conditions.
  - **Refresh.** The tab refreshes by polling, quietly.

## Capabilities

### New Capabilities
- `floor-checkin`: arrival, withdrawal, team lineups and floor-only members. It also
  covers the close gate with its impact and snapshot, and reopening.
- `floor-today`: the discipline × step matrix, the per-discipline address, slip, the
  waiting list, and the refresh.

### Modified Capabilities
None. `floor-plan`'s pins from gates already provide for the N pin, and `floor-console`
already lets each capability add badge conditions.

## Impact

- **Backend:**
  - `app/floor/checkin.py`;
  - tables `floor_arrivals`, `floor_withdrawals`, `floor_lineups`,
    `floor_local_persons`, `floor_snapshots` and `floor_snapshot_entrants`, migration
    `floor_0003`;
  - endpoints under `/floor/checkin/*` and `/floor/today`.
- **Office:** `account_deletion.py` classifies the new columns. Snapshot names are
  copies of roster names, kept as `team_members.name` is.
- **Frontend:**
  - `frontend/src/floor/checkin/` and `frontend/src/floor/today/`;
  - `routes.ts`: `floorPath(slug, phase?, discipline?)`.
