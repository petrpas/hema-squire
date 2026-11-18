## MODIFIED Requirements

### Requirement: Withdrawal is per entry and stays in the floor
The desk SHALL be able to withdraw a person from one discipline, or from all of them.
Removing an entrant on the Data sheet is the same withdrawal (`floor-data`, The sheet is
the floor's to correct). It is one state, shown on both tabs and undone from either.

A withdrawn entry SHALL NOT count toward its discipline's N.

**Undoing.** A withdrawal can be undone while the discipline's check-in is open.

**The office is untouched.** Withdrawing SHALL NOT cancel, amend or refund anything in
the office. The office console states nothing about it. A refund, where one is due,
remains the organizer's act there.

#### Scenario: A withdrawal does not cancel the registration
- **WHEN** the desk withdraws a fencer from Sabre Open
- **THEN** Sabre Open's N drops by one, and the fencer's registration in the office is unchanged

#### Scenario: Withdrawn at the desk, shown on Data
- **WHEN** the desk withdraws a fencer from Sabre Open
- **THEN** Sabre's Data sheet shows the fencer's row struck through with "Vrátit"

### Requirement: Closing check-in is a gate with its impact shown
For each discipline, the desk SHALL offer "Uzavřít prezenci".

**Before confirming,** it SHALL state:
- the discipline's N: arrived entries that have not withdrawn, or present teams;
- the pool structure the published plan's variant gives for that N;
- the change in its day's last end time against the published plan.

For example: "Uzavřít prezenci šavle: N = 29, vychází 5 skupin místo 6, konec o 25 minut
dřív". Where the new N has no feasible structure, the impact SHALL say so.

**Confirming SHALL:**
- freeze the discipline's snapshot: for each entrant, their key, name, club,
  nationality, HEMA Ratings id and that discipline's rating and rank as the Data sheet
  stated them at that moment, with the floor's corrections and fetched figures included
  (`floor-data`), and for a team discipline each present team and its lineup;
- pin N for the planner, as the check-in gate's pin (`floor-plan`).

**After closing.** Office changes after the close SHALL NOT change the snapshot. No
correction can be made on the Data sheet while the discipline is closed.

#### Scenario: Closing pins N and freezes the list
- **WHEN** the desk closes Sabre's check-in at N = 29
- **THEN** Sabre's snapshot lists the 29, the planner's N for Sabre is pinned to 29, and a registration cancelled in the office afterwards does not change the snapshot

#### Scenario: A corrected rating is what the snapshot keeps
- **WHEN** a fencer's Sabre rating was corrected on the Data sheet to 1550 and the desk then closes Sabre's check-in
- **THEN** the snapshot holds 1550 for that fencer, and the draw seeds by it
