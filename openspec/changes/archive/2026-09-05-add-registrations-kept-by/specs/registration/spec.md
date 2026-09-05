## MODIFIED Requirements

### Requirement: Registration availability
The system SHALL accept a registration only when the tournament's registrations are kept by Squire, the tournament has been published, and the current moment is within the registration window: at or after the tournament's opening moment when an opens date is set, and on or before the registration-closes date when set (otherwise up to the tournament date). When registration is unavailable, the rejection SHALL carry a distinct reason — kept by the organizer, not yet published, not yet open, or closed — so clients can present it (with the opening moment where applicable). The gate SHALL NOT re-check mandatory setup completeness: publication already guarantees it, and a published tournament cannot be edited into incompleteness.

A tournament whose registrations the organizer keeps SHALL be refused before every other reason is considered, and with a reason of its own, as fixed by `registration-ownership`. It SHALL NOT be reported as closed: the closed reason means a window has passed, and telling a fencer they were too late for a window that never existed on this tournament is a falsehood the client would then present.

The two edges of the window SHALL be evaluated differently, because they mean different things. The opening edge is an **instant**: the tournament's opens date, its opening time when set (the start of the day otherwise), read in the tournament's timezone as fixed by `tournament-admin`. The closing edge remains a **whole day**: registration is accepted through the end of the closing date in the tournament's timezone. No edge SHALL be evaluated against a day boundary in any other zone, so a tournament announced as opening at a given hour opens at that hour for every caller, wherever the system or the caller happens to run.

Amendment availability SHALL follow the same evaluation: it is closed by every reason registration is, plus its own amendments-close boundary when set, which is a whole day in the tournament's timezone.

The gate SHALL remain the sole authority on whether a registration may be created. A client MAY present the window and MAY reveal its registration form when the opening moment passes, but a submission that arrives before the opening moment SHALL still be rejected with the not-yet-open reason, and that rejection SHALL carry the opening moment so the client can return to presenting the wait rather than a generic failure.

#### Scenario: Kept by the organizer
- **WHEN** a fencer attempts to register for a published, open tournament whose registrations the organizer keeps
- **THEN** the registration is rejected with the kept-by-the-organizer reason

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
