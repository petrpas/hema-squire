# design-system Specification

## Purpose
Define the Bureau 1952 visual design system for Squire UI: a single CSS token source, typography conventions, ledger table behavior, form conventions, button hierarchy, tags/stamps, modal and payment-slip framing, icon usage, an accessibility baseline, a bounded personality "wink budget", a global list of prohibited patterns, and the narrow admission of a live text figure — so all screens read as one coherent, restrained, paper-ledger-inspired system.
## Requirements
### Requirement: Single token source
All color, font, and geometry values used by Squire UI SHALL come from CSS custom properties defined once in `tokens.css`. No component SHALL hardcode a literal hex value or a font-family other than `--font-ui`, `--font-data`, or `--font-doc`.

#### Scenario: New component styling
- **WHEN** a screen or component needs a color, font, or radius
- **THEN** it references a `var(--...)` from `tokens.css` and never a literal hex code or inline font name

#### Scenario: Auditing for stray values
- **WHEN** the codebase is searched for hex color literals outside `tokens.css`
- **THEN** none are found in any `.tsx` or `.css` file

### Requirement: Typography conventions
Body text SHALL use `--font-ui` at 14px/1.5 in `--ink`, weight 400 or 500 only. Form controls — `input`, `select` and `textarea` — SHALL draw their size from a single `--field-size` token: 14px by default, and 16px where the pointing device is coarse. Table headers and field labels SHALL be 10.5–11px uppercase with `letter-spacing: 0.12em`, weight 500, color `--ink-faded`. Data values (IDs, amounts, VS, revision numbers) SHALL use `--font-data` with `font-variant-numeric: tabular-nums` where numeric. Document titles (tournament name, form title) SHALL use `--font-doc` at 19–22px and appear nowhere else.

The 16px narrow-viewport size is deliberate and SHALL NOT be reverted. A mobile browser zooms the viewport when a control smaller than 16px takes focus and does not zoom back out, which pushes the rest of a form off-screen; the alternative countermeasure, suppressing user scaling in the viewport meta, is an accessibility regression and is prohibited.

The token SHALL be redefined in exactly one place — the token file, under one media block — and call sites SHALL read the token rather than carry media queries of their own, so that at any given width one value governs every control and no component can disagree with another.

A control whose size is inherited from the density of a data table it sits in — the console sheet's editable cell — is exempt, since it is edited with a pointer on a desktop instrument and raising it would change every row's height.

#### Scenario: Rendering a table header
- **WHEN** a ledger table is rendered
- **THEN** its header labels are uppercase, 10.5–11px, `--ink-faded`, with `letter-spacing: 0.12em`

#### Scenario: Rendering a monetary amount
- **WHEN** an amount is displayed in a table or payment slip
- **THEN** it uses `--font-data`, tabular numerals, is right-aligned, and shows currency after the number (e.g. "1 200 Kč")

#### Scenario: Rendering a form control on a touch device
- **WHEN** a text input, select, or textarea is rendered on a device whose pointer is coarse
- **THEN** it is 16px from the `--field-size` token, while the body text around it stays 14px

#### Scenario: Rendering a form control under a mouse
- **WHEN** the same control is rendered on a machine driven by a fine pointer, at any window width
- **THEN** it is 14px, matching the body text, and the sheet's own density is unchanged

#### Scenario: Auditing a form against the body-text rule
- **WHEN** an audit finds form controls set larger than the 14px body text on a touch device
- **THEN** the difference is the recorded 16px control size, not drift, and is left in place

### Requirement: Ledger table behavior
Tables SHALL have no zebra stripes. Rows are separated by a 1px `--hairline` rule; the header is underlined by a 2px `--rule-strong` rule. Row hover SHALL only change `background` to `--paper-shade`, no other hover effect. The first column SHALL show a zero-padded ordinal (`001, 002…`) in `--font-data`, colored `--ink-faded`. The table footer SHALL show a left-aligned summary and right-aligned metadata in `--font-data`.

#### Scenario: Hovering a table row
- **WHEN** a user hovers over a ledger row
- **THEN** only its background changes to `--paper-shade`; no shadow, border, or transform is applied

#### Scenario: Rendering rows
- **WHEN** a ledger table with multiple rows is rendered
- **THEN** no row has an alternating background color, and each row is separated from the next only by a 1px `--hairline` rule

### Requirement: Form (tiskopis) conventions
Forms SHALL number their sections with Roman numerals ("I.", "II.", …). Every labeled field, in panels and in modal dialogs alike, SHALL place its label above the control, styled per the typography conventions (10.5–11px uppercase, `letter-spacing: 0.12em`, weight 500, `--ink-faded`), with the control occupying the full width of its container. Inputs SHALL have a transparent background with a bottom rule only (`1px solid var(--ink)`), switching to a 2px `--stamp` bottom rule on focus, and no full-perimeter frame. Multiline text areas SHALL follow the same treatment and SHALL resize vertically only. Select and checkbox inputs SHALL use a full `1px solid var(--hairline)` frame on `--paper-raised` with 2px radius. Field error messages SHALL be `--stamp`-colored, 12px, placed below the field, stating what happened and what to do, with no exclamation marks.

