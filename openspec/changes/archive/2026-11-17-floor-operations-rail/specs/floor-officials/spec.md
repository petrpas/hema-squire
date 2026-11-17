## MODIFIED Requirements

### Requirement: The assignment follows the plan
The assignment SHALL be re-run for the affected blocks when:
- a new plan version is published, or
- a draw is announced (club and fencing conflicts become known).

Blocks the change does not touch keep their officials.

**On screen.** The `schedule` tab SHALL name each block's officials.

**Asking for a re-run.** The organizer can also ask for a re-run, from the `plan` tab's
operations panel (`floor-console`, A tab's operations stand in a panel on the right).

#### Scenario: A draw reveals a conflict
- **WHEN** Sabre's draw puts a referee's clubmate in the pool of the referee's block
- **THEN** the assignment for that block is re-run, and the conflict is removed or listed

#### Scenario: Officials on Rozvrh
- **WHEN** the organizer opens `schedule` after the assignment has run on a published plan
- **THEN** each block on the grid names its officials

### Requirement: The assignment prints
The floor SHALL print:
- a one-page rozpis per official, listing their blocks with day, piste, time and
  discipline, and marking the blocks where they hold the main place;
- a sheet per piste, listing its blocks and officials.

Both are PDF. They are printed from the `plan` tab's operations panel.

#### Scenario: An official's rozpis
- **WHEN** the organizer prints Eva's rozpis from the `plan` tab's operations panel
- **THEN** one page lists every block Eva is assigned to, in time order

### Requirement: Officials are planned only when asked for
The officials assignment SHALL exist only with "Plánovat rozhodčí" on (`floor-setup`).
Otherwise:
- no assignment is made or stored;
- the `plan` tab has no "Obsazení" section, and its operations panel offers no re-run
  and no officials' prints;
- the `schedule` tab names no officials;
- nothing in this capability badges a tab.

An assignment stored while the tick was on is kept, hidden, and is shown again when the
tick is turned back on and the assignment re-run.

#### Scenario: No officials, no Obsazení
- **WHEN** "Plánovat rozhodčí" is off and a plan is published
- **THEN** the `plan` tab shows no "Obsazení" section and the `schedule` tab names no officials
