## MODIFIED Requirements

### Requirement: Organizer's read-only teams view
The console SHALL present, per team discipline, the teams entered into it: the team name,
the entering fencer, the roster in order with each member's name and — where bound — HEMA
Ratings identifier, club, and nationality, the member count against the discipline's
minimum and maximum, and the team's waitlist position where it is waitlisted. Teams
marked below minimum after the composition deadline SHALL be distinguished.

The view SHALL be offered only while the tournament's team disciplines feature is on, as
fixed by `tournament-modes`. An organizer who has turned the feature off SHALL see no
Teams phase; the teams, rosters and waitlist positions it would have shown SHALL be
retained untouched and SHALL be shown again when the feature is turned back on. The
entering fencer's own roster editor on the tournament detail page SHALL be unaffected by
the feature, which governs the organizer's console alone.

The view SHALL be read-only. It SHALL offer no action on a team or a roster: no
admission from the waitlist, no roster editing on the entrant's behalf, and no team
cancellation. The organizer acts through the controls that already exist elsewhere in
the console.

#### Scenario: Teams listed per discipline
- **WHEN** an organizer opens the teams view for a team discipline holding six teams
- **THEN** each team is listed with its name, entering fencer, ordered roster, and member count against the minimum and maximum

#### Scenario: Short teams distinguished after the deadline
- **WHEN** the composition deadline has passed and two of the listed teams are below minimum
- **THEN** those two are distinguished from the rest

#### Scenario: Unbound members shown plainly
- **WHEN** a listed roster contains members with no HEMA Ratings identifier
- **THEN** those members are shown by name with no identifier, club, or nationality, and are not marked as a problem

#### Scenario: No actions offered
- **WHEN** an organizer views a waitlisted team or a team below minimum
- **THEN** the view offers no control to admit, edit, or cancel it

#### Scenario: No teams view while the feature is off
- **WHEN** an organizer opens the console of a tournament whose team disciplines feature is off
- **THEN** no Teams phase is offered

#### Scenario: Teams reappear with the feature
- **WHEN** that organizer turns the team disciplines feature back on
- **THEN** the Teams phase is offered again, listing the same teams and rosters as before

#### Scenario: Entrants keep their roster editor
- **WHEN** a fencer who entered a team opens the tournament detail page while the team feature is off
- **THEN** the team is listed and its roster editor is offered as usual
