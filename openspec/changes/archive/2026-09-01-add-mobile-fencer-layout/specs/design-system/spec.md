## MODIFIED Requirements

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
