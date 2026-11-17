## MODIFIED Requirements

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
