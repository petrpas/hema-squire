## Context

Setup (`frontend/src/SetupPanel.tsx`, 1252 lines) and the new-tournament dialog
(`frontend/src/TournamentPicker.tsx`) were built alongside the Bureau 1952 design
system rollout and did not receive its form pattern consistently: `.param-field`
(small-caps label above a bottom-ruled, full-width input) is used inside Setup
panels but not in `.modal`, where `<label>text<input/></label>` collapses onto one
line because nothing makes the label a block container.

On the data side, `Tournament` already carries subtitle, logo, location,
disciplines with schedule/ruleset, extra items with when/where/remark, and
`organizer_names: list[str]` in a JSON column. `ExtraCategory` is a `StrEnum`
persisted through `str_enum()` (`native_enum=False`, no CHECK constraint under
SQLAlchemy 2.0 defaults), so extending the enum is a code change, not a schema
change. Discount scopes reference the same category names
(`ScopeCategory` in `backend/app/schemas.py:141`).

Logo upload (`backend/app/routers/tournaments.py:291`) caps input at 512 KB
(413), decodes with Pillow, and maps decode failure to 422. Pillow in this
environment has a working JPEG decoder (verified: `features.check('jpg')` is
true, and a 2000×1500 JPEG round-trips and thumbnails cleanly), so the reported
"Tento soubor není obrázek" for a valid JPEG is not a decoder problem. The
frontend is the visible offender: `SetupPanel.tsx:67-74` maps 413 to "too large",
422 to "not an image", **and every other failure — 401, 403, 500, network — to
"not an image" as well**.

Owner decisions taken before drafting (2026-07-29): plain multiline description
field (no markdown), new enum values for the two generic extra kinds, qualification
as a choice plus criteria text that does not gate registration, and help hints as
a hover/focus marker.

## Goals / Non-Goals

**Goals:**

- The new-tournament dialog reads as the same tiskopis as Setup.
- Logo upload failures name the actual cause; a valid JPEG a phone produced
  succeeds.
- Optional fields in Setup explain themselves without permanently inflating rows.
- Extra services expose only the fields their kind can meaningfully carry, and
  cover generic "other action" / "other item" without abusing existing categories.
- Organizers, description, and qualification are capturable and presentable.

**Non-Goals:**

- Markdown authoring or rendering anywhere.
- Any change to price computation, discounts, or the registration flow.
- Qualification enforcement — it is published text, not a gate.
- Reworking Setup's overall layout beyond the specific items listed.

## Decisions

### D1 — One form-field pattern, shared by panels and dialogs

Promote the existing `.param-field` / `.param-fields` rules in `index.css` to a
neutral name (`.form-field` / `.form-fields`) and apply them inside `.modal`,
keeping `.param-field` as an alias so the many existing call sites need not change
in this pass. The dialog's three fields (name, date, slug) become labels with a
small-caps caption above a full-width bottom-ruled input; `.modal input` keeps its
current typography. All colors continue to come from `tokens.css`.

*Alternative rejected:* styling `.modal label` separately — that would give the
app two form idioms that drift apart.

### D2 — Logo errors: report the real cause, and stop rejecting real photos

Three changes, in this order:

1. **Reproduce first.** A backend test posts a real JPEG (generated with Pillow)
   to `POST /api/tournaments/{slug}/logo` and asserts 200 plus `has_logo`. If it
   passes, the fault is entirely in the client's error mapping; if it fails, the
   assertion names the status the server actually returns.
2. **Raise the input cap** from 512 KB to 8 MB. The endpoint re-encodes to a
   512 px PNG regardless, so the cap only exists to bound decode work — and at
   512 KB it rejects almost every phone or camera JPEG. Guard the decode with
   Pillow's `DecompressionBombError` (currently uncaught → 500 → the misleading
   message) and keep a pixel bound.
3. **Map statuses distinctly** in `SetupPanel.tsx`: 413 → too large, 415/422 →
   unsupported format, 401/403 → not authorized, anything else → a generic
   "upload failed" with the status. The server keeps returning machine-readable
   `detail` codes (`logo_too_large`, `logo_not_an_image`) and logs the decode
   exception.

*Alternative rejected:* client-side MIME sniffing before upload — it would mask
server-side causes rather than name them.

### D3 — Help hints as a static hover/focus marker

A small `HelpHint` component renders an `ⓘ`-style marker (a bordered glyph in
`--ink-faded`, not an emoji, not a filled icon) after a field label. The hint text
appears on hover **and** on keyboard focus of the marker, as an absolutely
positioned box: `--paper-raised` background, 1px `--ink` border, 2px radius, no
shadow, no animation, no transition — the prohibitions list forbids all three. The
marker is a `<button type="button">` with `aria-describedby` pointing at the hint
box so screen readers reach it.

Applied to: discipline `when`, `where`, `ruleset name`, `ruleset link`, and the
qualification criteria field. Hint texts live in `i18n/cs.json` and `en.json`.

