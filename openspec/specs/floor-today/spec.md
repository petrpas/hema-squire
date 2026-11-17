# floor-today Specification

## Purpose
TBD - created by archiving change add-floor-checkin. Update Purpose after archive.
## Requirements
### Requirement: Přehled shows discipline × step
The `today` tab SHALL draw a matrix. Its rows are the tournament's disciplines, in
tournament order. Its columns are the steps, in this order:
- Prezence
- Skupiny
- Pavouk
- Výsledky

Each cell states its step's state for that discipline in words.

**Prezence states.** This change defines them: "otevřená" or "uzavřená". The other
columns read "čeká" until their capabilities define more.

**The only place for both axes.** The matrix is the only place where both axes are seen
at once.

#### Scenario: Three disciplines at eleven
- **WHEN** Sabre's check-in is closed, and Longsword's and Rapier's are open
- **THEN** the Prezence column reads "uzavřená" for Sabre and "otevřená" for the other two

### Requirement: A step's tab opens at a discipline
A step tab SHALL accept a discipline in its address: `/organizer/:slug/floor/:phase/:discipline`.
The discipline is given by its slug, and the tab opens with that discipline current in
its discipline strip (`floor-console`, Step tabs choose their discipline by tabs, kept
across the console).

**Building the address.** It is built from `floorPath(slug, phase, discipline)`.

**From the matrix.** Each cell of the matrix SHALL link to its step's tab at its
discipline. Following a cell makes that discipline the one kept across the console.

**An unknown discipline.** A slug the tournament does not have SHALL resolve as an
address without a discipline: the discipline last chosen, or the strip's first.

#### Scenario: From a cell to the step
- **WHEN** the organizer follows the Skupiny cell of Sabre
- **THEN** the `pools` tab opens with Sabre current, at `/organizer/cup/floor/pools/SB`

#### Scenario: A cell's discipline is kept
- **WHEN** the organizer follows the Skupiny cell of Sabre and then follows the rail to `results`
- **THEN** `results` opens at Sabre

### Requirement: Slip and what is waiting
For each discipline with a published plan, the matrix SHALL state the slip: how many
minutes its current step runs behind or ahead of the published plan. It is computed from
the progress later capabilities record. Until they exist it reads nothing.

**The waiting list.** Below the matrix, the tab SHALL list everything that waits on the
organizer, from every tab's badge conditions. Each item links to where it is resolved.

#### Scenario: Waiting items link to their tab
- **WHEN** Rapier's check-in is open 20 minutes before its first pool
- **THEN** the waiting list names it and links to `checkin` at Rapier

### Requirement: Přehled refreshes quietly
While open, the `today` and `checkin` tabs SHALL refresh their data every 15 seconds.
A refresh SHALL NOT:
- animate;
- show a spinner;
- move the page's scroll position;
- disturb a field being edited.

A failed refresh SHALL state, as text, when the data was last refreshed.

#### Scenario: A second desk's tick appears
- **WHEN** a second desk ticks a fencer
- **THEN** the first desk's list shows the tick within 15 seconds, without any animation

