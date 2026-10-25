## 1. Tokens and styles

- [x] 1.1 Add `--ledger-red` / `--ledger-red-ink` to `tokens.css` in the day `:root` and the night block, with a comment placing them among the pastels
- [x] 1.2 Extend the night-skin contrast test (or add one) to check `--ledger-red-ink` on `--ledger-red` ≥ 4.5:1 in both skins
- [x] 1.3 `index.css`: `[data-tint="red"]` for `.home-card-cover`, the detail cover and `.tint-swatch`; the 1px `--stamp` outline on the open status block under a red cover
- [x] 1.4 `index.css`: `[data-photo]` cover rules — `.cover-photo` image behind the cover's children with `object-fit: cover`; ordinal on a `--paper` chip; Spravovat pill and Paid stamp on `--paper-raised`; hidden in the compact phone row

## 2. Backend

- [x] 2.1 `logo_tint.py`: keep `CoverTint` for the four tints (add `red`), add `CoverGround = CoverTint | "photo"`; slug/band logic untouched
- [x] 2.2 `models.py`: `cover_photo_bytes` (deferred `LargeBinary`), `cover_photo_mime`, `has_cover_photo`; `cover_tint` typed `CoverGround | None`
- [x] 2.3 Alembic revision adding the two columns; downgrade nulls `red`/`photo` in `cover_tint` and drops them
- [x] 2.4 `schemas.py`: widen every `cover_tint` literal to the ground values; add `has_cover_photo` to the list entry and the detail
- [x] 2.5 PATCH: reject `cover_tint="photo"` without a stored photo (422 `cover_photo_missing`)
- [x] 2.6 `POST/GET/DELETE /tournaments/{slug}/cover-photo`: logo's auth and size cap; `exif_transpose`, RGB, thumbnail 1600, JPEG q82 with no metadata; `cover_photo_too_large` / `cover_photo_not_an_image`; DELETE clears `cover_tint` when it is `photo`
- [x] 2.7 Tests: a rotated JPEG with GPS EXIF comes back upright, ≤1600px, without EXIF; oversized and undecodable rejected by cause; deleting the worn photo returns the choice to null; logo removal leaves the photo; `photo` refused without a photo
- [x] 2.8 `uv run ruff check .` and `uv run basedpyright` clean

## 3. Frontend data and rendering

- [x] 3.1 `api.ts`: `CoverTint` gains `red`, `CoverGround` adds `photo`; `has_cover_photo` on list entry and detail; `coverPhotoUrl(slug, version)`; upload/delete calls mirroring the logo's with error mapping
- [x] 3.2 `TournamentCover.tsx`: `coverTint()` ignores `photo` and falls through to band/slug; add `coverPhoto(subject)`; the cover renders `data-photo` and the `<img class="cover-photo" alt="" loading="lazy">`
- [x] 3.3 Card and detail covers use it; tests: a photo cover shows the image and keeps plate and status block; red chosen gives `data-tint="red"`; no choice never gives red

## 4. Setup field

- [x] 4.1 Rename `CoverTintField` to `setup/CoverGroundField.tsx`: follow / blue / green / yellow / red / photo, label "Pozadí pruhu"; photo option with tertiary upload/remove and a band-shaped thumbnail
- [x] 4.2 Choosing photo without a stored one opens the picker; successful upload selects it and dirties the section; failed upload reports its cause like the logo's
- [x] 4.3 `IdentitySection.tsx` wiring; i18n cs/en (`coverGround`, `coverTintName.red` = "Červená"/"Red", photo strings, error messages) in sentence case
- [x] 4.4 Tests for the field: red selectable and saved; photo selected after upload; tint over a stored photo keeps the photo choosable
- [x] 4.5 `npm run typecheck`, `npm run check`, `npm test` clean

## 5. Specs

- [x] 5.1 Look at a red card and a photo card in both skins in the running app; settle the open questions in design.md with the owner before archiving
