## Context

The monogram helper from `add-fencer-night-skin` is a pure frontend function.
This change lets the organizer override it. Brief: `openspec/night-skin-brief.md` §3.

## Goals / Non-Goals

**Goals:** one optional column, one field, one fallback.
**Non-Goals:** using the short code anywhere but the plate (exports, mails,
URLs); uniqueness across tournaments.

## Decisions

### D1. Store only a deliberate value
Prefilling with the derived monogram and storing only a change keeps the
derivation live for tournaments whose organizer never cared, so a rename still
updates the plate. The settings form compares against `monogram(display_name)`
computed client-side; the server stores what it is sent (null or a 1–3 char
string) and validates length. Comparing on the server would need a second
implementation of `monogram` in Python; the client is the only writer of this
field, so one implementation suffices.

### D2. Length counts visible characters
Validated as 1–3 grapheme-ish characters after trimming; in practice Czech
letters with diacritics are single code points in NFC, so the server normalizes
to NFC and counts code points.

### D3. Export
The tournament JSON export carries neither the subtitle nor the logo, so the
short code, which is of the same cosmetic kind, is not exported either.

### D4. The Setup field
The field stands right under the logo control, the thing it stands in for. The
identity section was already past the size the frontend conventions allow, so
the logo control moved to `setup/LogoControl.tsx` and the field with its rules
(`shortCodeShown`, `shortCodeCheck`, `shortCodePatch`) lives in
`setup/ShortCodeField.tsx`.

## Risks / Trade-offs

- [The prefilled value looks stored when it is not] → The help hint states that
  an unchanged value follows the name.

## Migration Plan

Nullable column, Alembic migration with no backfill. Rollback drops the column.

## Open Questions

None.
