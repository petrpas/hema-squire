# organizer-prose Specification

## Purpose
Define the markdown contract for organizer-authored long-form text — which fields are markdown, the honored subset, the sanitizer allowlist and the guarantee that no organizer input can inject markup, the link and heading presentation rules, plain-text back-compatibility, and the monospace authoring affordance in Setup.

## Requirements

### Requirement: Markdown-authored prose fields
The organizer-authored long-form text fields — the tournament `description` and the tournament `registration instructions` — SHALL be authored in markdown and presented as formatted content. The stored value SHALL always be the organizer's markdown source, unmodified: the system SHALL NOT store rendered output, and SHALL NOT rewrite, normalize, or escape the source on save. Rendering SHALL happen at presentation time only. No other field SHALL be treated as markdown; subtitle, location, qualification criteria, organizer names, discipline fields, and extra-item names, `when`, `where` and `remark` remain plain text.

#### Scenario: Source stored verbatim
- **WHEN** the organizer saves a description containing `## Program`, `- longsword`, and `**bring a mask**`
- **THEN** the stored value contains exactly those characters, and re-opening the Setup field shows the same markdown source the organizer typed

#### Scenario: Presented as formatted content
- **WHEN** a fencer opens the information screen of that tournament
- **THEN** `## Program` is presented as a heading, `- longsword` as a list item, and `bring a mask` in emphasized weight, with no markup characters visible

#### Scenario: Non-prose fields unaffected
- **WHEN** an organizer types `**Praha**` into the tournament location or an extra item's remark
- **THEN** the text is presented literally, asterisks included, because those fields are not markdown

### Requirement: Honored markdown subset
Rendering SHALL honor exactly this subset: paragraphs; soft line breaks (a single newline inside a paragraph renders as a line break); emphasis and strong emphasis; unordered and ordered lists, including nesting; headings of level 3 and level 4; links; block quotes; inline code and fenced code; and horizontal rules. Constructs outside this subset SHALL NOT render as markup. Headings written at level 1 or 2 SHALL be presented at the level-3 heading style rather than dropped, so an organizer who starts a document at `#` still gets structure. Images and tables SHALL NOT render.

#### Scenario: Subset renders
- **WHEN** a description uses paragraphs, `**strong**`, `*emphasis*`, a bullet list, a numbered list, `### heading`, `> quote`, `` `code` `` and `---`
- **THEN** each renders as its corresponding element

#### Scenario: Top-level headings demoted
- **WHEN** a description begins with `# Turnaj` and later has `## Program`
- **THEN** both are presented at the level-3 heading style, and no heading larger than the screen's own document heading appears

#### Scenario: Images and tables not rendered
- **WHEN** a description contains `![logo](https://example.com/x.png)` or a pipe table
- **THEN** no image element and no table element is produced

### Requirement: Rendered output is sanitized
Rendered output SHALL pass through an allowlist sanitizer before reaching the document. The sanitizer SHALL permit only the element set implied by the honored subset and only the attributes those elements require; every other element and attribute SHALL be removed. Raw HTML written in the source, including `<script>`, `<style>`, `<iframe>`, event-handler attributes, and `javascript:` URLs, SHALL NOT reach the document under any input. This guarantee SHALL hold for content authored by any organizer, and SHALL NOT depend on validation performed at save time.

#### Scenario: Embedded script neutralized
- **WHEN** a description contains `<script>alert(1)</script>` or `<img src=x onerror=alert(1)>`
- **THEN** no script executes and no such element appears in the document

#### Scenario: Dangerous link scheme dropped
- **WHEN** a description contains `[click](javascript:alert(1))`
- **THEN** the resulting element carries no `javascript:` destination

#### Scenario: Sanitizer is the last step
- **WHEN** any prose field is presented anywhere in the application
- **THEN** the content it renders has passed through the same single rendering entry point, and no call site inserts unsanitized markup

### Requirement: Prose presentation follows the design system
Rendered prose SHALL obey the design system's prohibitions and token discipline. Links SHALL be `--ink` with an underline, never the browser default blue; links to external destinations SHALL open in a new browsing context with `rel="noopener noreferrer"`. Headings SHALL use the existing type scale at weight 500 and SHALL NOT exceed the surrounding screen's own heading in size. Block quotes SHALL be marked by a hairline rule and `--ink-soft` text, not by a background fill. Code SHALL be set in `--font-data`. No color outside `tokens.css` SHALL be introduced, and no rendered element SHALL carry a shadow, gradient, or radius greater than 2px.

#### Scenario: Link presentation
- **WHEN** a rendered description contains a link to an external site
- **THEN** it is `--ink` and underlined, opens in a new tab, and carries `rel="noopener noreferrer"`

#### Scenario: Prose stays within the token set
- **WHEN** rendered prose is inspected on the information screen and on the registration form
- **THEN** every color, font and radius it uses comes from `tokens.css`, and none of the global prohibitions is present

### Requirement: Plain text stays correct
Text authored before markdown rendering existed, and text authored by an organizer who never uses markdown, SHALL keep rendering as written: paragraph breaks and single line breaks preserved, no characters lost. An empty or unset prose field SHALL render nothing at all — no empty block, rule, or spacing.

#### Scenario: Legacy plain-text description
- **WHEN** a description written as three plain paragraphs with single line breaks inside them is presented
- **THEN** the paragraphs and the line breaks inside them appear exactly as they did before markdown rendering was introduced

#### Scenario: Empty field renders nothing
- **WHEN** a tournament has no description and no registration instructions
- **THEN** neither screen shows an empty prose block or reserved space for one

### Requirement: Markdown authoring affordance in Setup
In the console Setup phase, each markdown prose field SHALL be edited in a monospace (`--font-data`) multiline control, and SHALL carry a localized one-line reminder of the honored syntax beneath it. The control SHALL accept and preserve exactly the characters typed; it SHALL NOT auto-format, auto-complete, or transform the source. No live preview or syntax-highlighting overlay is required in the editing control itself — the organizer sees rendered output in the Setup preview pane.

#### Scenario: Monospace editing with a hint
- **WHEN** the organizer opens the description or registration-instructions field in Setup
- **THEN** the text is set in `--font-data` and a one-line syntax reminder appears beneath the field in the console's language

#### Scenario: Rendered result visible while configuring
- **WHEN** the organizer saves a markdown description in Setup
- **THEN** the Setup preview shows it rendered exactly as a fencer will see it, because the preview renders through the same components as the fencer-facing screens
