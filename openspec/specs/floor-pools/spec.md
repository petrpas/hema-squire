# floor-pools Specification

## Purpose
TBD - created by archiving change add-floor-pools. Update Purpose after archive.
## Requirements
### Requirement: The pools tab follows the discipline's state
The `pools` tab SHALL show the selected discipline in one of four states:
- **draw:** before the announcement (`floor-draw`);
- **running:** after the announcement, while any bout is unrecorded;
- **complete:** every bout is recorded, and the pools are not yet closed;
- **closed:** the ranking is frozen.

Each state's content replaces the previous one's. The tab itself is always present.

**On `today`.** The Skupiny column of `today` SHALL state the same four states as
"čeká", "běží", "dokončeny" and "uzavřeny".

#### Scenario: The matrix follows the pools
- **WHEN** Sabre's draw is announced and one bout is recorded
- **THEN** Sabre's Skupiny cell on `today` reads "běží"

### Requirement: Pool sheets list the bouts in order
Every announced pool SHALL have a sheet stating:
- its discipline, number, piste and planned start;
- its fencers;
- its bouts, in the standard order for its size.

**Printing.** Sheets SHALL print as PDF from the templates adopted from `hema-agent`.

#### Scenario: A pool of six has fifteen bouts
- **WHEN** a pool of six fencers is announced
- **THEN** its sheet lists fifteen bouts in the standard order for six

### Requirement: Bouts are recorded by the adopted model
A bout result SHALL be recorded as the adopted `hema-agent` model records it:
- each side's score;
- each side's outcome: Win, Loss, Draw or No;
- an optional note, such as a walkover or a medical.

**How results are entered.** The console SHALL offer two ways:
- bout by bout;
- transcribing a whole paper sheet at once, for tournaments where one person enters at
  a table.

**Correcting.** A recorded result can be corrected until the discipline's pools are
closed. A correction replaces the result, and the floor keeps who changed it and when.

#### Scenario: A whole sheet is transcribed
- **WHEN** a pool of five's paper sheet is entered as one form of ten bouts
- **THEN** all ten bouts are recorded, and the pool reads complete

### Requirement: Standings are the adopted calculation
A pool's standings, and the discipline's overall pool ranking across its pools, SHALL be
computed by the calculation adopted from `hema-agent`'s `compute_pool_stats`. It states,
per fencer:
- V, the victories;
- M, the bouts;
- V/M;
- TS, touches scored;
- TR, touches received;
- the index.

These rules are not restated here. They are the adopted solution's (owner decision
2026-11-16).

**Warnings.** The adopted consistency checks SHALL be shown as warnings on the pool:
- a fencer with fewer recorded bouts than expected;
- a pool whose touches scored and received do not balance.

#### Scenario: An unbalanced pool is flagged
- **WHEN** a pool's recorded touches scored total 41 and touches received total 39
- **THEN** the pool states the imbalance as a warning

### Requirement: Closing the pools is a gate
"Uzavřít skupiny" SHALL be offered once every bout of the discipline is recorded.

**Before confirming,** it SHALL state:
- the overall pool ranking;
- the advancing count from the format;
- who advances.

**Confirming** freezes the ranking that seeds the elimination.

**Reopening** is refused once any elimination bout of the discipline has a result.

#### Scenario: Who advances is shown before closing
- **WHEN** the format advances 16 of 29 fencers
- **THEN** the confirmation lists the 16 by their pool ranking, and the 13 who do not advance

### Requirement: A call list names who is wanted next
The `pools` tab SHALL offer a call list. It names the fencers of the next wave's pools
that have not started, with their pool, piste and planned start, and orders them by
planned start.

#### Scenario: The next wave is called
- **WHEN** wave 1 of Longsword is running
- **THEN** the call list names wave 2's fencers by pool, piste and planned time

### Requirement: Pools report progress
A pool starts when its first bout is recorded and ends when its last bout is recorded.
These moments SHALL be reported to the planner, as frozen activities for re-planning,
and to `today`, as slip.

#### Scenario: A late pool is slip
- **WHEN** Sabre pool 2 was planned to start at 10:00 and its first bout is recorded at 10:20
- **THEN** `today` states Sabre 20 minutes behind

