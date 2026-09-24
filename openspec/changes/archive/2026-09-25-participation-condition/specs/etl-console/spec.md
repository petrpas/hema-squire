## MODIFIED Requirements

### Requirement: Manual entry fields follow the tournament's structure
The manual entry dialog SHALL offer the tournament's own structure rather than a generic fencer form. Disciplines SHALL be offered as the tournament's own offered individual disciplines, by their names; items to borrow SHALL be offered as the items the tournament lends, by their names; the afterparty SHALL be offered only where the tournament holds one. A choice the tournament does not offer SHALL NOT be presented.

Team disciplines SHALL NOT be offered in the dialog. A team is entered through the tournament's team handling, not by naming a team discipline on a fencer's row.

Where at least two individual disciplines are chosen, the dialog SHALL offer the participation condition as the registration form does (`registration`, **Participation condition**), as one tick, unticked by default. It SHALL be offered on an automatic tournament only: a manual tournament queues nobody, so the condition would have nothing to govern.

The dialog SHALL additionally take the fencer's name, nationality, club, HEMA Ratings id, e-mail, a registration moment, and a note. The registration moment SHALL default to the present moment in the tournament's own time zone and SHALL be changeable, so that a form received last week can be entered with the moment it was received.

#### Scenario: Only the offered disciplines appear
- **WHEN** a tournament offers three individual disciplines and one team discipline, and the organizer opens the dialog
- **THEN** the three individual disciplines are offered and the team discipline is not

#### Scenario: Rentals named as the tournament names them
- **WHEN** a tournament lends a mask and a longsword under those names
- **THEN** those are the items the dialog offers to borrow, and no others

#### Scenario: No afterparty, no question
- **WHEN** a tournament holds no afterparty
- **THEN** the dialog asks nothing about one

#### Scenario: Backdated entry
- **WHEN** the organizer changes the registration moment to a date three days ago and submits
- **THEN** the row is listed among the rows registered that day, not among today's

#### Scenario: The condition offered at the door
- **WHEN** the organizer of an automatic tournament chooses two disciplines in the dialog
- **THEN** the participation condition tick is offered, unticked
