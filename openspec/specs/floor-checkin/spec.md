# floor-checkin Specification

## Purpose
TBD - created by archiving change add-floor-checkin. Update Purpose after archive.
## Requirements
### Requirement: The desk ticks persons, once
The `checkin` tab SHALL list every person on the floor roster once. Each row shows:
- the person's name, club and nationality;
- the disciplines and teams the person entered;
- the paid mark of each entry.

The list SHALL be searchable by name and club.

**What a tick does.** Ticking a person SHALL mark them arrived in every discipline they
entered, and as a member of every team they appear on.

**Payment.** The paid mark is shown and decides nothing. An unpaid person can be ticked
(`floor-roster`, Payment marks an entry and filters nothing).

#### Scenario: One tick for two disciplines
- **WHEN** the desk ticks a fencer entered in Longsword Open and Sabre Open
- **THEN** both entries count as arrived

#### Scenario: Unpaid is shown, not blocked
- **WHEN** the desk ticks a fencer whose entry is unpaid
- **THEN** the tick is recorded, and the row still shows the entry unpaid

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

### Requirement: A team fields a lineup for the day
For each team in a team discipline, the desk SHALL set the day's lineup.

**Who can be in it.** The lineup is chosen from the team's members on the floor roster.
A member absent from the roster MAY be added by name, as a floor-only person. A
floor-only person exists only on the floor, carries a key the floor issues, and is
never written to the office.

**What it means.** The lineup SHALL be within the discipline's team size bounds. A team
is present when at least the minimum number of its lineup has arrived. The lineup's
arrived members are the team's pool participants (`floor-planner`).

#### Scenario: A substitute on the day
- **WHEN** a team's member did not come, and the captain names "Petr Dvořák" in their place at the desk
- **THEN** Petr Dvořák joins the lineup as a floor-only person, and the team's roster in the office is unchanged

#### Scenario: A team short of its minimum is not present
- **WHEN** a team discipline requires 3 and only 2 of a team's lineup have arrived
- **THEN** the team is not present, and its row says it is short by one

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

### Requirement: Reopening states what it invalidates
A closed check-in SHALL be reopenable.

**Before confirming,** reopening SHALL list what it invalidates:
- the N pin;
- the snapshot;
- the discipline's draw, where one exists.

**Recorded results.** Reopening SHALL be refused while any bout of the discipline has a
recorded result. That refusal names the recorded bouts.

#### Scenario: Reopening after the draw
- **WHEN** the organizer reopens Sabre's check-in after its draw was made but before any bout is recorded
- **THEN** the confirmation lists the snapshot, the N pin and the draw as invalidated, and confirming discards all three

#### Scenario: Reopening after a result is refused
- **WHEN** a Sabre pool bout has a recorded result
- **THEN** reopening Sabre's check-in is refused and names that bout

### Requirement: Check-in badges
The `checkin` tab SHALL carry a badge when a discipline whose first activity in the
published plan starts within 30 minutes still has check-in open.

#### Scenario: Open check-in before the first pool
- **WHEN** Rapier's first pool is planned for 10:00 and its check-in is still open at 09:35
- **THEN** the `checkin` tab carries a badge, and Rapier is named among what waits

