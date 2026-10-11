## ADDED Requirements

### Requirement: Skins
The system SHALL have two skins, day and night, that differ only in the values of the custom properties in `tokens.css`. The day skin is the values on `:root`. The night skin SHALL be defined as one block under `[data-skin="night"]` in `tokens.css` and nowhere else. No component SHALL read which skin is active, and no component SHALL carry a skin-specific value: a component reads `var(--paper)`, `var(--ink)`, `var(--stamp)` and the other role tokens, and the skin decides what they are.

A role token introduced for the night skin SHALL also be defined on `:root` with a day value that renders the day skin exactly as it rendered before the token existed, so introducing it changes no organizer screen.

The night skin SHALL apply to every screen rendered under the fencer layout — the tournament list, a tournament's detail and all of its tabs, and the sign-in screen when the fencer layout renders it — and to the Profile page and the not-found screen. Organizer and admin screens (the picker, the console, the admin panel) SHALL stay day. The skin follows the route, not the role: an organizer reading the public list sees night. The skin SHALL NOT follow `prefers-color-scheme` and SHALL offer no toggle.

The night root SHALL declare `color-scheme: dark`, so native controls and scrollbars match, and SHALL paint `--paper` at least to the viewport's full height, so no day paper shows on overscroll or below short content.

Both skins SHALL share: the Plex family; `--font-data` with tabular numerals for every figure; one saturated color, `--stamp`, of which `--stamp-hover` and `--stamp-on-tint` are shades and not further colors; the Paid stamp with its deterministic rotation; zero-padded ordinals; and every prohibition not carved out by name in `Global prohibitions`.

In the night skin `--ink-faded` SHALL be used only on `--paper`, `--paper-raised` and `--paper-shade`, and every `-ink` pastel token SHALL reach at least 4.5:1 on its own tint.

#### Scenario: A public screen renders night
- **WHEN** the tournament list, a tournament's detail, its entrants tab, the sign-in screen reached from the list, the Profile page, or the not-found screen is rendered
- **THEN** its root carries `data-skin="night"` and the page shows no day paper anywhere, including on overscroll

#### Scenario: An organizer screen renders day
- **WHEN** the tournament picker, a console phase or the admin panel is rendered
- **THEN** no ancestor of it carries `data-skin="night"`, and it is pixel-identical to its rendering before the night skin existed

#### Scenario: An organizer reads the public list
- **WHEN** an account that organizes tournaments opens the tournament list
- **THEN** the list renders night, the same as for any other visitor

#### Scenario: The device asks for light
- **WHEN** a visitor whose system prefers a light color scheme opens the tournament list
- **THEN** the list renders night

#### Scenario: No component knows the skin
- **WHEN** the frontend source is searched for code that reads `data-skin` or branches on the active skin
- **THEN** the only occurrences are the attributes that set it on a layout root and the selector in `tokens.css`

#### Scenario: Auditing for stray values with two skins
- **WHEN** the codebase is searched for hex color literals outside `tokens.css`
- **THEN** none are found, the night values included

### Requirement: A capacity meter is a static figure
A discipline's fill MAY be shown as a meter: a 4px track in `--paper-shade` with a fill whose width is the measured ratio of entered to capacity, capped at the full track. The meter SHALL be static. No transition and no animation SHALL be attached to it or to its fill, and it SHALL carry no motion on load or when the figure changes.

The figure SHALL also be stated as text beside the meter (`24/32`) in `--font-data` with tabular numerals, and the meter itself SHALL be `aria-hidden`: the text is the statement and the meter only draws it. A full discipline SHALL fill in `--stamp` and SHALL state `plno · +N čeká` / `full · +N waiting` in place of the fraction where a queue exists, and `plno` / `full` where none does.

This requirement sits beside `A live figure is text, not an animation` and does not relax the prohibition on animated progress bars: a meter states a measured quantity at the moment the page was built, and is redrawn only by a re-render with new data.

#### Scenario: A discipline part full
- **WHEN** a card shows a discipline with 24 of 32 places entered
- **THEN** the text beside it reads `24/32`, the meter's fill covers three quarters of its track, and the meter is hidden from assistive technology

#### Scenario: A full discipline with a queue
- **WHEN** a discipline has every place entered and three fencers waiting
- **THEN** its meter is filled to the end in `--stamp` and the text reads `plno · +3 čeká` in Czech and `full · +3 waiting` in English

#### Scenario: Nothing moves
- **WHEN** a page with meters loads, or re-renders with a changed count
- **THEN** each meter appears at its width at once, with no transition, animation, or growth from zero

### Requirement: Display headings read the display tokens
Document titles — a tournament's name, a form's title, the top bar's page title — SHALL read `--font-display` at weight `--weight-display`. In the day skin these resolve to `--font-doc` at 500, so the day renders as before. In the night skin they resolve to IBM Plex Sans Condensed at 700. IBM Plex Sans Condensed SHALL be loaded through the same mechanism as the rest of the Plex family, not a second one.

#### Scenario: A title in each skin
- **WHEN** a tournament's name is rendered on the organizer console and on the public detail
- **THEN** the console shows it in Plex Serif 500 as before, and the detail shows it in Plex Sans Condensed 700

