## MODIFIED Requirements

### Requirement: Tournament definition
A tournament SHALL be defined by internal name, display name, an optional subtitle, an optional logo, date, communication language, location (free text), an optional description, a qualification statement, a list of titular organizers, and a set of disciplines. The subtitle is free text that MAY be longer than the display name and is frequently empty; every presentation of the tournament SHALL render correctly whether or not the subtitle is set. The logo is an optional image supplied by the organizer, stored with the tournament and served for display; the system SHALL bound its size on upload (reject oversized uploads and re-encode to a bounded image) so it stays small. The description is optional free-form text of arbitrary length, authored in markdown and stored verbatim as its markdown source; it SHALL be presented as formatted content according to `organizer-prose`, which fixes the honored subset, the sanitizer allowlist, and the presentation rules. Titular organizers are free-text names of clubs or other entities shown publicly as the tournament's organizers, each with an optional link; they are independent of account-based console access. Each discipline SHALL have a code and human-readable name drawn from the HEMA taxonomy (weapon LS/SA/RA/RD/SB × gender Open/Women/Men × material Steel/Plastic), a capacity limit, a unit price, optional schedule fields (`when`, `where`) mainly for multi-day events, and an optional ruleset consisting of a short style name and an optional external link. In the console, a discipline SHALL be identified by its name in emphasized text, and each of its optional fields (`when`, `where`, ruleset name, ruleset link) SHALL carry a help hint stating what belongs in it.

Subtitle, logo, description, qualification, disciplines (including their schedule and ruleset fields) and titular organizers SHALL be editable in the console Setup phase, disciplines and organizers as row tables with add and remove. The communication language SHALL NOT be editable in Setup: it is assigned when the tournament is created and thereafter governs fencer emails without being offered as a settings field. The Setup section carrying the tournament's own identity fields SHALL NOT be given a section heading of its own, and SHALL present those fields in this order: display name, subtitle, logo, date, location, description, qualification statement, registration opens, registration closes, registration instructions.

#### Scenario: Organizer configures disciplines
- **WHEN** the organizer adds disciplines LS and SAW in the Setup table, each with a capacity and a unit price
- **THEN** registration offers exactly those disciplines under those capacity constraints at those prices

#### Scenario: Discipline schedule and ruleset captured
- **WHEN** the organizer sets a discipline's when to "Saturday", where to "Main Hall — Kurtzstrasse 21", and ruleset to "Right of Way" with an external link
- **THEN** the tournament information presents that discipline with its schedule and a ruleset link, and omits those lines for disciplines that leave them empty

#### Scenario: Optional discipline fields explain themselves
- **WHEN** the organizer reaches the help marker next to a discipline's `when`, `where`, ruleset name, or ruleset link field
- **THEN** a hint appears describing what belongs in that field (for example, for `when`: that it takes a rough time such as "Saturday morning")

#### Scenario: Identity fields in the stated order
- **WHEN** the organizer opens the `TOURNAMENT` tab
- **THEN** the identity fields read top to bottom as display name, subtitle, logo, date, location, description, qualification statement, registration opens, registration closes, registration instructions

#### Scenario: Communication language not offered
- **WHEN** the organizer looks through every Setup tab
- **THEN** no field offers the tournament's communication language, and the language stored at creation is unchanged by any save

#### Scenario: Emails still follow the stored language
- **WHEN** a fencer registers for a tournament created with Czech as its communication language
- **THEN** the confirmation email is Czech, exactly as before the field left Setup

#### Scenario: Subtitle and logo optional
- **WHEN** a tournament is saved with a subtitle and a logo, and another is saved with neither
- **THEN** both render correctly wherever the tournament is presented, the first showing its subtitle and logo and the second showing neither

#### Scenario: Oversized logo rejected
- **WHEN** the organizer uploads a logo larger than the configured cap
- **THEN** the upload is rejected with a clear message and no logo is stored

