## MODIFIED Requirements

### Requirement: Registration availability
The system SHALL accept a registration only when the tournament has been published and the current moment is within the registration window: at or after the tournament's opening moment when an opens date is set, and on or before the registration-closes date when set (otherwise up to the tournament date). When registration is unavailable, the rejection SHALL carry a distinct reason — not yet published, not yet open, or closed — so clients can present it (with the opening moment where applicable). The gate SHALL NOT re-check mandatory setup completeness: publication already guarantees it, and a published tournament cannot be edited into incompleteness.

The two edges of the window SHALL be evaluated differently, because they mean different things. The opening edge is an **instant**: the tournament's opens date, its opening time when set (the start of the day otherwise), read in the tournament's timezone as fixed by `tournament-admin`. The closing edge remains a **whole day**: registration is accepted through the end of the closing date in the tournament's timezone. No edge SHALL be evaluated against a day boundary in any other zone, so a tournament announced as opening at a given hour opens at that hour for every caller, wherever the system or the caller happens to run.

Amendment availability SHALL follow the same evaluation: it is closed by every reason registration is, plus its own amendments-close boundary when set, which is a whole day in the tournament's timezone.

The gate SHALL remain the sole authority on whether a registration may be created. A client MAY present the window and MAY reveal its registration form when the opening moment passes, but a submission that arrives before the opening moment SHALL still be rejected with the not-yet-open reason, and that rejection SHALL carry the opening moment so the client can return to presenting the wait rather than a generic failure.

#### Scenario: Not published
- **WHEN** a fencer attempts to register for a tournament that has not been published
- **THEN** the registration is rejected with the not-yet-published reason, whether or not its mandatory setup is complete

#### Scenario: After close
- **WHEN** a fencer attempts to register after the registration-closes date
- **THEN** the registration is rejected with the closed reason

#### Scenario: Before the opening hour
- **WHEN** a fencer submits a registration one minute before the tournament's opening moment
- **THEN** the registration is rejected with the not-yet-open reason, and the rejection states the opening moment

#### Scenario: At the opening hour
- **WHEN** a fencer submits a registration at the tournament's opening moment
- **THEN** the registration is accepted

#### Scenario: Opening is not a UTC day boundary
- **WHEN** a tournament in a zone ahead of UTC opens registration on a given date with no opening time, and a fencer submits during the hour after midnight UTC but before midnight locally
- **THEN** the registration is rejected with the not-yet-open reason

#### Scenario: Closing runs to the end of the local day
- **WHEN** a fencer submits a registration late in the evening, local to the tournament, on the registration-closes date
- **THEN** the registration is accepted

### Requirement: Fencer-facing tournament list
The system SHALL expose a tournament list for fencers containing only published, non-cancelled tournaments, each with its public information — including its subtitle and a reference to its logo when set, and its local currency — its per-discipline registered numbers (seats taken per capacity, counting confirmed registrations and unexpired reservations), the registration availability status (open, not yet open with the opening moment, or closed), and whether the requesting account has an active registration. The subtitle and logo reference SHALL be omitted (null/absent) when not set, and their absence SHALL NOT change the rest of the payload.

A not-yet-open entry SHALL carry the opening moment as a **resolved absolute instant bearing its offset**, not as a bare date, so that no consumer has to know the tournament's timezone rules to display it or to compare against it. The tournament's timezone identifier SHALL be carried alongside it, so a consumer can name the zone the hour is stated in. The same resolved instant and identifier SHALL appear on the fencer-facing tournament detail payload.

Every response carrying an opening moment SHALL also carry the **server's own current instant**, so that a consumer can measure its own clock against the system's rather than counting down against a clock that may be wrong.

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

#### Scenario: Opening moment carried as an instant
- **WHEN** a fencer lists tournaments and one of them opens registration at 18:00 local time on a future date
- **THEN** that entry's status is not-yet-open and its opening moment is an absolute instant carrying its offset, alongside the tournament's timezone identifier

#### Scenario: Response states the server's clock
- **WHEN** any fencer-facing tournament list or detail is fetched
- **THEN** the response states the server's current instant
