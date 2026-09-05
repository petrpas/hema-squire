## ADDED Requirements

### Requirement: The Fencers phase carries the settled mark where Squire collects nothing
WHERE Squire does not handle a tournament's payments, the Fencers phase SHALL carry a column stating whether each registration has been marked settled, and that column SHALL be the control that marks and unmarks it.

It SHALL be on Fencers rather than on Payments, because the Payments phase is not offered at all on such a tournament, and Fencers is the phase every tournament has and the one that lists everybody. Where Squire does handle the payments the column SHALL NOT be offered on Fencers, the state being the Payments phase's to show there.

This SHALL be the first column whose presence follows a tournament's settings rather than the phase alone, and it SHALL be the only one until another earns it.

The column SHALL state what the mark means where it could mislead: that it records the organizer's word that the money was received, and that Squire has received nothing itself.

**The mark SHALL be a write to the registration, not a rule.** Every other manual edit in the console persists as a rule replayed over the projection, which changes what the table and the export show and reaches nothing else. This mark changes what the registration *is* — the public participant list and the registration's own state depend on it — so it SHALL be written through. The departure SHALL be deliberate and confined to this one action.

#### Scenario: The column is offered where the organizer collects
- **WHEN** the organizer opens the Fencers phase on a tournament that handles its own payments
- **THEN** each row states whether it is marked settled, and the mark can be set and unset there

#### Scenario: Absent where Squire collects
- **WHEN** the organizer opens the Fencers phase on a tournament whose payments Squire handles
- **THEN** no settled column is offered, and the state is shown on the Payments phase as before

#### Scenario: The mark reaches the registration
- **WHEN** a registration is marked settled and the tournament's public participant list is read
- **THEN** that entrant is shown as confirmed, which no rule over the projection could have achieved
