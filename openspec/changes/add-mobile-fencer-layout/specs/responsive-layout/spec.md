## ADDED Requirements

### Requirement: One canonical breakpoint set, written as literals
The implementation SHALL use exactly three viewport breakpoints — **480px**, **768px**
and **1024px** — standing for phone-portrait, tablet or phone-landscape, and desktop.
The set SHALL be recorded as a comment in `tokens.css` as the single canonical list.

Breakpoints SHALL NOT be stored in CSS custom properties. A `@media` condition is
resolved before the cascade, so `var()` is not substituted inside it: a rule written
`@media (max-width: var(--bp-sm))` is discarded silently rather than reported, and the
page renders as though the breakpoint were never written. Every media query SHALL
therefore carry a literal length.

A width-based media query outside this set SHALL NOT be introduced. Where one already
exists it SHALL either be moved onto the set or annotated at its site as a content
threshold — the width at which a specific layout stops fitting — naming why it is not
a device breakpoint.

Capability queries — `hover`, `pointer`, `prefers-reduced-motion` — are not width
queries and this rule does not reach them. Where the real condition is what the input
device can do, the query SHALL ask that directly rather than use a width as a proxy for
it, and SHALL NOT be converted onto the breakpoint set by a later tidy-up.

#### Scenario: Adding a responsive rule
- **WHEN** a stylesheet rule needs to differ on a narrow viewport
- **THEN** its media query uses one of 480px, 768px or 1024px as a literal length, not a custom property

#### Scenario: Auditing the stylesheet for stray breakpoints
- **WHEN** the stylesheet's width-based media queries are listed
- **THEN** each is either one of the three canonical widths or carries a comment naming it a content threshold and explaining why

#### Scenario: Reading the canonical list
- **WHEN** a developer looks for the project's breakpoints
- **THEN** `tokens.css` states all three with what each stands for, and defines no breakpoint custom property

### Requirement: Form controls are sized so a mobile browser does not zoom
Form controls — `input`, `select` and `textarea` — SHALL render at 16px wherever the
pointing device is coarse. The size SHALL be defined once as a token whose value is
redefined in a single media block, so that call sites read the token and carry no media
query of their own. Everywhere else the token SHALL resolve to the 14px of body text.

The condition SHALL be the pointer and SHALL NOT be a width. Focus-zoom is a property
of touch browsers, not of narrow windows, and a width is wrong at both ends of it: a
tablet held in landscape is wider than any phone breakpoint and still zooms, while a
narrowed desktop window never does. This query therefore stands outside the canonical
breakpoint set by design, and SHALL NOT be rewritten into it.

A mobile browser that zooms the viewport when a control smaller than 16px takes focus
does not zoom back out afterwards, leaving the rest of the form off-screen. The
viewport meta SHALL NOT use `user-scalable=no` or a maximum scale to suppress that
zoom: doing so disables pinch-zoom everywhere, including where a user needs it, and is
an accessibility regression.

The rule SHALL reach every control a person types into, including controls smaller
than the 14px body size. A control whose size is inherited from a data table, and which
is edited only with a pointer on a desktop instrument, is exempt.

#### Scenario: Focusing a field on a mobile browser
- **WHEN** a fencer taps the e-mail field on the sign-in card on a touch device
- **THEN** the control is 16px, the viewport does not zoom, and the rest of the form stays visible

#### Scenario: A tablet too wide for any phone breakpoint
- **WHEN** the same card is opened on a tablet held in landscape, wider than every breakpoint in the canonical set
- **THEN** the control is still 16px, because the condition is the pointer and not the width

#### Scenario: The same control on a desktop instrument
- **WHEN** a control is rendered on a machine driven by a mouse, at any window width
- **THEN** it is 14px, and the density of the screen around it is unchanged

#### Scenario: One value, in one place
- **WHEN** the stylesheet is audited for the control size
- **THEN** it is defined in one token and redefined in one media block, and no individual component sets a control size of its own

#### Scenario: Registration checklist quantity field
- **WHEN** a fencer types a quantity into the registration checklist on a phone
- **THEN** that control is 16px and the viewport does not zoom, rather than the 13px it was set at

#### Scenario: Viewport meta
- **WHEN** the document's viewport meta tag is inspected
- **THEN** it sets `width=device-width` and `initial-scale=1.0` and constrains neither user scaling nor maximum scale

### Requirement: Frames measure the dynamic viewport and respect device insets
Any element sized to the height of the screen SHALL use dynamic viewport units
(`dvh`), not `vh`. On a mobile browser `vh` resolves against the viewport measured
without the address bar, so a full-height frame extends past the bottom of the screen
and its lowest content cannot be reached.

Content pinned to the top or bottom edge of the screen SHALL add the corresponding
`env(safe-area-inset-*)` to its padding, so it does not fall under a device's home
indicator or notch. The inset SHALL be added to the element's existing padding in a
way that degrades to that padding where `env()` is unsupported.

#### Scenario: Full-height application frame on a phone
- **WHEN** the app shell renders on a mobile browser showing its address bar
- **THEN** the shell's height matches the visible viewport and its bottom-most content is reachable without scrolling past the screen edge

#### Scenario: Sticky bar on a device with a home indicator
- **WHEN** a bar pinned to the bottom of the screen renders on a device reporting a bottom safe-area inset
- **THEN** its content sits above the home indicator rather than beneath it

#### Scenario: A dialog taller than the screen
- **WHEN** a dialog constrained to a fraction of the screen height opens on a mobile browser
- **THEN** that fraction is measured against the dynamic viewport, and the dialog's actions are reachable

