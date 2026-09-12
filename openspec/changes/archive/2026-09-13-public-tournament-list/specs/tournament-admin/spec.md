## MODIFIED Requirements

### Requirement: In-app tournament creation
An account holding the global Organizer role or higher SHALL be able to create a tournament from **the account menu**, from any screen, via a minimal dialog asking display name and date. The same dialog SHALL remain reachable from the tournament picker, which is where an organizer already stands when working through their tournaments. Wherever it is opened from, it SHALL be one dialog with one behaviour. The slug SHALL be auto-derived from the name and be editable before submission. Derivation SHALL append the event's year only when the slugified name does not already carry one: a four-digit group between 1900 and 2099 standing as its own token in the slug counts as a year already present, and in that case the slug is the slugified name alone. The creator SHALL become the tournament's Tournament Owner and land in the console's Setup phase. Accounts below the Organizer role SHALL NOT be able to create tournaments, and the menu SHALL NOT offer the entry to them at all.

Creation SHALL take two panels in one window, not two windows: the fields above, then the tournament's settings as fixed by `setup-navigation`. **No tournament SHALL exist until the second panel is confirmed** — the request that creates it carries its settings, so there is no moment at which one exists without them and none at which one exists because of a step the organizer then backed out of. Cancelling the second panel SHALL return to the first with every field intact, having created nothing.

A tournament SHALL be created in automatic mode with none of its features enabled, so that the settings panel only ever turns things on.

#### Scenario: Create from the account menu
- **WHEN** an account with the Organizer role opens the account menu from the tournament list and takes its Create tournament entry, giving a name and a date
- **THEN** the tournament is created with the derived slug, the account becomes its Tournament Owner, and the console opens on the Setup phase

#### Scenario: Create from picker
- **WHEN** an account with the Organizer role submits the "New tournament" dialog with a name and date
- **THEN** the settings panel opens; confirming it creates the tournament with the derived slug, makes the account its Tournament Owner, and opens the console on the Setup phase

#### Scenario: Year appended when the name carries none
- **WHEN** the organizer types "Prague Open" with a date in 2026
- **THEN** the derived slug is `prague-open-2026`

#### Scenario: Year not appended twice
- **WHEN** the organizer types "My Tournament 2027" with a date in 2026
- **THEN** the derived slug is `my-tournament-2027`, with no second year appended

#### Scenario: Digits that are not a year
- **WHEN** the organizer types "Turnaj 3 zbraní" with a date in 2026
- **THEN** the derived slug is `turnaj-3-zbrani-2026`, because `3` is not a four-digit year

#### Scenario: Slug collision
- **WHEN** the derived slug is already taken
- **THEN** creation is rejected with a clear error, no tournament exists, and the first panel is shown again with the input intact so the slug can be edited

#### Scenario: Fencer cannot create
- **WHEN** an account with only the Fencer role attempts to create a tournament
- **THEN** creation is rejected with an authorization error

#### Scenario: A fencer is not offered the entry
- **WHEN** an account with only the Fencer role opens the account menu
- **THEN** no tournament-creation entry is shown

#### Scenario: Created tournament starts with no features
- **WHEN** an organizer confirms the settings panel without changing anything
- **THEN** the tournament is created in automatic mode with every feature off, and the console opens on Setup

#### Scenario: Cancelling the settings panel creates nothing
- **WHEN** an organizer reaches the settings panel and cancels
- **THEN** no tournament has been created, and the first panel holds the name, date and slug that were typed
