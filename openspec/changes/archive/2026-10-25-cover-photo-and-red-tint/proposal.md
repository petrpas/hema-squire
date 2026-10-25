## Why

The cover band behind a tournament's plate can only be one of three pastels, and the organizer's choice among them stops at blue, green and yellow. Organizers whose event is red have no matching tint, and an organizer with a good photograph of the venue or of last year's bouts has no way to put it on the card and the detail. The owner asked for both in one field: the cover's ground is either a color or a photo, and the colors gain red.

## What Changes

- The Setup field beside the logo becomes the cover's ground ("Pozadí pruhu") rather than its tint alone: follow the logo, file-blue, seal-green, form-yellow, the new red tint, or a photo.
- A new pastel tint, red, with its `-ink`, defined in `tokens.css` for both skins. It is offered only as the organizer's choice: the logo's band and the slug keep choosing among the original three, so no existing cover changes.
- An organizer can upload a cover photo. The server bounds it, applies its orientation, strips its metadata and stores it re-encoded, as it does a logo. The photo fills the band, cropped to cover it; the plate, the status block, the ordinal, the Spravovat button and the Paid stamp stand on it unchanged in place.
- On a photo, the parts that stood on the bare tint — the ordinal, the Spravovat button, the Paid stamp — stand on a paper ground so they stay legible. No scrim, gradient, blur or shadow is laid over the photo.
- Removing the photo returns the cover to following the logo. A photo outlives a change or removal of the logo, as the chosen tint does.
- The compact phone row, which has no band, shows no photo.

## Capabilities

### New Capabilities
<!-- none -->

### Modified Capabilities
- `tournament-admin`: "The organizer chooses the cover tint" becomes the choice of the cover's ground — four tints or a photo; a new requirement for uploading, storing and removing the cover photo.
- `fencer-home`: the card's cover and the detail's cover may wear the red tint or a photo; the tint rule names the red tint as a choice only; the legibility of the cover's parts on a photo.
- `design-system`: a fourth pastel pair, red, joins the tint tokens in both skins, distinct from `--stamp-tint` so the open status block stays apart from a red band.

## Impact

- Backend: `Tournament` gains the stored cover photo (bytes, deferred, and mime); `cover_tint` admits `red` and `photo`; an Alembic migration; upload/serve/delete endpoints beside the logo's; list and detail payloads carry whether a cover photo is present; `CoverTint` literal and the schemas.
- Frontend: `tokens.css` (both skins), `index.css` cover/swatch rules, `TournamentCover.tsx`, `setup/CoverTintField.tsx` (becomes the ground field with a photo upload), `IdentitySection.tsx`, `api.ts`, i18n cs/en.
- Tests: backend upload bounds and metadata stripping, the choice's persistence and its clearing when the photo is removed; frontend cover rendering and the Setup field.
