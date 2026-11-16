## Context

**Context: floor.** After `add-floor-planner`, a published plan exists, with N per
discipline counted from registrations. Check-in turns registrations into the people
present.

**What the owner documents say.**
- Check-in is per person. Closing is per discipline.
- Live office link until close.
- Gates show their impact and can be reopened.

**Owner decisions of 2026-11-16.**
- Withdrawals and lineups live only in the floor.
- Teams have individual pools of their members.

## Goals / Non-Goals

**Goals:**
- Arrival, withdrawal, lineups and floor-only members.
- A per-discipline close gate with its impact, snapshot and N pin. Reopening with its
  invalidations.
- The `today` matrix, the per-discipline address, slip, the waiting list, and quiet
  refresh.

**Non-Goals:**
- Any write to office registrations, rosters or payments.
- A kiosk or self check-in. The desk is the organizer's console.
- QR codes on registrations.

## Decisions

### D1. State is recorded as events over roster keys
| Table | Holds |
|---|---|
| `floor_arrivals` | `tournament_id`, `person_key` (unique per tournament), `at`, `by` |
| `floor_withdrawals` | `tournament_id`, `entry_key` (`<person_key>@<discipline_id>` or `team:<id>`), `at`, `by` |
| `floor_lineups` | `tournament_id`, `team_key`, `person_key`, `ordinal` |
| `floor_local_persons` | `tournament_id`, `id`, `name`, `club`, `nationality`. Key `local:<id>` |
| `floor_snapshots` | `tournament_id`, `discipline_id` (unique while closed), `closed_at`, `closed_by`, `n` |
| `floor_snapshot_entrants` | `snapshot_id`, `entrant_key`, `kind` (person / team), `name`, `club`, `nationality`, `hr_id`, `rating`, `rank`, `members` (JSON person keys, teams only) |

**How undoing works.** Undoing an arrival or a withdrawal deletes its row. The floor
keeps no audit of desk clicks, because the desk is a working surface, not a ledger.

**Floor-only persons.** They are the floor's own small source of persons. Their keys
use a prefix the office never issues (`local:`). Everything above the roster reads
persons through one function, `floor.persons(tournament)`. It merges the port's persons
with floor-only persons, so no consumer cares where a person came from. This is also the
seam a second roster adapter will use.

### D2. N and presence are computed, not stored, until close
**N.** N for a discipline is read from the live roster minus withdrawals, intersected
with arrivals. For a team discipline it is the teams whose lineup has at least
`team_min` arrived. The pool participants of a team discipline are the arrived lineup
members.

**At close.** The values are copied into the snapshot. From then on every floor reader
takes that discipline's entrants from the snapshot, through the same
`floor.entrants(tournament, discipline)` function. It returns live entrants before close
and the snapshot after.

### D3. The close gate's impact runs the planner
The impact calls the planner with the published plan's variant and the new N pinned. It
returns k, the sizes and the day's last end, and is compared with the published plan.
The planner is fast enough (`add-floor-planner` D3) to run on each "Uzavřít prezenci"
dialog. Confirming:
1. writes the snapshot;
2. adds a `floor_pins` row with `gate = "checkin:<discipline_id>"`;
3. does not re-plan. Re-planning is the organizer's act (`floor-plan`).

### D4. Reopening cascades, but never over results
Reopening deletes the snapshot and the gate's pin. Where `floor-pools` has stored a draw
for the discipline, it deletes that too. It is refused while any bout result is stored.

**Why not cascade over results.** Throwing away recorded results is never the side
effect of a check-in correction. `floor-pools` adds its draw to the invalidation list
through a hook registry in `app/floor/gates.py`. Each capability registers what reopening
a gate discards and what refuses it. The check-in module then never imports the pools
module.

### D5. Today, slip and waiting
**Cell states.** `GET /floor/today` returns, per discipline, each step's state. Each
capability registers a state function in `app/floor/steps.py`. This change registers
Prezence.

**Slip.** It is the difference between the published plan's start of the discipline's
current activity and its actual start, from `app/floor/progress.py`. Until pools exist
it is absent.

**The waiting list.** It is the union of the badge conditions already computed for
`/floor/summary`.

### D6. Refresh by polling
The app has no push channel, and adding one for this would be infrastructure out of
proportion. Fifteen-second polling of two small GET endpoints serves two desks and an
organizer.

**Respecting the design rules.**
- Responses carry an `ETag`, so an unchanged state costs a 304.
- The client keeps fields being edited and the scroll position.
- A stale state is stated as text ("aktualizováno v 11:04"), never with a spinner
  (`design-system`).

### D7. Imports that cross the floor boundary
None new.
- `checkin.py` reads `app.floor.models`, the persons and entrants functions,
  `app.floor.planning` (for the impact), `app.db` and `app.errors`.
- The roster arrives through the existing adapter.

### D8. Decisions made during implementation (made by me; for the owner's review)
Decided on 2026-11-17 while the owner was away, as asked:
- **The N pin is a pin of its own kind, `n`.** It is listed on the Plan tab with its
  gate, as every gate's pin is. The planner reads N from the snapshot, so the engine
  needs no N pin of its own.
- **The close impact keeps the published k where the new N allows it.** Otherwise it
  takes the feasible k nearest to it. The day's end is the published variant scheduled
  again with the new N.
- **A team discipline's N is its present teams.** Its pool participants are their
  arrived lineup members. A team with no stated lineup fields its roster members.
- **Check-in team bounds come from the port.** `FloorDiscipline` gains `team_min` and
  `team_max`, filled by the adapter from objects it already reads.
- **Desk authors are account ids**, as plan authors are (`add-floor-planner` D10).
- **Polling uses `Cache-Control: no-cache` with the `ETag`.** The browser then
  revalidates on every poll instead of serving its own copy, and the 304 stays cheap.
- **Lineups are saved as each tick is made.** The lineup is not a draft with a save
  button, because a lineup is set at the desk while the captain stands there.

## Risks / Trade-offs

- **[Two desks tick the same person at once.]** → `floor_arrivals` is unique per person,
  so the second insert is a no-op that answers "already arrived".
- **[A floor-only person is invisible to the office's GDPR machinery.]** → Classify
  `floor_local_persons.*` in `account_deletion.py` as organizer-entered names
  (`kept`). They are tied to no account. Retention of floor data is a question for
  `add-floor-results`.
- **[A team member arrives under another team too.]** → Arrival is per person. A person
  in two lineups of one discipline is refused at lineup save.

## Open Questions

None left. Resolved 2026-11-16 (owner): a substitute added on the floor is never
written back to the office team roster. The floor does not write to the office.
