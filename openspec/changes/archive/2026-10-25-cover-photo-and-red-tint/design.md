## Context

The cover band (card and detail) wears one of three pastel tints, resolved in `coverTint()` (`frontend/src/TournamentCover.tsx`) from, in order, the organizer's `cover_tint`, the logo's hue band (`logo_tint`) and the slug hash. Setup offers the choice in `setup/CoverTintField.tsx` beside the logo, saved with the identity section. The logo itself is stored inline on `Tournament` (`logo_bytes` deferred, `logo_mime`), uploaded through `POST /tournaments/{slug}/logo`, bounded by `LOGO_MAX_UPLOAD_BYTES` and re-encoded to PNG ≤ 512px.

The owner asked for two things in one field: a photo as the band's ground, and red among the colors. The design system forbids a second saturated color, hex outside `tokens.css`, and any scrim, gradient, blur or shadow — which rules out the usual darkening veil over a cover photo.

## Goals / Non-Goals

**Goals:**
- One Setup choice for the cover's ground: follow the logo, four tints, or a photo.
- A red pastel token pair for both skins, offered by choice only.
- A stored, bounded, metadata-free cover photo served publicly beside the logo.
- Every cover part stays legible on any photo without overlaying the photo.

**Non-Goals:**
- No cropping or focal-point editor; the photo is centred and cropped to cover.
- No red from the logo's band or the slug; no change to faces, tags or statuses.
- No photo on the compact phone row, in exports, or on the roster print.
- No free color picker (see the earlier cover-tint decision).

## Decisions

**D1. `cover_tint` becomes the ground choice; values `blue | green | yellow | red | photo | null`.** One column keeps "one choice" literal and reuses the existing save path in `IdentitySection`. A separate `cover_kind` column was considered and rejected: it would admit the meaningless pair "photo + green". The Python `CoverTint` literal splits into `CoverTint` (four tints) and `CoverGround = CoverTint | "photo"`; the column widens no further than `String(10)` already allows. The PATCH rejects `photo` while no photo is stored (422 `cover_photo_missing`).

**D2. The photo lives inline like the logo:** `cover_photo_bytes` (`LargeBinary`, deferred) and `cover_photo_mime`, with a `has_cover_photo` property. Endpoints `POST/GET/DELETE /tournaments/{slug}/cover-photo`, mirroring the logo's authorization, size cap (8 MB) and error codes (`cover_photo_too_large`, `cover_photo_not_an_image`). Re-encode: `ImageOps.exif_transpose`, convert to RGB, `thumbnail((1600, 1600))`, save as JPEG quality 82 without `exif=` — Pillow writes no metadata unless asked, which is the stripping. JPEG rather than the logo's PNG because a photograph at 1600px is several times smaller as JPEG. Inline storage keeps backups and the deploy simple; at ≲300 KB per tournament it is well within what the logo column already proves.

**D3. Removing the photo clears `cover_tint` when it was `photo`.** The cover never points at a missing picture. Choosing a tint keeps the stored photo (spec: return without re-uploading); a kept, unworn photo is still publicly readable — it was uploaded to be shown, and hiding it would cost an authorization branch on the GET for nothing.

**D4. Payloads carry `has_cover_photo`;** the frontend shows the photo where `cover_tint === "photo" && has_cover_photo`. The public covers use the plain URL, as the logo does; the Setup preview carries a version counter bumped on upload, as `LogoControl`'s does. (A version from `updated_at` was considered; the tournament has no such column, and the logo has lived without one.)

**D5. Rendering.** `coverTint()` keeps returning a tint (`photo` excluded) — it still colors the monogram and names what "follow the logo" gives. A new `coverPhoto(subject): boolean` decides the ground. The cover element gets `data-photo` and an `<img class="cover-photo">` absolutely positioned behind its children with `object-fit: cover`; no `background-image` in a `style` attribute, so no URL or color lives in CSS strings built by a component. Under `[data-photo]`, CSS gives the ordinal a `--paper` chip, the Spravovat pill a `--paper-raised` ground, the Paid stamp a `--paper-raised` ground. The compact row hides the image with the band.

**D6. Red token.** `--ledger-red` / `--ledger-red-ink`, named in the bureau family (file, seal, form, ledger). Starting values, to be checked by the contrast test the night skin already has: day `#ddc0b4` / `#6e3b30` (ink 5.3:1), night `#2a1712` / `#e8b4a6` (ink 9.4:1). They lean rose-brown against `--stamp-tint`'s pink. Lightness alone cannot separate them in the night skin (1.1:1), hence the spec's 1px `--stamp` outline on the open status block under `[data-tint="red"]`.

**D7. Red is never derived.** The slug hash keeps its three-element list and the warm band keeps form-yellow. Adding red to either would repaint covers organizers have already seen; the owner asked for red as an option.

**D8. Setup field.** `CoverTintField` becomes `CoverGroundField`: six radios (follow, four tints, photo), the photo radio followed by the tertiary upload/remove actions and a small thumbnail when stored. Choosing photo without a stored one opens the file picker. The file itself is sent and removed at once, as the logo's is, but the section is not reloaded: a successful upload selects photo and marks the section dirty, so the ordinary Save wears it and other unsaved edits survive. Removal deselects photo locally; the server has already returned a saved photo choice to following the logo.

## Risks / Trade-offs

- [A busy or very light photo makes the plate's `--hairline-strong` ring hard to see] → the plate itself is opaque `--plate`/`--paper`, so the logo stays readable; the ring is decoration, not the sole carrier of open/closed (the status block states it).
- [Photo payload weight on the list] → bounded 1600px JPEG, `loading="lazy"` on cards, cache headers like the logo's.
- [Organizer uploads a portrait photo into a wide band] → cropped to centre; the Setup thumbnail shows the band's aspect so the crop is seen before saving.
- [Database growth] → one photo per tournament, ≲300 KB; acceptable at the platform's scale.

## Migration Plan

One Alembic revision adds `cover_photo_bytes` and `cover_photo_mime` (nullable). `cover_tint` needs no data migration: existing values remain valid. Rollback drops the two columns and resets any `red`/`photo` value in `cover_tint` to NULL in the downgrade.

## Resolved Questions (owner, 2026-10-25)

- Should a warm logo's band now give red instead of yellow? **Yes** — but not in this change, which ships red as a choice only (D7). A follow-up change splits the warm band so a red logo's cover wears ledger-red, and states which covers already seen change.
- The red values of D6 are accepted as they are.
- The Spravovat pill on a photo stays outline-only on `--paper-raised`.
