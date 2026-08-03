## Why

Four defects reported from live use, all in screens a fencer or an organizer meets daily. The tournament detail page cannot be read to the end — its content is clipped with no way to scroll — and it stacks every section flush against the next. The registration form offers an afterparty and four weapon rentals nobody configured. The discipline dialog, reopened on an existing discipline, shows derived values instead of the name and slug that discipline actually carries, so confirming it silently rewrites them. And a slug help hint opened in the disciplines table is painted behind the neighbouring column headers.

None of these need new capability; they need the existing screens to behave as their specs already imply, plus one deliberate restructuring of the detail page from a link-and-screen model into tabs.

## What Changes

**Tournament detail page (fencer-facing)**

- The page SHALL scroll to its end. Its content container currently clips overflow, so the lower half of a long tournament is unreachable.
- Sections SHALL be separated by vertical space instead of sitting flush against one another.
- The logo SHALL be shown at twice its present size and without a frame.
- The information/register split becomes a two-tab header: the tournament name at the left, then `Tournament` and `Register` — reading `Registered` when the account holds a registration — then a close control at the far right. This replaces the "Back to tournaments" link and the "Back to information" link, and replaces the Register button on the information screen.
- Closing returns to whatever list the page was opened from.

**Registration form**

- The legacy fixed-fee rows — one `Afterparty` row and one row per taxonomy weapon for rental — SHALL no longer be rendered. They appear today for any tournament that configures no extra services at all, which is every new tournament, so the form asks about things the organizer never offered. Only itemized extra services remain.
- The free-text note to the organizer stays (owner decision, 2026-08-02).
- The legacy fee columns, their setup fields, and any imported values are untouched (owner decision, 2026-08-02) — this is a rendering change only.
- Vertical space SHALL be set before the registration instructions and before the total, and the total SHALL be aligned to the right edge of the priced list it closes.

**Discipline dialog**

- Reopening the dialog on an existing discipline SHALL show that discipline's stored name and slug, not values re-derived from its classification. Derivation continues to drive a newly added discipline and continues to stop per field once typed into.

**Help hints**

- A help hint opened from a table header SHALL be legible above the neighbouring headers rather than painted behind them.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `fencer-home`: the tournament detail page's shell — tabbed navigation between information and registration, a close control instead of back links, a scrollable body, section spacing, and logo presentation.
- `registration`: the registration form no longer renders the legacy fixed-fee rows; the instructions and total gain their own spacing and the total is right-aligned.
- `tournament-admin`: the discipline dialog states the stored name and slug when reopened on an existing discipline.
- `design-system`: a help hint reveals above adjacent sticky table headers.

## Impact

Frontend only; no API, schema, or migration.

- `frontend/src/TournamentDetail.tsx` — tab header, close control, container that scrolls.
- `frontend/src/TournamentFace.tsx` — legacy row removal (`legacy` flag at line 559), instructions and total spacing.
- `frontend/src/DisciplineDialog.tsx` — derivation effect must not overwrite loaded values on reopen.
- `frontend/src/index.css` — `.setup-panel` reuse on the detail page, `.detail-logo`, section gap, `.form-total`, sticky-header stacking for `.help-hint-box`.
- `frontend/src/i18n/{cs,en}.json` — tab labels and the close control's accessible name; the removed legacy rows' keys go with them.

Not affected: the console's own Setup panel and preview keep rendering through the same fencer-facing components, so the form changes land in the preview for free.
