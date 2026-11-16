## ADDED Requirements

### Requirement: Data shows who the floor will work with
The `data` tab SHALL list the floor roster, live, per discipline:
- for an individual discipline, its entrants' names, clubs and nationalities, ratings
  and paid marks;
- for a team discipline, its teams with their members.

Each discipline SHALL state its entry count.

**Live until the snapshot.** The list SHALL be read from the floor roster on every open.
It changes as the office changes, until check-in freezes the discipline's snapshot
(`floor-checkin`). From then on, Data states for that discipline that its entrants were
taken at the snapshot, and when.

#### Scenario: A cancellation reaches the floor
- **WHEN** a registration is cancelled in the office console before check-in closes
- **THEN** the Data tab no longer lists that entrant

### Requirement: Entrants come from the office
The `data` tab SHALL NOT offer an import of its own. Entrants come from the office
(`floor-roster`). Where the tournament's list is kept by the organizer, the tab SHALL
link to the office console's Import phase and state that a table imported there reaches
the floor.

The floor roster port stays the only way entrants reach the floor. A later change may
fill it from a second source without changing any other floor code (owner decision
2026-11-16).

#### Scenario: An organizer-kept tournament is pointed to Import
- **WHEN** the organizer opens Data on a tournament whose list they keep
- **THEN** the tab links to `/organizer/:slug/console/import`
