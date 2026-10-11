## Why

A card states how many fencers and clubs are entered, but not whether anyone the
visitor knows is among them — which is what makes a younger fencer decide to go.
The rosters already publish every name; this change brings the few that matter
to a signed-in visitor onto the card. Design source: `openspec/night-skin-brief.md` §2.
Depends on `add-fencer-night-skin` (card footer, club normalizer).

## What Changes

- The list payload gains, for a signed-in caller only, `familiar`: up to three
  seated entrants from the caller's club, or failing any, the top-rated from the
  caller's country, with the total behind them. Absent for an anonymous caller
  and absent where nobody matches.
- The card footer's left side shows up to three overlapping round faces (initials
  on a tint) and a note: `3 z tvého klubu` / `nejvýš hodnocení z CZ`.
- Selection is computed for the whole list in batched queries, never per card.

## Capabilities

### New Capabilities
<!-- none -->

### Modified Capabilities
- `public-browsing`: a list entry may carry a caller-dependent `familiar` field,
  absent without a credential like the other bond fields.
- `fencer-home`: the card footer's left side states familiar faces.

## Impact

- Backend: `OpenTournamentOut.familiar`, a selection module reading `Fencer.hr_id`
  → `HRFighter.club` / `.nationality`, the seated-entrant predicate shared with
  the public roster, the club normalizer from `add-fencer-night-skin`, and the
  latest rating snapshot where one exists.
- Frontend: `OpenTournament.familiar` in `api.ts`, a `FamiliarFaces` component in
  the card footer, i18n keys in both locales.
- Privacy: exposes only names and initials already public on the entrant rosters,
  to signed-in callers.