A field carrying an error SHALL mark itself with a `1px solid var(--stamp)` bottom rule, thickening to 2px on focus exactly as a valid field does, and SHALL carry `aria-invalid` with its message associated by `aria-describedby`. No other visual treatment SHALL signal invalidity: no browser default outline, no glow, no background fill, no icon, no animation. Numeric fields SHALL be rendered as text controls with a numeric input mode rather than native number inputs, so no separator a user types is discarded by the browser and no spinner appears.

When a save is blocked because fields need attention, the save control SHALL state so plainly — what is wrong and how many fields — in the same 12px `--stamp` text as a field error, with no exclamation mark, and the statement SHALL move focus to the first invalid field when activated.

#### Scenario: Focusing a text input
- **WHEN** a user focuses a form text input
- **THEN** its bottom rule becomes `2px solid var(--stamp)` and no other frame or outline appears around it

#### Scenario: Validation failure
- **WHEN** a field fails validation (e.g. an invalid variable symbol)
- **THEN** an error message appears below the field in `--stamp`, 12px, describing the problem and the fix, without an exclamation mark

#### Scenario: Marking the invalid field itself
- **WHEN** a field is showing an error message
- **THEN** its bottom rule is `--stamp`-colored, it reports `aria-invalid`, its message is reachable through `aria-describedby`, and no outline, glow, fill or icon is added

#### Scenario: A numeric field
- **WHEN** a form presents a field that accepts only numbers
- **THEN** it is a text control with a numeric input mode, showing no spinner and accepting a typed decimal comma or point without discarding it

#### Scenario: A blocked save
- **WHEN** a save is attempted while fields in that section are invalid
- **THEN** the save control states how many fields need attention in 12px `--stamp` text without an exclamation mark, and activating that statement focuses the first invalid field

#### Scenario: Field inside a modal dialog
- **WHEN** a form field is rendered inside a modal dialog
- **THEN** its label sits above the control in the uppercase label style and the control spans the dialog's content width, identical to the same field rendered in a panel

#### Scenario: Multiline field
- **WHEN** a form presents a multiline text area
- **THEN** it carries the same label-above, transparent, bottom-ruled treatment as single-line inputs and can be resized vertically but not horizontally

### Requirement: Field help hints
A form field MAY carry a help hint explaining what belongs in it. The hint SHALL be reached through a marker placed after the field's label, drawn from the outline icon set or as a bordered glyph in `--ink-faded`, never an emoji and never filled. The hint SHALL be revealed on pointer hover **and** on keyboard focus of the marker, and SHALL be rendered as a static box on `--paper-raised` with a `1px solid var(--ink)` border and 2px radius — with no shadow, no blur, no transition, and no entrance animation. The marker SHALL be a focusable control associated with the hint text via `aria-describedby`. Help hints SHALL be reserved for fields whose expected content is not evident from the label; they SHALL NOT replace field labels or error messages.

A revealed hint SHALL be legible in full, above every element it overlaps — including the neighbouring cells of a sticky table header it is opened from, and the rows beneath it. Nothing on the page SHALL paint over an open hint box.

#### Scenario: Revealing a hint by pointer
- **WHEN** a user hovers the help marker next to a field label
- **THEN** the hint text appears in a static bordered box with no shadow and no animation, and disappears when the pointer leaves

#### Scenario: Revealing a hint by keyboard
- **WHEN** a user tabs to the help marker
- **THEN** the same hint box appears and the marker's `aria-describedby` resolves to the hint text

#### Scenario: A self-evident field
- **WHEN** a field's label already states what belongs in it
- **THEN** no help marker is rendered

#### Scenario: Hint opened from a table header
- **WHEN** a user reveals the hint on a column header that has other column headers to its right in the same sticky header row
- **THEN** the whole hint box is readable above those headers, with no part of it hidden behind them

### Requirement: Button hierarchy
Each screen SHALL have at most one primary button (filled `--stamp`, uppercase text, `--paper` text color, 2px radius). Secondary buttons SHALL be outlined (`1px solid var(--ink)`, `--ink` text). Tertiary actions SHALL be underlined text with no frame. All button and in-text link labels SHALL be verbs or verb phrases naming the action, never generic labels like "OK" or "Submit", and in-text links SHALL be `--ink` with underline, never the browser default blue.

