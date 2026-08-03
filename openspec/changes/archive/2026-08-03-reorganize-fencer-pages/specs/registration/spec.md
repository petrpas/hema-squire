## MODIFIED Requirements

### Requirement: Fencer-facing tournament list
The system SHALL expose a tournament list for fencers containing only published, non-cancelled tournaments, each with its public information — including its subtitle and a reference to its logo when set, and its local currency — its per-discipline registered numbers (seats taken per capacity, counting confirmed registrations and unexpired reservations), the registration availability status (open, not yet open with the opening date, or closed), and whether the requesting account has an active registration. The subtitle and logo reference SHALL be omitted (null/absent) when not set, and their absence SHALL NOT change the rest of the payload.

The list SHALL be served in three scopes, carrying the same entry shape so one presentation serves all three:

- **upcoming** — tournaments dated today or later, ordered by date ascending;
- **held** — tournaments dated before today, ordered by date descending, listed for every requesting account whether or not it was involved with them;
- **own** — tournaments in either direction of today where the requesting account holds or held a registration in any state, including cancelled, or is the tournament's owner or a member of its console team, ordered by date descending.

Every entry SHALL carry the requesting account's own relationship to that tournament: its registration state when it holds or held one, and an organizer mark when the account is its owner or console team member. An entry SHALL be able to carry both facts, and a consumer SHALL be able to tell a registration from an organizer relationship without a second request.

A per-discipline count SHALL be stated in the unit its discipline is entered in: fencers for an individual discipline, teams for a team discipline. No scope SHALL apply the fencer-counting rule to a team discipline.

#### Scenario: Counts and own status included
- **WHEN** a logged-in fencer requests the fencer-facing tournament list
- **THEN** each tournament carries taken/capacity numbers per discipline, its registration status, and a flag for the fencer's own active registration

#### Scenario: Held scope is public
- **WHEN** an account with no registration and no organizer role requests the held scope
- **THEN** every published, non-cancelled tournament dated before today is returned, each with no registration state and no organizer mark for that account

#### Scenario: Own scope spans both directions
- **WHEN** an account holding a reservation for a tournament next month and a paid registration for one last year requests the own scope
- **THEN** both are returned, newest first, each carrying its registration state

#### Scenario: Organizer relationship reported
- **WHEN** an account that organizes a tournament but never registered for it requests the own scope
- **THEN** that tournament is returned carrying the organizer mark and no registration state

#### Scenario: Own scope excludes the unrelated
- **WHEN** a published tournament exists that the account neither registered for nor organizes
- **THEN** it is absent from the own scope while remaining present in the scope its date puts it in

#### Scenario: Team discipline counted in teams
- **WHEN** any scope lists a tournament offering a team discipline
- **THEN** that discipline's count states entered teams against its capacity in teams, and the request succeeds

#### Scenario: Subtitle and logo carried when set
- **WHEN** a listed tournament has a subtitle and a logo
- **THEN** its list entry carries the subtitle and a reference to its logo, and entries without them omit those fields

#### Scenario: Currency carried
- **WHEN** a fencer requests the list
- **THEN** each entry carries the tournament's local currency so amounts render without a hardcoded unit

#### Scenario: Unpublished excluded
- **WHEN** a tournament has not been published, or it is cancelled
- **THEN** it is absent from the fencer-facing list, in every scope

#### Scenario: Setup-complete draft still excluded
- **WHEN** a tournament's mandatory setup is complete but nobody has published it
- **THEN** it is absent from the fencer-facing list
