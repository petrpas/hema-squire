## Why

The owner wants Spravovat in the cover band's bottom right corner on the card
and the detail (2026-10-11), rather than below the card's foot and beside the
detail's tabs.

## What Changes

- Card: the Spravovat link stays a sibling of the card's body link (no link in
  a link) and is placed over the cover's bottom right corner; on a phone, where
  there is no cover band, it stays below the foot.
- Detail: `InfoHeader` takes an optional cover action rendered in the cover's
  bottom right corner; the detail passes Spravovat there and the header no
  longer carries it. The Setup preview passes none.

## Capabilities

### New Capabilities
<!-- none -->

### Modified Capabilities
- `fencer-home`: Managing a tournament from its card — placement.

## Impact

`TournamentCard.tsx` (none), `TournamentFace.tsx`, `TournamentDetail.tsx`,
`index.css`, `publicDetail.test.tsx`.
