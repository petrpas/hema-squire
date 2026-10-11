## MODIFIED Requirements

### Requirement: Skins
The system SHALL have two skins, day and night, that differ only in the values of the custom properties in `tokens.css`. The day skin is the values on `:root`. The night skin SHALL be defined as one block under `[data-skin="night"]` in `tokens.css` and nowhere else. No component SHALL read which skin is active, and no component SHALL carry a skin-specific value: a component reads `var(--paper)`, `var(--ink)`, `var(--stamp)` and the other role tokens, and the skin decides what they are.

A role token introduced for the night skin SHALL also be defined on `:root` with a day value that renders the day skin exactly as it rendered before the token existed, so introducing it changes no organizer screen.

The night skin SHALL apply to every screen rendered under the fencer layout — the tournament list, a tournament's detail and all of its tabs, and the sign-in screen when the fencer layout renders it — and to the Profile page and the not-found screen. Organizer and admin screens (the picker, the console, the admin panel) SHALL stay day, with one exception: the console's preview of the public page wears the night skin on its own panel, since what it previews is a night screen (`setup-preview`). The skin follows the route, not the role: an organizer reading the public list sees night. The skin SHALL NOT follow `prefers-color-scheme` and SHALL offer no toggle.

The night root SHALL declare `color-scheme: dark`, so native controls and scrollbars match, and SHALL paint `--paper` at least to the viewport's full height, so no day paper shows on overscroll or below short content.

Both skins SHALL share: the Plex family; `--font-data` with tabular numerals for every figure; one saturated color, `--stamp`, of which `--stamp-hover` and `--stamp-on-tint` are shades and not further colors; the Paid stamp with its deterministic rotation; zero-padded ordinals; and every prohibition not carved out by name in `Global prohibitions`.

In the night skin `--ink-faded` SHALL be used only on `--paper`, `--paper-raised` and `--paper-shade`, and every `-ink` pastel token SHALL reach at least 4.5:1 on its own tint.

#### Scenario: A public screen renders night
- **WHEN** the tournament list, a tournament's detail, its entrants tab, the sign-in screen reached from the list, the Profile page, or the not-found screen is rendered
- **THEN** its root carries `data-skin="night"` and the page shows no day paper anywhere, including on overscroll

#### Scenario: An organizer screen renders day
- **WHEN** the tournament picker, a console phase or the admin panel is rendered
- **THEN** no ancestor of it carries `data-skin="night"`, and it is pixel-identical to its rendering before the night skin existed; the Setup preview panel alone carries the attribute, on itself

#### Scenario: An organizer reads the public list
- **WHEN** an account that organizes tournaments opens the tournament list
- **THEN** the list renders night, the same as for any other visitor

#### Scenario: The device asks for light
- **WHEN** a visitor whose system prefers a light color scheme opens the tournament list
- **THEN** the list renders night

#### Scenario: No component knows the skin
- **WHEN** the frontend source is searched for code that reads `data-skin` or branches on the active skin
- **THEN** the only occurrences are the attributes that set it on a layout root or the preview panel, and the selector in `tokens.css`

#### Scenario: Auditing for stray values with two skins
- **WHEN** the codebase is searched for hex color literals outside `tokens.css`
- **THEN** none are found, the night values included

### Requirement: Button hierarchy
Each screen SHALL have at most one primary button (filled `--stamp`, uppercase text, `--paper` text color, `--radius-pill`). Secondary buttons SHALL be outlined (`1px solid var(--ink)`, `--ink` text) at `--radius-pill`. `--radius-pill` is 2px in the day skin, so the console's buttons are unchanged; in the night skin every button is a pill. Tertiary actions SHALL be underlined text with no frame. All button and in-text link labels SHALL be verbs or verb phrases naming the action, never generic labels like "OK" or "Submit", and in-text links SHALL be `--ink` with underline, never the browser default blue.

#### Scenario: Screen with a primary action
- **WHEN** a screen is rendered
- **THEN** at most one button uses the primary (filled `--stamp`) style

#### Scenario: Labeling a submit action
- **WHEN** a registration form's submit button is rendered
- **THEN** its label is a verb phrase describing the action (e.g. "Register fencer"), not "Submit" or "OK"

#### Scenario: A button on each side
- **WHEN** the registration form's submit button is shown on a tournament's public detail and a console save button is shown in Setup
- **THEN** the first is a pill and the second keeps its 2px corners
