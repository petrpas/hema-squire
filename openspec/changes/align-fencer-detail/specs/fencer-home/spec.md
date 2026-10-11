## ADDED Requirements

### Requirement: Tournament detail wears the list's geometry
The tournament detail SHALL read as the same object as its card on the list. Its tabs SHALL be the segmented pill control the list's filter tabs are, the active tab inverted. Each block of its content — information, disciplines, discounts, other actions, the registration form and the registration panel — SHALL be drawn on `--paper-raised` with a 1px `--hairline` border at `--radius-card`. Its buttons SHALL be pills (`design-system`, Button hierarchy). Form fields, tags and the entrant tables SHALL keep the 2px geometry the skin keeps for them. Every value SHALL come from a role token whose day value is the old one, so the console, which shares these components, is unchanged.

#### Scenario: Tabs on the detail
- **WHEN** a tournament's detail is opened
- **THEN** its Tournament, Entrants and Register tabs stand as pills inside one pill, the shown one inverted, as the list's tabs do

#### Scenario: Blocks round, tables do not
- **WHEN** the detail's Entrants tab is shown
- **THEN** the surrounding blocks have the card's rounded corners and the roster table's cells and the form fields keep square corners

#### Scenario: The console is untouched
- **WHEN** a console phase that shares these blocks and buttons is rendered
- **THEN** its corners are 2px as before

### Requirement: Tournament detail opens on its cover
The detail's information block SHALL open with the same cover its card wears: a band in the tint the card would choose (`A card's cover tint follows its logo`), the plate at its centre — the logo on `--plate` cropped to fill it, or the short code or monogram — ringed in `--stamp` while registration is open and in `--hairline-strong` otherwise, and at its top left the status block stating registration's state as the card states it. The status is the one the page itself computes against the server's clock, so the block changes in place when registration opens. The title, subtitle and facts follow beneath the cover.

#### Scenario: An open tournament with a logo
- **WHEN** the detail of a tournament whose registration is open and whose logo is green is opened
- **THEN** it opens on a seal-green band with the logo filling a plate ringed in `--stamp`, and the status block reads `registrace` / `otevřena` / `do {date}`

#### Scenario: Registration opens while the page is open
- **WHEN** the opening moment passes with the detail open
- **THEN** the status block reads open and the plate's ring turns `--stamp`, without a reload

### Requirement: Detail disciplines carry capacity meters
Each individual or team discipline listed on the detail SHALL carry, beneath its row, the static capacity meter the card carries (`design-system`, A capacity meter is a static figure), drawn from the same entered and capacity figures the row's count states. The row's count remains the text the meter draws, and remains a link to the roster where it was one. A full discipline's meter fills in `--stamp`.

#### Scenario: A discipline part full
- **WHEN** the detail lists a discipline with 3 of 4 places entered
- **THEN** its row states the count as before and beneath it a hidden-from-assistive-technology track is three quarters filled
