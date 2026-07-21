## ADDED Requirements

### Requirement: Single token source
All color, font, and geometry values used by Squire UI SHALL come from CSS custom properties defined once in `tokens.css`. No component SHALL hardcode a literal hex value or a font-family other than `--font-ui`, `--font-data`, or `--font-doc`.

#### Scenario: New component styling
- **WHEN** a screen or component needs a color, font, or radius
- **THEN** it references a `var(--...)` from `tokens.css` and never a literal hex code or inline font name

#### Scenario: Auditing for stray values
- **WHEN** the codebase is searched for hex color literals outside `tokens.css`
- **THEN** none are found in any `.tsx` or `.css` file

### Requirement: Typography conventions
Body text SHALL use `--font-ui` at 14px/1.5 in `--ink`, weight 400 or 500 only. Table headers and field labels SHALL be 10.5–11px uppercase with `letter-spacing: 0.12em`, weight 500, color `--ink-faded`. Data values (IDs, amounts, VS, revision numbers) SHALL use `--font-data` with `font-variant-numeric: tabular-nums` where numeric. Document titles (tournament name, form title) SHALL use `--font-doc` at 19–22px and appear nowhere else.

#### Scenario: Rendering a table header
- **WHEN** a ledger table is rendered
- **THEN** its header labels are uppercase, 10.5–11px, `--ink-faded`, with `letter-spacing: 0.12em`

#### Scenario: Rendering a monetary amount
- **WHEN** an amount is displayed in a table or payment slip
- **THEN** it uses `--font-data`, tabular numerals, is right-aligned, and shows currency after the number (e.g. "1 200 Kč")

### Requirement: Ledger table behavior
Tables SHALL have no zebra stripes. Rows are separated by a 1px `--hairline` rule; the header is underlined by a 2px `--rule-strong` rule. Row hover SHALL only change `background` to `--paper-shade`, no other hover effect. The first column SHALL show a zero-padded ordinal (`001, 002…`) in `--font-data`, colored `--ink-faded`. The table footer SHALL show a left-aligned summary and right-aligned metadata in `--font-data`.

#### Scenario: Hovering a table row
- **WHEN** a user hovers over a ledger row
- **THEN** only its background changes to `--paper-shade`; no shadow, border, or transform is applied

#### Scenario: Rendering rows
- **WHEN** a ledger table with multiple rows is rendered
- **THEN** no row has an alternating background color, and each row is separated from the next only by a 1px `--hairline` rule

### Requirement: Form (tiskopis) conventions
Forms SHALL number their sections with Roman numerals ("I.", "II.", …). Inputs SHALL have a transparent background with a bottom rule only (`1px solid var(--ink)`), switching to a 2px `--stamp` bottom rule on focus, and no full-perimeter frame. Select and checkbox inputs SHALL use a full `1px solid var(--hairline)` frame on `--paper-raised` with 2px radius. Field error messages SHALL be `--stamp`-colored, 12px, placed below the field, stating what happened and what to do, with no exclamation marks.

#### Scenario: Focusing a text input
- **WHEN** a user focuses a form text input
- **THEN** its bottom rule becomes `2px solid var(--stamp)` and no other frame or outline appears around it

#### Scenario: Validation failure
- **WHEN** a field fails validation (e.g. an invalid variable symbol)
- **THEN** an error message appears below the field in `--stamp`, 12px, describing the problem and the fix, without an exclamation mark

### Requirement: Button hierarchy
Each screen SHALL have at most one primary button (filled `--stamp`, uppercase text, `--paper` text color, 2px radius). Secondary buttons SHALL be outlined (`1px solid var(--ink)`, `--ink` text). Tertiary actions SHALL be underlined text with no frame. All button and in-text link labels SHALL be verbs or verb phrases naming the action, never generic labels like "OK" or "Submit", and in-text links SHALL be `--ink` with underline, never the browser default blue.

#### Scenario: Screen with a primary action
- **WHEN** a screen is rendered
- **THEN** at most one button uses the primary (filled `--stamp`) style

#### Scenario: Labeling a submit action
- **WHEN** a registration form's submit button is rendered
- **THEN** its label is a verb phrase describing the action (e.g. "Register fencer"), not "Submit" or "OK"

### Requirement: Tags and stamps
Category tags SHALL render as a pastel background with its matching `-ink` text color, 11px, 2px radius. The "Paid" stamp SHALL be an outlined (`1.5px solid var(--stamp)`) uppercase 10px label with `letter-spacing: 0.1em` and a rotation between −2° and +2° that is deterministically derived from the registration ID, so the same record renders the same tilt on every render. Pending payments SHALL render as plain `--ink-faded` text with the VS in `--font-data`, never as a badge.

