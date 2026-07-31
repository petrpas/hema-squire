## Why

The tournament Setup phase and the "new tournament" dialog shipped functionally
complete but visually and semantically unfinished: the create-tournament form
renders labels and inputs on one line with no field styling, logo upload reports
"this file is not an image" for perfectly valid JPEGs, and several fields
organizers actually need when publishing a tournament (a description, a
qualification statement, links to organizers) have nowhere to live. Optional
discipline fields give no hint what belongs in them, and the extra-services table
offers when/where on items where those make no sense while missing the two
generic kinds ("other action", "other item") organizers keep asking for.

## What Changes

- **New-tournament dialog**: adopt the Setup form pattern — small-caps label above
  a full-width bottom-ruled input, all colors from `tokens.css`. No new fields.
- **Logo upload**: correct the misleading error. Distinguish "too large",
  "unsupported format", and "upload failed" instead of collapsing everything into
  "not an image", and fix the underlying cause of valid JPEGs being refused.
- **Identity section**: drop the "Základní údaje" heading — the section is the
  first thing in Setup and does not need to name itself.
- **Discipline rows**: discipline name in bold; the four optional fields (when,
  where, ruleset name, ruleset link) get hover/focus help hints explaining what
  goes in them.
- **Extra services**:
  - when/where shown only for time-and-place kinds (afterparty, seminar, other
    action), hidden for goods kinds (merch, gear rental, other item)
  - no maximum-count input for afterparty/seminar/other action — stored as 1
  - two new categories: `other_action` (behaves like afterparty/seminar) and
    `other_item` (behaves like merch)
- **Organizers**: an optional link per titular organizer row.
- **Tournament description**: a new optional multiline free-text field, stored as
  text and presented with line breaks preserved. No markdown.
- **Tournament qualification**: a new optional field between the dates and the
  logo — "open to everyone" (default) or "qualification required" with free-text
  criteria and a help hint. Informational only; it does not gate registration.

## Capabilities

### New Capabilities

None. Every change extends an existing capability.

### Modified Capabilities

- `tournament-admin`: tournament definition gains description, qualification
  (openness + criteria), and per-organizer links; discipline and extra-service
  editing gain help hints; the extra-service category enum gains `other_action`
  and `other_item`, with when/where and quantity limits conditioned on the
  category kind; logo upload errors become specific.
- `design-system`: the form pattern (small-caps label above a bottom-ruled
  field) applies to dialogs as well as panels, and a static hover/focus help hint
  is added to the component vocabulary.

### Unchanged

`registration`, `payments`, and the pricing computation are untouched — the new
fields are informational and the new categories carry the pricing behavior of the
kinds they mirror.

## Impact

- Backend: `ExtraCategory` enum (+ Alembic migration), `Tournament` model
  (description, qualification openness, qualification criteria), organizer names
  becoming name+link pairs (+ migration), schemas, tournament router, logo upload
  error mapping.
- Frontend: `TournamentPicker.tsx` (dialog), `SetupPanel.tsx` (identity,
  disciplines, extras, organizers, new qualification and description fields),
  `TournamentDetail.tsx` (present description, qualification, organizer links),
  `index.css` (dialog form fields, help-hint component), `i18n/cs.json` and
  `i18n/en.json`.
- No dependency changes. No breaking API changes for existing clients: new fields
  are optional and organizer entries stay readable as names.