*Alternative rejected:* the native `title` attribute — unstyleable and
keyboard-inaccessible.

### D4 — Extra-service categories split into "action" and "item" kinds

`ExtraCategory` gains `OTHER_ACTION = "other_action"` and `OTHER_ITEM =
"other_item"`; `ScopeCategory` in `schemas.py` gains both. Because `str_enum()`
builds a non-native VARCHAR enum with no CHECK constraint, no DDL migration is
required — the migration for this change is a no-op for the enum, and a test
asserts that a row with the new category persists and reloads.

A single kind map, defined once in the frontend and mirrored by a backend
predicate, drives behavior:

| Kind | Categories | when / where | max_qty |
|---|---|---|---|
| action | `seminar`, `afterparty`, `other_action` | shown | hidden, stored as 1 |
| item | `rental`, `merch`, `other_item` | hidden | shown |

`remark` stays available to both. Existing action-category rows whose `max_qty` is
not 1 are left untouched by the migration (their stored totals stay reproducible);
the UI stops offering the input, and the next save normalizes them to 1. Switching
a row's category in the UI clears the fields that its new kind does not carry.

*Alternative rejected:* a separate `kind` column — it would duplicate information
the category already determines.

### D5 — Organizers become name + optional link

`Tournament.organizer_names` (JSON list of strings) becomes `Tournament.organizers`
(JSON list of `{"name": str, "link": str | null}`). An Alembic data migration
rewrites existing rows in place; the reader tolerates bare strings so a
partially-migrated or restored-from-old-export deployment still loads.

`organizer_names` is part of the versioned export contract
(`export_json._TOURNAMENT_FIELDS`), so `SCHEMA_VERSION` goes 1 → 2, the field list
carries `organizers`, and restore accepts both shapes (a v1 document's list of
strings normalizes on the way in). Read sites — `TournamentDetail.tsx:46`,
`FencerHome.tsx:54`, `setup.setup_missing` — render names as text and the name as
a link (`--ink`, underlined, never blue) where a link is present.

*Alternative rejected:* a parallel `organizer_links` array — index-aligned arrays
drift.

### D6 — Description as plain text

`Tournament.description: Text | None`, edited as a textarea in the Setup identity
section, presented with `white-space: pre-wrap` so paragraph breaks survive. No
markdown parsing, no HTML: the value is rendered as text content, which also means
nothing to sanitize. A textarea styled like `.form-field input` (transparent, one
bottom rule, `--font-ui`) with a modest default height and vertical resize only.

### D7 — Qualification as openness flag plus criteria

Two columns: `qualification_open: bool` (default true, so every existing
tournament reads "open to everyone") and `qualification_criteria: Text | None`.
The Setup identity section places the control between the registration dates and
the logo: two radios, with the criteria field (plus its help hint: national
championship, HR top 500, …) shown only when "qualification required" is chosen.
Saving with "open to everyone" clears the criteria text. Validation: choosing
"qualification required" with empty criteria is rejected with a field-level
message. Public presentation states the criteria when set and says "open to
everyone" otherwise; registration is unaffected.

### D8 — Identity heading removed, discipline names bold

`t("setup.identity.title")` is dropped from the rendered output (the key stays in
the catalogs for the phase-level heading if needed). The discipline row's code and
name become `<strong>{code} — {name}</strong>` at weight 500, since weight 600+ is
prohibited.

## Risks / Trade-offs

- **The JPEG failure may not reproduce** → the reproduction test is step one, and
  the distinct error mapping is valuable regardless of what it uncovers; if the
  test fails, the actual status is captured in the assertion rather than guessed.
- **Export schema bump** → restore keeps reading v1 documents, and the bump is
  covered by a round-trip test in both directions.
- **`organizers` rename touches several read sites** → all five are known and
  listed in D5; the tolerant reader means a missed one degrades to plain names,
  not an exception.
- **Action rows with `max_qty > 1` in existing data** → left as stored so historic
  totals stay reproducible; normalized on next save. Documented in the spec delta.
- **Raising the logo cap 16× increases decode cost** → bounded by the pixel guard
  and `DecompressionBombError`; the stored blob is unchanged at ≤512 px PNG.
- **Hint markers add a control per optional field** → they are focusable buttons,
  so the tab order in the discipline sub-row grows; hints are attached only to the
  five fields that genuinely need explaining.

## Migration Plan

1. Alembic revision: add `description`, `qualification_open` (default true, not
   null), `qualification_criteria`; rewrite the `organizer_names` JSON payload into
   `organizers` (list of objects) and drop the old column.
2. Deploy backend and frontend together — the frontend reads `organizers`.
3. Rollback: the down-revision restores `organizer_names` from `organizers` by
   taking each entry's `name`, losing only the links.

## Open Questions

None; the four open decisions were resolved with the owner on 2026-07-29 and are
recorded in D3, D4, D6, and D7.