### Requirement: Touch targets grow by spacing, never by type size
Below 768px, every element a person can activate — buttons, tabs, link-buttons, row
actions and chips — SHALL present an activation area of at least 44 × 44 CSS pixels.

That area SHALL be reached by increasing vertical padding alone. `font-size` and
`letter-spacing` SHALL be held at their desktop values. Enlarging type on a narrow
screen would collapse the distinction between the 11px uppercase label register and
14px body text that the design system rests on; the intended result is the same
official density, set more airily.

#### Scenario: Tapping a filter tab on a phone
- **WHEN** a fencer taps a tab in the tab control on a 390px-wide screen
- **THEN** the tab's activation area is at least 44px tall and its label is the same size and letter-spacing as on desktop

#### Scenario: An icon-only row action on a phone
- **WHEN** an icon-only action such as the detail page's close control renders below 768px
- **THEN** its activation area is at least 44 × 44px while the icon itself is unchanged

### Requirement: Hover effects are declared by pointer capability or given a resting form
On a touch screen there is no hover, and a mobile browser emulates it stickily: the
first tap applies the hover state and only a second tap activates the element. Every
`:hover` rule SHALL therefore be classified and treated by what it is for.

A hover rule that only acknowledges the pointer, on an element already fully visible
and legible at rest, SHALL be enclosed in `@media (hover: hover)`.

A hover rule that is the only signal an action exists SHALL, below 768px, be given a
resting form that is always visible. That resting form SHALL be drawn from the
existing visual vocabulary — a rule, a hairline, an existing token — and SHALL NOT
introduce an icon, a second saturated colour, or any prohibited treatment.

A hover rule already paired with a `:focus` or `:focus-within` twin on a focusable
element SHALL be left as it is: a tap focuses that element and reveals the same state.

#### Scenario: A decorative hover rule
- **WHEN** a rule only changes an already-visible control's background under the pointer
- **THEN** it is enclosed in `@media (hover: hover)` and never applies on a touch device

#### Scenario: Hover as the sole affordance
- **WHEN** a list's rows are borderless and their only clickable signal is a hover background
- **THEN** below 768px those rows carry a permanently visible affordance drawn from the existing vocabulary

#### Scenario: A hint revealed on hover and focus alike
- **WHEN** a hint box is revealed by both `:hover` and `:focus` on a focusable marker
- **THEN** the rule is unchanged, and tapping the marker reveals the hint

### Requirement: A tab control too wide for the screen becomes one scrolling band
WHEN a tab control's tabs are together wider than the viewport below 768px, the
control SHALL become a full-width, horizontally scrollable band rather than wrap,
shrink its labels, or overflow the screen.

The band SHALL snap along its horizontal axis and SHALL hide its scrollbar. The 1px
rules dividing the tabs and the control's own frame SHALL be retained: it is a strip
cut from a printed form, not a row of pills, and dropping the frame would be the
rounded-and-floating treatment the design prohibitions exclude.

WHEN the selected tab changes, and on first render, the selected tab SHALL be scrolled
into view centred along the horizontal axis only. Vertical scroll position SHALL NOT
be altered by that operation — moving the page vertically to centre a tab jumps the
whole workspace beneath a sticky bar.

The mechanism SHALL be defined once and applied wherever a tab control needs it,
rather than reimplemented per screen.

#### Scenario: Four filter tabs on a narrow phone
- **WHEN** the fencer's four filter tabs render on a 390px screen
- **THEN** they occupy one full-width band that scrolls horizontally, keeping their dividing rules and outer frame, with no visible scrollbar and no sideways scrolling of the page

#### Scenario: The selected tab starts out of view
- **WHEN** a fencer loads the page with the last tab selected and the band is scrolled to its start
- **THEN** the selected tab is scrolled to the centre of the band, and the page's vertical scroll position is unchanged

#### Scenario: A second tab control needing the same treatment
- **WHEN** the tournament detail page's tab control is too wide below 768px
- **THEN** it uses the same band mechanism as the filter tabs, not a separate implementation

### Requirement: A bar fixed to the top of the screen scrolls with the document
A bar held at the top of the viewport SHALL be positioned `sticky`, never `fixed`.
A `fixed` element is removed from the document flow and, in mobile browsers that
collapse their address bar during a scroll, detaches and judders against the content
it should sit above.

#### Scenario: Scrolling a long list on a phone
- **WHEN** a fencer scrolls a long tournament list on a mobile browser whose address bar collapses
- **THEN** the top bar stays at the top of the content without detaching, jumping, or overlapping the list

### Requirement: Responsive rules live with the component they modify
A responsive rule SHALL be written in its own component's block in the stylesheet,
adjacent to the rules it modifies. The stylesheet SHALL NOT collect responsive rules
into a trailing section grouped by breakpoint.

Where a layout can adapt without a media query it SHALL: intrinsic sizing (`min()`,
`clamp()`), `flex-wrap`, and `repeat(auto-fit, minmax(...))` are the first choice. A
media query binds to the size of the window rather than the size of the element's
container, so it stops matching correctly after a layout is rearranged, and it does so
without any error.

#### Scenario: Adding a narrow-screen rule for a component
- **WHEN** a component needs a different layout below a breakpoint
- **THEN** the rule sits in that component's own block in the stylesheet, not in a section at the end of the file

#### Scenario: A card wider than a narrow screen
- **WHEN** a fixed-width card would overflow a 360px viewport
- **THEN** it is constrained by intrinsic sizing rather than by a media query
