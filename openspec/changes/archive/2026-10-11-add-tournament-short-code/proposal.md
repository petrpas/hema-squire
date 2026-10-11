## Why

Where a tournament has no logo its card shows a monogram derived from its name
(`add-fencer-night-skin`). Derivation guesses wrong for some names — a series
known by its initials, a name that starts with a year or a sponsor. The organizer
should be able to say what the plate reads. Design source:
`openspec/night-skin-brief.md` §3. Optional; depends on `add-fencer-night-skin`.

## What Changes

- `Tournament.short_code: str | None`, 1–3 characters, set in tournament settings
  as "Zkratka" with a help hint saying it is used where the tournament has no logo.
- The field is prefilled with the derived monogram and stored only when the
  organizer changes it; clearing it returns to the derived one.
- The list payload carries `short_code`; the card's plate reads
  `short_code ?? monogram(display_name)`.

## Capabilities

### New Capabilities
<!-- none -->

### Modified Capabilities
- `tournament-admin`: a new optional setting, the short code.
- `fencer-home`: the plate prefers the organizer's short code to the derived monogram.

## Impact

- Backend: model column + Alembic migration, settings schema and validation,
  `OpenTournamentOut.short_code`, JSON export/import version if tournament fields
  are exported there.
- Frontend: one field in the settings dialog's identity section, `api.ts`, the
  card's plate.
