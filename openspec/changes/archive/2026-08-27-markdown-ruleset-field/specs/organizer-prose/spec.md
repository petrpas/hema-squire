## MODIFIED Requirements

### Requirement: Markdown-authored prose fields
The organizer-authored long-form text fields — the tournament `description` and the tournament `registration instructions` — SHALL be authored in markdown and presented as formatted content. The tournament `location` and a discipline's `ruleset` SHALL be authored in the inline markdown subset defined below. The stored value SHALL always be the organizer's markdown source, unmodified: the system SHALL NOT store rendered output, and SHALL NOT rewrite, normalize, or escape the source on save. Rendering SHALL happen at presentation time only. No other field SHALL be treated as markdown; subtitle, qualification criteria, organizer names, a discipline's `when` and `where`, and extra-item names, `when`, `where` and `remark` remain plain text.

#### Scenario: Source stored verbatim
- **WHEN** the organizer saves a description containing `## Program`, `- longsword`, and `**bring a mask**`
- **THEN** the stored value contains exactly those characters, and re-opening the Setup field shows the same markdown source the organizer typed

#### Scenario: Location source stored verbatim
- **WHEN** the organizer saves the location `[ZŠ Bílá](https://osm.org/go/0J0ajlLg8?m=)`
- **THEN** the stored value is exactly that text, re-opening the Setup field shows it unchanged, and no migration or format conversion is applied to locations stored earlier

#### Scenario: Presented as formatted content
- **WHEN** a fencer opens the information screen of that tournament
- **THEN** `## Program` is presented as a heading, `- longsword` as a list item, and `bring a mask` in emphasized weight, with no markup characters visible

#### Scenario: Ruleset source stored verbatim
- **WHEN** the organizer saves a discipline's ruleset as `[Barbasetti Right of Way](https://example.com/cz.pdf) (CZ) · [EN](https://example.com/en.pdf)`
- **THEN** the stored value is exactly that text, and re-opening the Setup field shows it unchanged

#### Scenario: Non-prose fields unaffected
- **WHEN** an organizer types `**Praha**` into a tournament subtitle, a discipline's `where`, or an extra item's remark
- **THEN** the text is presented literally, asterisks included, because those fields are not markdown

### Requirement: Markdown authoring affordance in Setup
In the console Setup phase, each markdown prose field SHALL be edited in a monospace (`--font-data`) multiline control, and SHALL carry a localized one-line reminder of the honored syntax beneath it. An inline markdown field SHALL keep its single-line control and SHALL carry its own localized one-line reminder naming only the inline subset, so an organizer is never invited to write a heading or a list where one cannot render. Every inline field SHALL show the same reminder, worded once and shared, and that wording SHALL state the link form with its scheme — `[link](https://...)` — since reaching an external document is the reason these fields accept markdown at all. Every such control SHALL accept and preserve exactly the characters typed; it SHALL NOT auto-format, auto-complete, or transform the source. No live preview or syntax-highlighting overlay is required in the editing control itself — the organizer sees rendered output in the Setup preview pane.

#### Scenario: Monospace editing with a hint
- **WHEN** the organizer opens the description or registration-instructions field in Setup
- **THEN** the text is set in `--font-data` and a one-line syntax reminder appears beneath the field in the console's language

#### Scenario: Location hint names only the inline subset
- **WHEN** the organizer opens the location field in Setup
- **THEN** it is still a single-line control, and the reminder beneath it names links and emphasis and does not name headings, lists, quotes or rules

#### Scenario: The ruleset field carries the same hint
- **WHEN** the organizer opens a discipline's ruleset field in Setup
- **THEN** it is a single-line control carrying the same reminder the location field carries

#### Scenario: The hint spells out the link form
- **WHEN** the organizer reads the reminder beneath any inline markdown field
- **THEN** it shows the link form written with its scheme, `[link](https://...)`, and it is the same wording under every such field

#### Scenario: Rendered result visible while configuring
- **WHEN** the organizer saves a markdown description in Setup
- **THEN** the Setup preview shows it rendered exactly as a fencer will see it, because the preview renders through the same components as the fencer-facing screens
