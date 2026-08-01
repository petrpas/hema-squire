## MODIFIED Requirements

### Requirement: Tournament definition
A tournament SHALL be defined by internal name, display name, an optional subtitle, an optional logo, date, communication language, location (free text), an optional description, a qualification statement, a list of titular organizers, and a set of disciplines. The subtitle is free text that MAY be longer than the display name and is frequently empty; every presentation of the tournament SHALL render correctly whether or not the subtitle is set. The logo is an optional image supplied by the organizer, stored with the tournament and served for display; the system SHALL bound its size on upload (reject oversized uploads and re-encode to a bounded image) so it stays small. The description is optional free-form text of arbitrary length, authored in markdown and stored verbatim as its markdown source; it SHALL be presented as formatted content according to `organizer-prose`, which fixes the honored subset, the sanitizer allowlist, and the presentation rules. Titular organizers are free-text names of clubs or other entities shown publicly as the tournament's organizers, each with an optional link; they are independent of account-based console access. Each discipline SHALL have a code and human-readable name drawn from the HEMA taxonomy (weapon LS/SA/RA/RD/SB × gender Open/Women/Men × material Steel/Plastic), a capacity limit, a unit price, optional schedule fields (`when`, `where`) mainly for multi-day events, and an optional ruleset consisting of a short style name and an optional external link. In the console, a discipline SHALL be identified by its name in emphasized text, and each of its optional fields (`when`, `where`, ruleset name, ruleset link) SHALL carry a help hint stating what belongs in it. Subtitle, logo, description, qualification, disciplines (including their schedule and ruleset fields) and titular organizers SHALL be editable in the console Setup phase, disciplines and organizers as row tables with add and remove. The Setup section carrying the tournament's own identity fields SHALL NOT be given a section heading of its own.

#### Scenario: Organizer configures disciplines
- **WHEN** the organizer adds disciplines LS and SAW in the Setup table, each with a capacity and a unit price
- **THEN** registration offers exactly those disciplines under those capacity constraints at those prices

#### Scenario: Discipline schedule and ruleset captured
- **WHEN** the organizer sets a discipline's when to "Saturday", where to "Main Hall — Kurtzstrasse 21", and ruleset to "Right of Way" with an external link
- **THEN** the tournament information presents that discipline with its schedule and a ruleset link, and omits those lines for disciplines that leave them empty

#### Scenario: Optional discipline fields explain themselves
- **WHEN** the organizer reaches the help marker next to a discipline's `when`, `where`, ruleset name, or ruleset link field
- **THEN** a hint appears describing what belongs in that field (for example, for `when`: that it takes a rough time such as "Saturday morning")

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

### Requirement: Registration instructions
A tournament SHALL have an optional multiline free-text `registration instructions` field, editable in the Setup phase and distinct from the public description. It is authored in markdown and stored verbatim as its markdown source, and SHALL be presented as formatted content according to `organizer-prose`. It SHALL be presented only on the registration form. It SHALL NOT be part of mandatory setup, and its absence SHALL NOT change any other presentation.

#### Scenario: Instructions shown on the form only
- **WHEN** the organizer fills registration instructions and a fencer opens the tournament
- **THEN** the instructions appear on the registration form and do not appear on the information screen

#### Scenario: Instructions absent
- **WHEN** a tournament has no registration instructions
- **THEN** the registration form renders correctly with no instructions block

#### Scenario: Markdown rendered, line breaks preserved
- **WHEN** the instructions contain several paragraphs, a bullet list and a link
- **THEN** they render with their paragraph and line breaks intact, the list as list items and the link as an `--ink` underlined link, with no markup characters visible
