## MODIFIED Requirements

### Requirement: Registration window
A tournament SHALL have optional registration-opens and registration-closes dates, an optional opening time of day carried by the opens date, and a timezone. Registration SHALL be unavailable before the opening moment (when an opens date is set) and after the closes date (when set); with no closes date, registration stays available until the tournament date. With no opens date, registration is available as soon as the tournament is published (see `tournament-publication`).

The **opening time of day** SHALL name the wall-clock moment registration opens on the opening day. Unset, registration SHALL open at the start of that day, which is what a tournament carrying only an opens date has always meant. The time SHALL be offered only alongside the opens date and SHALL be a child of it: clearing the opens date SHALL clear the opening time in the same save, and an opening time submitted with no opens date SHALL be rejected with a validation error on the time rather than stored.

The **timezone** SHALL be the tournament's own local zone, named by its IANA identifier, and SHALL be the zone in which the opening time and every date on the timeline is read. It SHALL always be set: a new tournament SHALL be given a default, and a tournament created before this field existed SHALL carry that same default. A submitted zone that is not a known IANA identifier SHALL be rejected with a validation error. The organizer SHALL be offered a choice among zones with the default preselected, and the tournament's stored zone SHALL always be among the choices offered even where it falls outside that list, so a zone set through the API is never silently rewritten by opening Setup.

Because the timezone governs the whole timeline, a whole-day boundary SHALL be evaluated as a day in that zone: a tournament whose registration closes on a given date SHALL accept registrations until the end of that day locally, not until the end of that day in any other zone.

These dates, the seating deadline and the team composition deadline SHALL be presented together as the tournament's timeline, in chronological order, anchored by the tournament's own date shown read-only at its foot. The order SHALL be fixed by meaning rather than by which dates are filled, so an unset date keeps its place in the sequence.

**Each date SHALL carry a hint stating what it governs and what happens when it is left unset**, since each falls back to something different and the fallback is otherwise invisible: registration opens on publication, the seating deadline falls on the registration close, the registration close falls on the tournament date, and an unset composition deadline means no deadline and no reminders. The opening time's own fallback — that an unset time opens registration at the start of the opening day — SHALL be stated in the registration-opens hint rather than in a second hint of its own, since the time is offered as part of that field and not as a field beside it. The timezone SHALL carry a hint stating that every date and time on the timeline is read in it. The composition deadline's hint SHALL lead with what it does not do — it checks and reminds, and locks nothing.

A tournament SHALL additionally have an optional amendments-close date, after which fencers may no longer amend their registrations even while registration itself remains open. It SHALL NOT be offered to the organizer; unset, amendment is available on exactly the same window as registration, which is the intended default. The stored date SHALL be retained and honoured where one is already set, so the field can be offered again without a migration.

A tournament SHALL additionally have an optional team composition deadline, constrained only to be a date on or before the tournament date. It SHALL be independent of the registration and amendment windows in both directions: it MAY fall before or after either, and no combination of the three SHALL be rejected on account of their order. It governs nothing but the check and the reminder fixed by `team-disciplines`, and SHALL have no effect on a tournament that offers no team discipline.

#### Scenario: Before opening
- **WHEN** a fencer visits registration before the tournament's opening moment
- **THEN** registration is unavailable and the opening moment — its date, and its time when one is set — is shown

#### Scenario: No close date set
- **WHEN** no registration-closes date is set
- **THEN** registration remains available through the tournament date

#### Scenario: Dates read as a sequence
- **WHEN** the organizer opens the timeline with only the registration-opens date set
- **THEN** every date is shown in chronological order with its place kept, and the tournament date closes the sequence without a field to edit it

#### Scenario: Fallback stated on an unset date
- **WHEN** the organizer reads the seating deadline with no value set
- **THEN** its hint states that it falls on the registration close

#### Scenario: Composition deadline hint does not imply a lock
- **WHEN** the organizer reads the team composition deadline
- **THEN** its hint states that it reminds only, and that no roster is locked, no team is cancelled or queued, and no capacity is freed

#### Scenario: Amendments follow registration by default
- **WHEN** the organizer looks for an amendments-close date
- **THEN** none is offered, and amendment is available exactly while registration is available

#### Scenario: Stored amendments-close still honoured
- **WHEN** a tournament already carries an amendments-close date two weeks before registration closes
- **THEN** amendment still closes on that date, even though the field is no longer offered

#### Scenario: Composition deadline after amendments close
- **WHEN** a composition deadline falls four weeks after amendment has closed
- **THEN** the combination is accepted, and rosters stay editable after amendments have closed

#### Scenario: Opening at a chosen hour
- **WHEN** the organizer sets the registration-opens date to 1 September and the opening time to 18:00 on a tournament in the Europe/Prague zone
- **THEN** registration is unavailable at 17:59 Prague time on 1 September and available at 18:00 Prague time that day

#### Scenario: No opening time means the start of the day
- **WHEN** a tournament carries a registration-opens date and no opening time
- **THEN** registration opens at the start of that day in the tournament's timezone

#### Scenario: Clearing the date clears the time
- **WHEN** the organizer clears the registration-opens date on a tournament whose opening time is 18:00
- **THEN** both the date and the opening time are cleared, and registration opens as soon as the tournament is published

#### Scenario: Opening time without an opening date
- **WHEN** an opening time is submitted for a tournament with no registration-opens date
- **THEN** the save is rejected with a validation error on the opening time and neither field is stored

#### Scenario: Clock time that does not exist
- **WHEN** the organizer sets an opening time that the tournament's timezone skips on that date because the clocks go forward
- **THEN** the save is rejected with a validation error naming the clock change, rather than being resolved to a different hour

#### Scenario: Clock time that occurs twice
- **WHEN** the organizer sets an opening time that the tournament's timezone repeats on that date because the clocks go back
- **THEN** the save is accepted and registration opens at the first of the two occurrences

#### Scenario: Unknown timezone rejected
- **WHEN** a timezone that is not a known IANA identifier is submitted
- **THEN** the save is rejected with a validation error on the timezone

#### Scenario: Timezone offered with the stored value present
- **WHEN** the organizer opens the timeline of a tournament whose stored timezone is outside the offered list
- **THEN** the stored zone is shown as the current choice and remains selectable, and saving the section unchanged leaves it unchanged

#### Scenario: The close is a local day
- **WHEN** a tournament in the Europe/Prague zone closes registration on 30 September and a fencer registers at 23:30 Prague time that day
- **THEN** the registration is accepted
