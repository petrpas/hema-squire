## 1. Logo upload — diagnose and fix

- [x] 1.1 Add a backend test that posts a Pillow-generated multi-megapixel JPEG to `POST /api/tournaments/{slug}/logo` and asserts 200 with `has_logo` true; record the status it actually returns if it fails
- [x] 1.2 Raise `LOGO_MAX_UPLOAD_BYTES` to 8 MB, catch `Image.DecompressionBombError` alongside `UnidentifiedImageError`/`OSError`, keep the 512 px re-encode, and log the decode exception on 422
- [x] 1.3 Map upload failures distinctly in `SetupPanel.tsx` (413 too large, 415/422 unsupported format, 401/403 not authorized, other → generic failure with status) and add the three new message keys to `cs.json` and `en.json`
- [x] 1.4 Add backend tests for the oversized (413) and undecodable (422) paths

## 2. Form pattern in dialogs

- [x] 2.1 Rename `.param-field`/`.param-fields` to `.form-field`/`.form-fields` in `index.css`, keeping the old names as aliases, and add a textarea variant (transparent, single bottom rule, vertical resize only)
- [x] 2.2 Apply the field pattern to the new-tournament dialog in `TournamentPicker.tsx` (name, date, slug) so labels sit above full-width inputs, with all colors from `tokens.css`
- [x] 2.3 Verify the dialog against the prohibitions list: no shadow, no radius > 2px, no default blue focus ring, no hex outside `tokens.css`

## 3. Help hint component

- [x] 3.1 Add a `HelpHint` component: focusable bordered `ⓘ`-style marker after a label, hint box on hover and focus, `aria-describedby`, no shadow/blur/transition
- [x] 3.2 Add its CSS to `index.css` using only `tokens.css` values
- [x] 3.3 Attach hints to the four optional discipline fields with the agreed Czech texts (when / where / ruleset name / ruleset link) and their English equivalents

## 4. Backend data model

- [x] 4.1 Add `description` (Text, nullable), `qualification_open` (bool, default true, not null), `qualification_criteria` (Text, nullable) to `Tournament`
- [x] 4.2 Replace `organizer_names: list[str]` with `organizers: list[{name, link}]` on the model, with a reader that tolerates bare strings
- [x] 4.3 Extend `ExtraCategory` with `OTHER_ACTION` and `OTHER_ITEM`, extend `ScopeCategory` in `schemas.py`, and add a test that a row in a new category persists and reloads
- [x] 4.4 Write the Alembic revision: new columns, JSON rewrite of `organizer_names` → `organizers`, and a down-revision that restores names without links
- [x] 4.5 Update `schemas.py` (`TournamentUpdate`, `TournamentOut`, `TournamentDetailOut`), the tournament router's response construction, and `setup.setup_missing`
- [x] 4.6 Bump `export_json.SCHEMA_VERSION` to 2, carry `organizers`/`description`/qualification in `_TOURNAMENT_FIELDS`, accept v1 organizer strings on restore, and cover both directions with a round-trip test

## 5. Validation and pricing behavior

- [x] 5.1 Reject a save that sets `qualification_open` false with empty criteria (field-level 422); clear criteria when set back to open
- [x] 5.2 Force `max_qty` to 1 on save for action categories (`seminar`, `afterparty`, `other_action`) and reject `when`/`where` on item categories
- [x] 5.3 Add a pricing test proving `other_action` and `other_item` total and discount-scope exactly as `afterparty` and `merch`
- [x] 5.4 Add a test that an existing action-category row with `max_qty > 1` keeps its stored value until re-saved

## 6. Setup panel

- [x] 6.1 Remove the identity section heading; keep the i18n key
- [x] 6.2 Add the description textarea to the identity section
- [x] 6.3 Add the qualification control (two radios + conditional criteria field with help hint) between the registration dates and the logo
- [x] 6.4 Render discipline code and name in emphasized text (weight 500, never 600+)
- [x] 6.5 Extras table: derive the kind from the category, show `when`/`where` only for action kinds, show the quantity column only for item kinds, clear fields the new kind does not carry when the category changes, and add the two new categories to the picker with `cs`/`en` labels
- [x] 6.6 Organizers table: add the optional link column, save name+link pairs, keep add/remove working

## 7. Presentation

- [x] 7.1 Present description (`white-space: pre-wrap`), qualification statement, and organizer links in `TournamentDetail.tsx`
- [x] 7.2 Present organizer links in `FencerHome.tsx` and keep the plain-name fallback for entries with no link
- [x] 7.3 Style links as `--ink` with underline, never blue

## 8. Verification

- [x] 8.1 Run the backend test suite and the frontend build/typecheck
- [x] 8.2 Walk the Setup phase and the new-tournament dialog in the running app: create a tournament, upload a real JPEG logo, fill description and qualification, add an organizer with a link, add an `other_action` and an `other_item` row
- [x] 8.3 Grep the diff for hex literals outside `tokens.css`, `box-shadow`, emoji, and radius values above 2px
