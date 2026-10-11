## Context

`add-fencer-night-skin` tints a card's cover by `slugHash(slug) % 3`. Logos are
stored inline (`logo_bytes`, re-encoded to a ≤512px PNG on upload); only the
upload and delete endpoints write them. Owner decisions (2026-10-11): an
achromatic logo falls back to the slug; red/orange/pink logos go to the warm
band, which is form-yellow (stamp-tint stays reserved for open registration).

## Goals / Non-Goals

**Goals:** a cover that matches its logo; no new color values; computed once.

**Non-Goals:** rendering any color from the logo; more than three tints;
letting the organizer pick the tint (a later change could add it beside the
short code).

## Decisions

### D1. Computed on the server, at upload, stored
The list is read far more often than a logo changes, and the frontend may not
read pixel colors from a cross-origin-safe image without a canvas round trip on
every card. One computation per upload, stored as a nullable string column
`logo_tint` (`blue|green|warm`), costs nothing at read time.

### D2. The algorithm
Downscale a copy to 32×32 (`Image.thumbnail`), convert to RGBA, and for each
pixel with alpha ≥ 128 compute HSV. A pixel votes when saturation ≥ 0.25 and
value is between 0.2 and 0.97; its weight is its saturation. Hue bands (degrees):
blue 170–290, green 70–170, warm otherwise. If voting pixels are under 10% of
opaque pixels, the band is none. Pure function `logo_hue_band(image) -> str |
None` in its own module, tested with synthetic images.

*Alternative:* k-means dominant color. Rejected: three bands need a vote, not a
cluster, and the vote is deterministic and dependency-free.

### D3. Names over indices
`data-tint` becomes `blue|green|yellow` so CSS reads as what it means. The slug
fallback maps `slugHash % 3` onto the same three names. `warm` maps to `yellow`
in the frontend's single lookup, so the payload names a band and the frontend
names a tint.

### D4. Backfill in the migration
The migration adds the column and, for every tournament with `logo_bytes`,
computes the band with the same function. Logos are few and small.
`alembic/` imports from `app` already for data migrations; if it does not, the
function is vendored into the migration per the repo's migration rules.

## Risks / Trade-offs

- [A logo on a large colored rectangle votes for its background] → Accepted:
  the background is then the logo's color as anyone would read it.
- [Thresholds misjudge a muted logo] → Falls back to the slug, which is today's
  behavior.

## Migration Plan

Additive nullable column with a data backfill. Rollback drops the column; the
frontend falls back to the slug when the field is absent.

## Open Questions

None.