#### Scenario: Titular organizers edited
- **WHEN** the organizer adds "Duelanti od sv. Rocha" as a titular organizer row
- **THEN** the name appears wherever the tournament presents its organizers, without granting any console access

#### Scenario: Organizer with a link
- **WHEN** a titular organizer row carries a link and another leaves it empty
- **THEN** the first is presented as a link on the organizer's name and the second as plain text, and both are stored with the tournament

#### Scenario: Description written and presented
- **WHEN** the organizer writes a multi-paragraph markdown description in Setup and saves
- **THEN** the markdown source is stored verbatim and presented as formatted content — paragraph breaks intact, headings, lists, emphasis and links rendered, and nothing outside the honored subset rendered as markup

#### Scenario: Description written without markdown
- **WHEN** the organizer writes a plain multi-paragraph description using no markdown markers
- **THEN** it is presented with its paragraph breaks and line breaks intact, exactly as before markdown authoring was introduced

### Requirement: Tournament qualification statement
Each tournament SHALL carry a qualification statement consisting of an openness flag and optional criteria text. The flag SHALL default to open, so a tournament that never sets it presents as open to everyone. When the organizer marks the tournament as requiring qualification, criteria text SHALL be required and SHALL be free text (for example "national championship placement, HR top 500"); the field SHALL carry a help hint offering such examples. Marking the tournament open again SHALL clear the criteria text. The statement SHALL be editable in the Setup phase between the description and the registration dates, and SHALL be presented wherever the tournament is described. The statement is informational: it SHALL NOT restrict, block, or flag any registration.

#### Scenario: Default is open
- **WHEN** a tournament is created and its qualification is never touched
- **THEN** it is stored as open to everyone and presented as such

#### Scenario: Qualification criteria recorded
- **WHEN** the organizer marks the tournament as requiring qualification and enters "mistrovství ČR, HR top 500"
- **THEN** that text is stored and presented as the tournament's qualification criteria

#### Scenario: Criteria required when qualification is required
- **WHEN** the organizer marks the tournament as requiring qualification and saves with empty criteria
- **THEN** the save is rejected with a field-level message and the tournament's stored qualification is unchanged

#### Scenario: Reopening clears criteria
- **WHEN** a tournament with qualification criteria is switched back to open to everyone and saved
- **THEN** the criteria text is cleared and the tournament presents as open to everyone

#### Scenario: Statement sits after the description
- **WHEN** the organizer opens the `TOURNAMENT` tab
- **THEN** the qualification statement appears below the description and above the registration-opens field

#### Scenario: Qualification does not gate registration
- **WHEN** a fencer registers for a tournament that requires qualification
- **THEN** the registration proceeds exactly as it would for an open tournament

### Requirement: Variable symbol series
Each tournament SHALL carry a VS year and a VS series, which together form the prefix of every variable symbol it issues. The VS year SHALL be taken from the tournament's date when the series is assigned, so that an event held in January belongs to that January's year even when it is created and sells out during the preceding year. The VS series SHALL be an integer from 1 to 99 and SHALL be unique among the tournaments sharing a VS year.

The series SHALL be assigned automatically when the tournament is created, as the lowest value not already taken for its year. It SHALL NOT be editable by the organizer at any point. The Setup phase SHALL state the assigned series and the resulting variable-symbol prefix so the organizer can see what payers will quote, presented as a fact about the tournament rather than as a field. A change to the tournament's date before its first registration MAY reassign the year and series; once the tournament has its first registration, both SHALL be fixed, a later change to the date SHALL NOT reassign either, and no already-issued variable symbol SHALL be renumbered. A tournament whose date later moves into another year therefore keeps its original prefix, which is correct because nothing routes on the prefix.

Assigning a series SHALL fail with a clear message naming the exhausted year when every value from 1 to 99 is already taken for that year, rather than assigning a duplicate or an out-of-range value.

