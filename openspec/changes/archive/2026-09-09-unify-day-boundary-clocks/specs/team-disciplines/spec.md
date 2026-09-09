## MODIFIED Requirements

### Requirement: Team composition deadline checks rather than enforces
A tournament SHALL carry an optional team composition deadline: the date by which rosters
are expected to reach their disciplines' minimum sizes. It SHALL be configurable only as
a date, SHALL be meaningful only when the tournament offers at least one team discipline,
and SHALL be presented to the entering fencer alongside their teams.

The deadline SHALL NOT enforce anything. Passing it SHALL NOT lock a roster, SHALL NOT
cancel or waitlist a team, SHALL NOT free capacity, SHALL NOT change a total or a refund
state, and SHALL NOT block any action. Rosters remain editable after it under the same
rules as before it.

Its sole effect SHALL be to mark, from the day after it passes, every team whose roster is
below its discipline's minimum, for the organizer to act on through the controls that
already exist.

It SHALL be read as a whole day in the tournament's timezone, as `day-boundaries` fixes
for every date the organizer entered — the same rule the registration close beside it
already follows. Whether a team is marked below minimum SHALL NOT depend on the hour the
organizer opens the view, nor on the deployment's timezone.

#### Scenario: Deadline passes with a short roster
- **WHEN** the composition deadline passes and a team holds two members against a minimum of three
- **THEN** the team is marked as below minimum for the organizer, remains entered, keeps its capacity slot, and its registration's total and payment state are unchanged

#### Scenario: Roster completed after the deadline
- **WHEN** the entering fencer adds the missing member after the deadline has passed
- **THEN** the edit is accepted and the team is no longer marked as below minimum

#### Scenario: Member swapped the night before
- **WHEN** the entering fencer replaces a member the day before the tournament
- **THEN** the edit is accepted

#### Scenario: No deadline configured
- **WHEN** a tournament offering a team discipline has no composition deadline set
- **THEN** no team is ever marked as below minimum and nothing is reminded

#### Scenario: The deadline's last hours are local
- **WHEN** a tournament held in a zone ahead of UTC has a composition deadline of the 20th, and the organizer opens the teams view after midnight UTC on the 21st but before midnight where the tournament is held
- **THEN** no team is marked as below minimum, because the deadline has not passed
