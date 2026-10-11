## Why

The night skin rebuilt the tournament list as cards but left the detail on the
ledger geometry: square tabs, 2px blocks and buttons, a bare logo. Opening a
card leads to a page that reads as a different system. The owner asked for the
detail to match the list (2026-10-11).

## What Changes

- Detail tabs become the list's segmented pill control.
- Content blocks (`rail-card`) round at `--radius-card`; buttons become pills
  through `--radius-pill`. Both are token reads with 2px day values, so the
  console is unchanged.
- The information block opens on the card's cover: tint, plate with logo or
  short code/monogram, ring by status, and the status block.
- Disciplines on the detail carry the static capacity meter.
- The Setup preview panel wears the night skin, since it previews a night page.
- The fencer detail payload gains `logo_tint` and `short_code`.

## Capabilities

### New Capabilities
<!-- none -->

### Modified Capabilities
- `design-system`: Skins admits the preview panel as a night island; Button
  hierarchy reads `--radius-pill`.
- `fencer-home`: the detail's geometry, cover and meters.
- `setup-preview`: the preview renders night.

## Impact

- Frontend: `index.css` (stage-control pill variant shared by list and detail,
  `rail-card`, buttons), `TournamentFace.tsx` (`InfoHeader` cover,
  `DisciplinesInfo` meters), `StatusBlock` generalized to the detail's data,
  a shared cover/plate component, `SetupPreview.tsx`, `TournamentDetail.tsx`.
- Backend: `FencerTournamentOut` and `TournamentOut` carry `logo_tint` and
  `short_code`.