#### Scenario: Series assigned on creation
- **WHEN** an organizer creates the first tournament dated in 2026
- **THEN** it is assigned VS year 2026 and series 1, and its Setup shows the variable-symbol prefix 2601

#### Scenario: Lowest free series taken
- **WHEN** a new tournament is created for a year in which series 1 and 3 are taken
- **THEN** it is assigned series 2

#### Scenario: Series taken from the tournament date, not the creation date
- **WHEN** an organizer creates a tournament in November 2026 for a date in January 2027
- **THEN** its VS year is 2027 and its series is the lowest free value among 2027 tournaments

#### Scenario: Series presented, not offered for editing
- **WHEN** the organizer opens the `PAYMENTS` tab on a tournament with no registrations
- **THEN** the series and its prefix are stated as read-only text, with no input, and the tab's save control counts no pending change for them

#### Scenario: Date change before registrations reassigns
- **WHEN** a tournament with no registrations has its date moved into another year
- **THEN** it is reassigned the lowest free series for the new year and the stated prefix follows

#### Scenario: Date change after registrations does not renumber
- **WHEN** a tournament with registrations has its date moved from December 2026 into January 2027
- **THEN** its VS year and series are unchanged, every issued variable symbol keeps its value, and newly issued symbols continue on the same prefix

#### Scenario: Year exhausted
- **WHEN** a tournament is created for a year that already holds 99 tournaments
- **THEN** creation is refused with a message naming the exhausted year

### Requirement: In-app tournament creation
An account holding the global Organizer role or higher SHALL be able to create a tournament from the tournament picker via a minimal dialog asking display name and date. The slug SHALL be auto-derived from the name and be editable before submission. Derivation SHALL append the event's year only when the slugified name does not already carry one: a four-digit group between 1900 and 2099 standing as its own token in the slug counts as a year already present, and in that case the slug is the slugified name alone. The creator SHALL become the tournament's Tournament Owner and land in the console's Setup phase. Accounts below the Organizer role SHALL NOT be able to create tournaments.

#### Scenario: Create from picker
- **WHEN** an account with the Organizer role submits the "New tournament" dialog with a name and date
- **THEN** the tournament is created with the derived slug, the account becomes its Tournament Owner, and the console opens on the Setup phase

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
- **THEN** creation is rejected with a clear error and the user can edit the slug

#### Scenario: Fencer cannot create
- **WHEN** an account with only the Fencer role attempts to create a tournament
- **THEN** creation is rejected with an authorization error

## ADDED Requirements

### Requirement: Price columns labelled uniformly
Every price column the organizer edits in Setup — on the disciplines table, the
extra-items table, and the fixed-amount rows of the discount list — SHALL be labelled
"unit price", naming its currency where the tournament prices in two. No such column
SHALL be labelled "fee" or "price". The label SHALL be localized like all other
user-facing text.

#### Scenario: Disciplines and extras agree
- **WHEN** the organizer moves between the `DISCIPLINES` and `EXTRA` tabs on a CZK + EUR tournament
- **THEN** both price columns are headed "unit price" with their currency, and neither is headed "fee" or "price"

#### Scenario: Single-currency tournament
- **WHEN** the tournament prices in one currency
- **THEN** each price column is headed "unit price" with that currency and no EUR column is shown

### Requirement: Logo control is a tertiary text action
The logo upload and removal controls on `TOURNAMENT` SHALL be presented as tertiary
underlined text actions, in the same treatment as "add organizer", rather than as
buttons. This keeps them visibly distinct from the tab's save control, which is the
only element on the tab styled as a primary action.

#### Scenario: Upload offered as a text action
- **WHEN** the organizer looks at the logo control
- **THEN** the upload is an underlined text action matching "add organizer", not a button, and choosing a file uploads it as before

#### Scenario: Removal matches the upload
- **WHEN** the tournament has a logo
- **THEN** its removal control is presented in the same tertiary treatment as the upload