#### Scenario: Rendering a Paid stamp twice for the same registration
- **WHEN** the same registration's "Paid" stamp is rendered on two different page loads
- **THEN** both renders show the identical rotation angle

#### Scenario: Rendering a Paid stamp for two different registrations
- **WHEN** two different registrations both show a "Paid" stamp
- **THEN** their rotation angles are independently derived from each registration's own ID (not necessarily different, but not coordinated)

#### Scenario: Pending registration
- **WHEN** a registration is unpaid and awaiting payment
- **THEN** it shows plain text "pending — VS <number>" with no badge, frame, or background fill

### Requirement: Modal and payment slip framing
Modals SHALL use a double frame (`1px solid var(--ink)` border plus a `1px solid var(--ink)` outline at 3px offset) on `--paper-raised`, with no `box-shadow`, over a `--ink` backdrop at 0.35 opacity. The SPAYD QR payment block SHALL be framed as a labeled "Payment slip" with the QR on `--paper-raised` and amount/VS in `--font-data`.

#### Scenario: Opening a modal
- **WHEN** any modal dialog opens
- **THEN** it renders with the double-frame border/outline treatment and no box-shadow

#### Scenario: Displaying the payment slip
- **WHEN** a registration's payment slip is shown
- **THEN** it is titled "Payment slip", contains the SPAYD QR code, and shows amount and VS in `--font-data`

### Requirement: Icon usage
Icons SHALL be used sparingly, only where a text label would be insufficient, and SHALL come exclusively from a single outline icon set at 1.5px stroke, 16–18px, colored from inherited text color. Filled icon variants and emoji SHALL never be used.

#### Scenario: A screen needing a status indicator
- **WHEN** a UI element could be conveyed by a text label alone
- **THEN** no icon is used

#### Scenario: A screen using an icon
- **WHEN** an icon is used because text alone is insufficient
- **THEN** it is drawn from the single outline icon set at 1.5px stroke, never filled, never emoji

### Requirement: Interaction and accessibility baseline
Every interactive element SHALL show a visible focus ring (`outline: var(--focus); outline-offset: 2px`). Transitions SHALL be limited to `background-color`/`border-color` at up to 120ms, with no transform-based hover effects; this SHALL be disabled entirely when `prefers-reduced-motion` is set. All text on paper backgrounds SHALL pass WCAG AA contrast, with `--ink-faded` restricted to 11px+ metadata and never used for primary content.

#### Scenario: Keyboard navigation
- **WHEN** a user tabs to any interactive element
- **THEN** a visible focus outline appears using `--focus`

#### Scenario: Reduced motion preference
- **WHEN** the user's OS has `prefers-reduced-motion` enabled
- **THEN** the app's 120ms color transitions are disabled

### Requirement: Wink budget
Personality/microcopy touches SHALL be limited to at most one per screen, drawn only from the four touches registered in the design spec (deterministic Paid-stamp rotation, empty-state microcopy, tiskopis form numbering, document/table footer line with revision number). None SHALL appear on error paths, failed payments, or payment-related emails. Adding a new wink requires amending `squire-design-spec.md` first, not an ad hoc addition in implementation.

#### Scenario: Counting winks on a screen
- **WHEN** any single screen is rendered
- **THEN** at most one of the four registered personality touches is visible on it

#### Scenario: Error state
- **WHEN** a screen is showing a validation error or a failed payment
- **THEN** no wink-budget personality touch is present; copy is strictly matter-of-fact

### Requirement: Global prohibitions
The implementation SHALL NOT use: gradients, `box-shadow`/`text-shadow`, blur, or glow; zebra-striped tables; `border-radius` greater than 2px; pure `#FFF` or `#000`; default browser blue links or blue focus outlines; emoji or filled icons; skeleton shimmer, spinners, or animated progress bars; toast entrance animations; font weight 600+, Title Case, or exclamation marks in system copy; more than one saturated color (`--stamp` is the only one); or any hex value outside `tokens.css`.

#### Scenario: Auditing any screen against the prohibition list
- **WHEN** any Squire screen is inspected
- **THEN** none of the prohibited patterns (gradients, shadows, zebra stripes, radius > 2px, pure white/black, blue links, emoji/filled icons, shimmer/spinners, toast entrance animation, weight 600+, Title Case, exclamation marks, a second saturated color, hex outside `tokens.css`) are present
