## MODIFIED Requirements

### Requirement: Markdown-authored prose fields
The organizer-authored long-form text fields — the tournament `description` and the tournament `registration instructions` — SHALL be authored in markdown and presented as formatted content. The tournament `location` SHALL be authored in the inline markdown subset defined below. The stored value SHALL always be the organizer's markdown source, unmodified: the system SHALL NOT store rendered output, and SHALL NOT rewrite, normalize, or escape the source on save. Rendering SHALL happen at presentation time only. No other field SHALL be treated as markdown; subtitle, qualification criteria, organizer names, discipline fields, and extra-item names, `when`, `where` and `remark` remain plain text.

#### Scenario: Source stored verbatim
- **WHEN** the organizer saves a description containing `## Program`, `- longsword`, and `**bring a mask**`
- **THEN** the stored value contains exactly those characters, and re-opening the Setup field shows the same markdown source the organizer typed

#### Scenario: Location source stored verbatim
- **WHEN** the organizer saves the location `[ZŠ Bílá](https://osm.org/go/0J0ajlLg8?m=)`
- **THEN** the stored value is exactly that text, re-opening the Setup field shows it unchanged, and no migration or format conversion is applied to locations stored earlier

#### Scenario: Presented as formatted content
- **WHEN** a fencer opens the information screen of that tournament
- **THEN** `## Program` is presented as a heading, `- longsword` as a list item, and `bring a mask` in emphasized weight, with no markup characters visible

#### Scenario: Non-prose fields unaffected
- **WHEN** an organizer types `**Praha**` into a tournament subtitle or an extra item's remark
- **THEN** the text is presented literally, asterisks included, because those fields are not markdown

### Requirement: Markdown authoring affordance in Setup
In the console Setup phase, each markdown prose field SHALL be edited in a monospace (`--font-data`) multiline control, and SHALL carry a localized one-line reminder of the honored syntax beneath it. The inline markdown field SHALL keep its single-line control and SHALL carry its own localized one-line reminder naming only the inline subset, so an organizer is never invited to write a heading or a list where one cannot render. Every such control SHALL accept and preserve exactly the characters typed; it SHALL NOT auto-format, auto-complete, or transform the source. No live preview or syntax-highlighting overlay is required in the editing control itself — the organizer sees rendered output in the Setup preview pane.

#### Scenario: Monospace editing with a hint
- **WHEN** the organizer opens the description or registration-instructions field in Setup
- **THEN** the text is set in `--font-data` and a one-line syntax reminder appears beneath the field in the console's language

#### Scenario: Location hint names only the inline subset
- **WHEN** the organizer opens the location field in Setup
- **THEN** it is still a single-line control, and the reminder beneath it names links and emphasis and does not name headings, lists, quotes or rules

#### Scenario: Rendered result visible while configuring
- **WHEN** the organizer saves a markdown description in Setup
- **THEN** the Setup preview shows it rendered exactly as a fencer will see it, because the preview renders through the same components as the fencer-facing screens

## ADDED Requirements

### Requirement: Inline markdown subset
An inline markdown field SHALL honor exactly this subset: links, emphasis, strong emphasis, and inline code. Block constructs — headings, lists, block quotes, horizontal rules, fenced code, and paragraph or line breaks — SHALL NOT render as markup, and rendering an inline field SHALL NOT introduce a block element or a line break into the line that contains it. Images and tables SHALL NOT render. Text outside the honored subset SHALL be presented literally. Rendered output SHALL pass through the same allowlist sanitizer and the same single rendering entry point as long-form prose, so raw HTML, event-handler attributes and `javascript:` destinations SHALL NOT reach the document under any input.

#### Scenario: Link renders
- **WHEN** a location reads `[ZŠ Bílá](https://osm.org/go/0J0ajlLg8?m=)`
- **THEN** the line shows `ZŠ Bílá` as a link to that destination, with no brackets, parentheses or URL text visible

#### Scenario: Block syntax stays literal
- **WHEN** a location reads `# Praha` or `- Praha`
- **THEN** no heading and no list item is produced, the line does not gain a break, and the characters are presented as typed

#### Scenario: Inline field cannot inject markup
- **WHEN** a location contains `<script>alert(1)</script>`, `<img src=x onerror=alert(1)>` or `[click](javascript:alert(1))`
- **THEN** no script executes, no such element appears in the document, and no `javascript:` destination is carried

#### Scenario: Plain text location unchanged
- **WHEN** a location written before inline markdown existed reads `Sportovní hala, Praha 6`
- **THEN** it is presented exactly as written, with no characters lost or added

#### Scenario: Empty location renders nothing
- **WHEN** a tournament has no location
- **THEN** no empty element, separator, or reserved space is rendered for it

### Requirement: Inline links inside a link target
WHEN an inline markdown field is presented inside a region that is itself a link, its links SHALL be rendered as their label text only — never as a nested link — while the rest of the honored subset still renders. Elsewhere, links in an inline field SHALL follow the design system's link presentation: `--ink` with an underline, opening in a new browsing context with `rel="noopener noreferrer"`.

#### Scenario: Label only inside a linked card
- **WHEN** a location `[ZŠ Bílá](https://osm.org/go/0J0ajlLg8?m=)` appears on a card whose whole surface links to the tournament
- **THEN** the card shows `ZŠ Bílá` as plain text, the card's own link still works, and the document contains no link nested inside another link

#### Scenario: Real link outside a link target
- **WHEN** the same location appears on the tournament information screen
- **THEN** it is a link to that destination, `--ink` and underlined, opening in a new tab with `rel="noopener noreferrer"`
