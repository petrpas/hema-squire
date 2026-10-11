## Why

A card's cover tint is picked from the slug, so a tournament with a green logo
can sit on a yellow cover. Matching the cover to the logo makes the card read as
one object, without letting a logo's own colors into the palette. Follows
`add-fencer-night-skin`.

## What Changes

- On logo upload the system derives the logo's dominant **hue band** — blue,
  green or warm — from its saturated, opaque pixels, and stores it with the
  tournament (`logo_tint`), or nothing where the logo has no meaningful color.
  Deleting the logo clears it. Existing logos get it in the migration.
- The list payload carries `logo_tint`.
- A card's cover uses the tint of the logo's band (blue → file-blue,
  green → seal-green, warm → form-yellow); with no logo or an achromatic one it
  falls back to the slug, as today.
- `data-tint` becomes a name (`blue | green | yellow`) instead of an index.

## Capabilities

### New Capabilities
<!-- none -->

### Modified Capabilities
- `tournament-admin`: a logo upload records the logo's hue band.
- `fencer-home`: the card's cover tint follows the logo where it has a band.

## Impact

- Backend: `Tournament.logo_tint` column + Alembic migration with backfill from
  stored logos; a pure `logo_hue_band(image)` function; upload and delete
  endpoints; `OpenTournamentOut.logo_tint`.
- Frontend: `OpenTournament.logo_tint`; `TournamentCard` cover choice; the
  three `[data-tint]` selectors in `index.css` renamed.
- No new color values: the bands are hue ranges, the colors stay the three
  pastel tokens.