## MODIFIED Requirements

### Requirement: Typography conventions
Body text SHALL use `--font-ui` at `--body-size`/1.5 in `--ink`, weight 400 or 500 only; `--body-size` is 14px in the day skin and 15px in the night skin. Form controls — `input`, `select` and `textarea` — SHALL draw their size from a single `--field-size` token: 14px by default, and 16px where the pointing device is coarse. Table headers and field labels SHALL be 10.5–11px uppercase with `letter-spacing: 0.12em`, weight 500, color `--ink-faded`. Data values (IDs, amounts, VS, revision numbers) SHALL use `--font-data` with `font-variant-numeric: tabular-nums` where numeric. Document titles (tournament name, form title) SHALL use `--font-display` at `--weight-display` (see `Display headings read the display tokens`) and appear nowhere else; in the day skin they are 19–22px, and in the night skin they MAY run from 20px to 30px where the fencer screens set them as the page's headline.

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
- **THEN** it is 16px from the `--field-size` token, while the body text around it stays at `--body-size`

#### Scenario: Rendering a form control under a mouse
- **WHEN** the same control is rendered on a machine driven by a fine pointer, at any window width
- **THEN** it is 14px, and the sheet's own density is unchanged

#### Scenario: Auditing a form against the body-text rule
- **WHEN** an audit finds form controls set larger than the body text on a touch device
- **THEN** the difference is the recorded 16px control size, not drift, and is left in place

#### Scenario: Body text in the night skin
- **WHEN** a paragraph is rendered on a public screen
- **THEN** it is 15px, while the same paragraph on an organizer screen is 14px

### Requirement: Modal and payment slip framing
Modals SHALL use a double frame (`1px solid var(--ink)` border plus a `1px solid var(--ink)` outline at 3px offset) on `--paper-raised`, with no `box-shadow`, over a backdrop painted in `--scrim`. `--scrim` is `--ink` at 0.35 opacity in the day skin; in the night skin, where `--ink` is light, it SHALL be a dark veil that dims the page rather than lightening it. The SPAYD QR payment block SHALL be framed as a labeled "Payment slip" with the QR on `--qr-paper` and amount/VS in `--font-data`. The QR SHALL show dark modules on a light ground in both skins, its quiet zone included: inverted codes fail in some banking applications. The code is drawn as an opaque image carrying its own light ground and quiet zone; `--qr-paper`, the ground around it, is `--paper-raised` in the day skin and a light plate in the night skin.

#### Scenario: Opening a modal
- **WHEN** any modal dialog opens
- **THEN** it renders with the double-frame border/outline treatment and no box-shadow

#### Scenario: Opening a modal on a public screen
- **WHEN** a modal dialog opens over a night screen
- **THEN** the page behind it is dimmed darker, not veiled in a light color

#### Scenario: Displaying the payment slip
- **WHEN** a registration's payment slip is shown
- **THEN** it is titled "Payment slip", contains the SPAYD QR code, and shows amount and VS in `--font-data`

#### Scenario: The QR on a night screen
- **WHEN** the payment slip is shown on a tournament's detail in the night skin
- **THEN** the QR is dark modules on a light plate that also covers its quiet zone, as it is in the day skin

### Requirement: Global prohibitions
The implementation SHALL NOT use: gradients, `box-shadow`/`text-shadow`, blur, or glow; zebra-striped tables; `border-radius` greater than 2px, EXCEPT through the skin geometry tokens `--radius-card`, `--radius-pill`, `--radius-plate` and `--radius-chip`, which are 2px in the day skin and larger only under `[data-skin="night"]`; pure `#FFF` or `#000`; default browser blue links or blue focus outlines; emoji or filled icons; skeleton shimmer, spinners, or animated progress bars; toast entrance animations; font weight 600+, EXCEPT `--weight-display` on display headings, which is 500 in the day skin and 700 only under `[data-skin="night"]`; Title Case or exclamation marks in system copy; more than one saturated color (`--stamp` is the only one, in either skin); or any hex value outside `tokens.css`.

`--radius` itself stays 2px in both skins: form fields, tags and table cells keep it, and only cards, pills, plates and status chips round. Everything else on this list binds both skins. A small solid dot marking a status beside its words is a mark, not an icon, and is not a filled icon.

#### Scenario: Auditing any screen against the prohibition list
- **WHEN** any Squire screen is inspected
- **THEN** none of the prohibited patterns (gradients, shadows, zebra stripes, radius > 2px outside the skin geometry tokens, pure white/black, blue links, emoji/filled icons, shimmer/spinners, toast entrance animation, weight 600+ outside `--weight-display`, Title Case, exclamation marks, a second saturated color, hex outside `tokens.css`) are present

#### Scenario: The carve-outs do not reach the day
- **WHEN** an organizer screen is inspected
- **THEN** no element has a radius above 2px and no text is heavier than 500, the skin tokens resolving to their day values

#### Scenario: The carve-outs do not reach a literal
- **WHEN** the stylesheet is searched for a `border-radius` or `font-weight` value
- **THEN** every radius above 2px and every weight above 500 is read through a skin token, never written as a literal
