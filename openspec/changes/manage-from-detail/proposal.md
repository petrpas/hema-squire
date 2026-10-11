## Why

An organizer opening their own tournament's detail has no way to its console,
and on the list the Spravovat control is an underlined link that reads as
text (owner, 2026-10-11).

## What Changes

- The public detail payload carries the caller's `organized` bond (absent
  anonymously); the detail header shows a Spravovat button when it is true.
- Spravovat on the card and the detail is a quiet secondary pill button,
  still a link to the console URL.

## Capabilities

### New Capabilities
<!-- none -->

### Modified Capabilities
- `fencer-home`: Managing a tournament from its card extends to the detail and
  fixes the control's look.
- `public-browsing`: the detail carries the manage bond.

## Impact

Backend `fencer_tournament_detail` and `FencerTournamentOut`; frontend
`TournamentDetail.tsx`, `TournamentCard.tsx`, `index.css`, `api.ts`.