#### Scenario: Screen with a primary action
- **WHEN** a screen is rendered
- **THEN** at most one button uses the primary (filled `--stamp`) style

#### Scenario: Labeling a submit action
- **WHEN** a registration form's submit button is rendered
- **THEN** its label is a verb phrase describing the action (e.g. "Register fencer"), not "Submit" or "OK"

### Requirement: Destructive actions
An action that ends or rewrites something the user already holds — cancelling a registration, amending one that is already reserved or paid — SHALL be presented as a destructive control: outlined in `--stamp` with `--stamp` text, never filled, so it stays distinct from the screen's single primary button and adds no second saturated color.

A destructive control SHALL ask for confirmation before acting. The confirmation SHALL be the static, unanimated pattern already used for cancellation — a plain statement of the consequence with a pair of controls, one confirming and one abandoning — and SHALL NOT be a browser dialog.

WHERE two or more destructive controls stand together, they SHALL be laid out as one centered row with space between them, so neither reads as the continuation of the other and neither can be hit by aiming at its neighbour.

#### Scenario: A destructive control is drawn
- **WHEN** a screen offers a cancel-registration control
- **THEN** it is outlined in `--stamp` with `--stamp` text, unfilled, and the screen's primary button remains the only filled one

#### Scenario: Confirmation before acting
- **WHEN** a user activates a destructive control
- **THEN** a static confirmation states what will happen and offers confirming and abandoning controls, with no animation and no browser dialog

#### Scenario: Two destructive controls together
- **WHEN** a screen offers both amend and cancel
- **THEN** the two stand in one centered row separated by space

#### Scenario: Abandoning changes nothing
- **WHEN** a user abandons the confirmation
- **THEN** nothing is sent, and the screen returns to the state it was in

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

One departure is admitted, and only this one: a confirmation that a momentary action succeeded — the note beside a copied payment field being the case this system has — MAY leave by a transition on `opacity` of up to 400ms. It SHALL appear instantly, with no entrance transition of any kind, and SHALL occupy its space whether or not it is showing, so that its arrival and departure move nothing around it. This is the fade-out the global prohibitions already contemplate when they bar toast entrance animations, stated here so a later audit reads a 400ms opacity transition as sanctioned rather than as drift from the 120ms rule.

A hover rule SHALL additionally be declared by pointer capability or given a resting form, per the `responsive-layout` capability: on a touch screen hover does not exist and is emulated stickily, so a rule left ungated costs the first tap.

#### Scenario: Keyboard navigation
- **WHEN** a user tabs to any interactive element
- **THEN** a visible focus outline appears using `--focus`

#### Scenario: Reduced motion preference
- **WHEN** the user's OS has `prefers-reduced-motion` enabled
- **THEN** the app's 120ms color transitions are disabled, and so is the confirmation fade-out

#### Scenario: Confirming a copied value
- **WHEN** a fencer copies a payment field and the confirmation note appears
- **THEN** it appears at once with no entrance animation, holds, then leaves by fading out, and nothing around it moves as it comes or goes

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

### Requirement: A live figure is text, not an animation
A figure that changes because the value it states has changed — a countdown to a known moment being the case this system has — SHALL be admitted, and SHALL be drawn as a line of type in the ordinary ink of its context. It is distinct from the animated progress indicators the prohibitions forbid: those move to suggest progress they do not measure, while a live figure only ever states a measured quantity.

Such a figure SHALL NOT be accompanied by a bar, a ring, a track, a fill, a spinner, or any decoration that moves. No CSS animation and no transition SHALL be attached to it or to its container. It SHALL use tabular numerals at a fixed width so that its line neither reflows nor shifts as its digits change — the jitter, not the change of value, is what would read as animation.

A live figure SHALL update no more often than once per second, and SHALL be shown only while its value is worth watching. Where a figure counts towards a moment, it SHALL stop at that moment rather than continue past it, and SHALL never present a negative quantity.

This requirement admits nothing else: it does not relax the prohibition on skeleton shimmer, spinners, or animated progress bars, and it is not a licence to animate a value that is not being measured.

#### Scenario: A countdown is drawn
- **WHEN** a screen counts down to a known moment
- **THEN** the figure is a line of type in the surrounding ink, with no bar, ring, track, fill, or spinner beside it

#### Scenario: Digits change without moving the line
- **WHEN** a live figure ticks from one value to the next
- **THEN** its line keeps its width and its position, and nothing fades, slides, or fills

#### Scenario: The figure stops at its moment
- **WHEN** a countdown reaches the moment it counts towards
- **THEN** it stops and is replaced by what the moment brings, and no negative figure is shown

#### Scenario: The prohibition still stands
- **WHEN** a screen is waiting on work whose duration is unknown
- **THEN** no spinner, shimmer, or animated progress bar is drawn, and this requirement does not permit one

