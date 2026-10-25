## MODIFIED Requirements

### Requirement: Composition reminder to the entering fencer
When a tournament has a composition deadline, the system SHALL remind the entering fencer,
once, ahead of that deadline, of every team of theirs whose roster is still below its
discipline's minimum. The reminder SHALL name the teams, state how many members each
still needs, state the deadline, and link to the roster editor. That link SHALL be the
tournament link every registration message carries (`outgoing-mail`), which opens the
tournament page where the entering fencer's roster editor lives, and for a guest
registration additionally its manage link.

The reminder SHALL be sent at most once per team and SHALL record when it was sent, so
that a repeated run does not resend it. No reminder SHALL be sent for a team already at
or above its minimum, for a cancelled or expired registration, or for a waitlisted team.

No reminder SHALL be sent for a team whose registration Squire does not write to: one
entered by hand at the console and one issued from an imported list, on the same terms as
the confirmation (`registration`). Such a team SHALL NOT be stamped as reminded, so the
stamp continues to mean that a message was sent.

#### Scenario: Reminder for a short roster
- **WHEN** the reminder runs ahead of the deadline for a team holding one member against a minimum of three
- **THEN** the entering fencer receives one localized reminder naming the team, the shortfall, and the deadline, carrying the link to the tournament page

#### Scenario: Reminder not repeated
- **WHEN** the reminder job runs again while the roster is still short
- **THEN** no second reminder is sent for that team

#### Scenario: Complete roster not reminded
- **WHEN** the reminder runs for a team already at its minimum
- **THEN** no reminder is sent

#### Scenario: Hand entry not reminded
- **WHEN** the reminder runs ahead of the deadline for a short team on a registration the organizer entered by hand
- **THEN** no reminder is sent and the team is not stamped as reminded

#### Scenario: Imported registration not reminded
- **WHEN** the reminder runs ahead of the deadline for a short team on a registration issued from an imported list
- **THEN** no reminder is sent and the team is not stamped as reminded
