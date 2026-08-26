## ADDED Requirements

### Requirement: The timeline carries the opening time and the tournament timezone
The opening time of day SHALL sit on `TIMELINE` beside the registration-opens date it belongs to, in every mode, as one field pair rather than as two independent rows: it is read as a qualifier of that date, not as a date of its own, and SHALL therefore never take its own place in the chronological sequence the timeline presents.

The tournament's timezone SHALL also sit on `TIMELINE`, in every mode, presented as governing the whole section rather than any single date — it is the zone every date and time on the timeline is read in, as fixed by `tournament-admin`. It SHALL sit apart from the chronological sequence so that it does not read as another deadline.

Both SHALL save with the rest of the timeline section, through the same single save the section already performs, so that a date and its time can never reach the system as two separate saves with an inconsistent state between them.

#### Scenario: Opening time beside its date
- **WHEN** the organizer opens `TIMELINE`
- **THEN** the opening time is offered beside the registration-opens date, and the chronological sequence of dates is unchanged, with the tournament's own date still closing it read-only

#### Scenario: Timezone offered apart from the sequence
- **WHEN** the organizer opens `TIMELINE`
- **THEN** the tournament's timezone is offered as a property of the section as a whole, not as an entry in the sequence of dates

#### Scenario: Offered in easy mode
- **WHEN** the organizer of a tournament in easy mode opens `TIMELINE`
- **THEN** both the opening time and the timezone are offered, exactly as the registration window itself is

#### Scenario: Saved with the section
- **WHEN** the organizer changes the registration-opens date and its opening time and saves the section
- **THEN** both reach the system in the same save, and a rejection of either leaves neither stored
